# Dashboard Data Contract Audit

## تصمیم اجرایی

**معماری هدف: Historical Closed Trade Journal. اصلاح قرارداد داده قبل از بازطراحی UI ضروری است.**

این گزارش فقط پیشنهاد اصلاح است؛ هیچ منطق برنامه، schema، داده یا تبدیل ارزی تغییر نکرده است. دادهٔ Open/Floating نباید جزو KPIهای تاریخی Dashboard باشد. قابلیت‌های عملیاتی Prop و Finance در صفحات مالک خود باقی می‌مانند.

**اولویت‌ها: 3 مورد P0، 6 مورد P1، 3 مورد P2؛ جمعاً 12 مسئله.** P0 در این گزارش یعنی مانع اعتماد به قرارداد تاریخی و شروع redesign، نه اثبات خسارت مالی یا نقص امنیتی بحرانی. یافته‌های داده‌وابسته مشروط‌اند؛ دادهٔ production بررسی نشده است.

## روش، شواهد و محدودیت

- مبنا، کد فعلی workspace است، نه ادعاهای گزارش قبلی. وضعیت اولیهٔ `git status --short` خالی بود.
- مسیر Dashboard → client/request → API → query/helper → equity/drawdown بررسی شد. بخش‌های مرتبط با قرارداد، یافته‌ها و توصیه‌های گزارش قبلی تطبیق داده شدند؛ بازبینی کامل تمام 13 بخش UX گزارش قبلی ادعا نمی‌شود.
- خروجی‌های خواندن بزرگ بعضاً میانه‌بریده بودند؛ یافته‌های زیر به بخش‌های مشخص و قابل مشاهدهٔ کد متکی‌اند. شواهد ناقص قبلی مبنای اثبات قرار نگرفتند.
- تست‌های موجود اجرا شدند؛ تست جدید، browser test، فراخوانی سرور واقعی یا بررسی دیتابیس production انجام نشد. پوشش کامل parserهای هر broker و تمام schemaهای ورودی احراز نشده است.
- تاریخ آینده در queryهای خوانده‌شده منع نشده است؛ این اثبات نمی‌کند هر مسیر ورودی حتماً آن را می‌پذیرد. دفاع read-side همچنان لازم است.

### راهنمای ارجاع به منابع

تمام ارجاع‌های کوتاه زیر به همین مسیرهای absolute و شمارهٔ خطوط نسخهٔ زمان ممیزی اشاره دارند:

| شناسه | مسیر |
|---|---|
| D | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx` |
| C | `C:\MokTradeDesk\frontend\src\api\client.ts` |
| A | `C:\MokTradeDesk\backend\app\api\analytics.py` |
| F | `C:\MokTradeDesk\backend\app\api\finance.py` |
| T | `C:\MokTradeDesk\backend\app\api\trades.py` |
| X | `C:\MokTradeDesk\backend\app\api\export.py` |
| M | `C:\MokTradeDesk\backend\app\services\metrics.py` |
| FM | `C:\MokTradeDesk\backend\app\services\finance_metrics.py` |
| AS | `C:\MokTradeDesk\backend\app\services\analysis_service.py` |
| PR | `C:\MokTradeDesk\backend\app\services\prop_rule_engine.py` |
| EQ | `C:\MokTradeDesk\backend\app\domain\risk\equity_engine.py` |
| DD | `C:\MokTradeDesk\backend\app\domain\risk\drawdown_engine.py` |
| EC | `C:\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx` |
| DR | `C:\MokTradeDesk\backend\app\utils\date_range.py` |
| TH | `C:\MokTradeDesk\backend\app\utils\time_helpers.py` |
| TM | `C:\MokTradeDesk\backend\app\utils\trade_metrics.py` |
| IM | `C:\MokTradeDesk\backend\app\services\import_engine.py` |
| MODEL | `C:\MokTradeDesk\backend\app\models\strategy.py` |
| OLD | `C:\MokTradeDesk\DASHBOARD_AUDIT.md` |

## 1. جریان دادهٔ فعلی

1. D:198–239 درخواست اصلی analytics را با Date/Scope/Currency می‌فرستد؛ هم‌زمان Real Summary فقط Currency، Yesterday فقط Scope/Currency، و Recent Trades فقط status/currency/limit/sort می‌گیرند. این‌ها یک جمعیت مشترک ندارند.
2. D:245–269 برای Backtest درخواست مستقل `scope=backtest,currency=USDT,version_id` می‌فرستد؛ تاریخ انتخابی به آن منتقل نمی‌شود.
3. A:325–367 query پایه را می‌سازد. count و Net PnL از `scoped_q`، اما برد/باخت، PF و Average R از معاملات بسته محاسبه می‌شوند. `_scope_filter` فقط با وجود مرز تاریخ، بسته‌بودن را اجباری می‌کند (A:100–124).
4. A:370–418 همان closed query را با ترتیب `close_time,id` به domain equity می‌فرستد؛ adapter در A:233–240 مقدار net را به pnl و هزینه‌ها را به صفر می‌گذارد. **هزینه دوباره اعمال نمی‌شود.**
5. F:1445–1554 کارت‌های Real را مستقلاً از معاملات بستهٔ REAL_PERSONAL و FUNDED_REAL هم‌ارز می‌سازد؛ Analytics یا AnalysisRun منبع این کارت‌ها نیست.
6. X:439–448 به‌جای استفاده از context صفحه، Dashboard را با Real/USDT و بدون version/date فراخوانی می‌کند. C:181–182 و D:319–321 نیز هیچ فیلتر export نمی‌فرستند.
7. AS مسیر جداگانهٔ تحلیل و ذخیرهٔ نتیجه است. queryهای تحلیل نسخه/حساب/مرحله در AS:207–235 closed-only هستند؛ فرمول‌های net/R/PF در AS:380–434 قرار دارند. واردکردن AnalysisService در Analytics به معنی استفادهٔ Dashboard از snapshotهای تحلیل نیست.

## 2. ماتریس فیلتر فعلی

«ثابت» یعنی context مستقل، نه پشتیبانی از فیلتر انتخابی Dashboard. «خیر» یعنی در درخواست/قرارداد مربوطه اعمال نمی‌شود. Closed فقط non-null بودن close_time را نشان می‌دهد، نه تأیید سقف as_of.

| مصرف‌کننده / endpoint | Date | Scope | Currency | Version | Account | Closed Only | Prop Stage |
|---|---|---|---|---|---|---|---|
| `/api/analytics/dashboard` summary | بله، close_time؛ parser اختصاصی | بله | بله | API بله؛ درخواست اصلی خیر | خیر | **خیر بدون تاریخ** برای net/count | real فقط funded؛ selector ندارد |
| همان endpoint: curve/PF/R/distribution | بله، close_time | بله | بله | API بله | خیر | بله | همان محدودیت scope |
| همان endpoint: today/periods | بازهٔ ثابت ∩ تاریخ انتخابی | بله | بله | API بله | خیر | بله؛ بدون سقف now | همان محدودیت scope |
| همان endpoint: open_trades | خیر | بله | **خیر** | خیر | خیر | خیر، فقط open | real فقط funded |
| همان endpoint: prop_progress | خیر، lifecycle | مستقل از scope | بله | خیر | selector ندارد | ترکیبی، وابسته به risk basis | همهٔ مراحل active هم‌ارز |
| همان endpoint: spendable_money | خیر | مستقل | بله | خیر | تجمیعی | funded helper فاقد closed شرط | funded |
| `/api/finance/real-summary` | خیر، کل تاریخ | ثابت real | بله | خیر | selector ندارد | بله | فقط funded |
| Backtest panel → analytics/dashboard | ارسال نمی‌شود | ثابت backtest | ثابت USDT | بله | نامرتبط | net/count بدون تاریخ خیر | نامرتبط |
| `/api/analytics/yesterday` | ثابت روز قبل تهران | بله | بله | خیر | خیر | بله | real فقط funded |
| `/api/trades/` API | بله، **open_time** | test_type، نه scope ترکیبی | بله | بله | personal/prop بله | فقط با status=closed | selector دارد |
| Recent Trades در Dashboard | **ارسال نمی‌شود** | **ارسال نمی‌شود** | بله | خیر | خیر | بله | selector ارسال نمی‌شود |
| `/api/finance/real-pnl` و `/net-profit` | خیر | بر مبنای ارتباط حساب/مرحله | بله | خیر | تجمیعی | **خیر**؛ pnl non-null | funded برای prop |
| `/api/export/dashboard/pdf` | خیر | ثابت real | ثابت USDT | صریحاً None | خیر | نقص summary ارث می‌رسد | ثابت بر اساس real |

منابع: D:203–215,263؛ A:100–124,308–335,407–410,441–486,565–589؛ F:1325–1366,1445–1492,1557–1581؛ FM:56–89؛ T:276–347؛ X:441–448.

درخواست‌های Finance Summary/Accounts/Spendable Assets/Asset Trend در D:207–215 تاریخ، scope، version یا حساب انتخابی Dashboard را نمی‌گیرند؛ Cashflow فقط currency می‌گیرد. این‌ها ledger/asset context هستند و نباید به‌عنوان endpointهای ژورنال تاریخی تلقی شوند. قرارداد کامل همهٔ جزئیات Finance خارج از دامنهٔ این ممیزی است.

## 3. حسابداری، KPI و هم‌خوانی

### Closed eligibility و زمان

- معیار بسته‌بودن فعلی `close_time IS NOT NULL` است؛ PnL non-null جانشین معتبری برای آن نیست. معاملات باز با commission یا pnl ذخیره‌شده می‌توانند net غیرصفر داشته باشند.
- A:47–59 تاریخ نامعتبر را به None تبدیل می‌کند؛ تاریخ date-only را UTC تلقی و پایان را 23:59:59 می‌کند. A:123 از `<=` استفاده می‌کند؛ آخرین میکروثانیه‌های روز حذف می‌شوند. DR:25–50 به‌جای آن بازهٔ UTC نیمه‌باز می‌سازد. این دو قرارداد یکسان نیستند.
- امروز و دیروز بر مبنای مرز تهران‌اند (TH:16–24؛ A:408,582–589). ماه/فصل/سال در A:442–445 **Gregorian UTC** هستند؛ این نکته نباید زیر برچسب تاریخ شمسی پنهان شود.
- امروز و دوره‌های جاری فقط lower bound دارند (A:448–454)، بنابراین رکورد آینده در query واجد شرایط است. Today هم با بازهٔ انتخابی قطع می‌شود، ولی Yesterday مستقل است.
- عنوان تاریخ و weekday دیروز از `y_start` UTC ساخته می‌شود (A:625–630)، نه تاریخ محلی تهران؛ شروع روز تهران در روز تقویمی قبل UTC است.

### Net PnL و ذخیره‌سازی

- `net_pnl = coalesce(pnl,0) + coalesce(commission,0) + coalesce(swap,0)`؛ هزینه‌ها signed هستند (M:22–33). MODEL:218–224 property محاسباتی است، نه ستون جدید Trade.
- IM:328–369 زمان را با offset منبع normalize و pnl/commission/swap را جدا نگه می‌دارد. این شواهد اجازه نمی‌دهد فرض کنیم parser هر broker همیشه gross pnl صحیح تحویل می‌دهد؛ fixture منبع لازم است.
- روی prepared Dashboard curve هزینه‌ها یک‌بار اعمال می‌شوند. در fallback مشترک EC:18–29 فقط raw pnl جمع می‌شود؛ این ایراد واقعی fallback است، **نه اثبات نقص مسیر prepared Dashboard**.
- F:1341,1355 هم open با pnl را می‌پذیرد و هم closed با pnl=NULL و هزینهٔ غیرصفر را حذف می‌کند. FM:56–89 نیز closed شرط ندارد.
- `broker_pnl` در FM:31–45 از اختلاف موجودی، سرمایهٔ اولیه و جریان نقدی ساخته می‌شود؛ مساوی‌گرفتن آن با جمع معامله‌ها بدون reconciliation درست نیست. Finance Net Profit هزینه‌های FEE/PURCHASE را هم کم می‌کند (F:1370–1381,1557–1581). تکرار واقعی یک هزینه در ledger و trade از این کد به‌تنهایی اثبات نشده است.

### تعریف و وضعیت متریک‌ها

| متریک | رفتار فعلی و نتیجه |
|---|---|
| Count | Analytics total ممکن است open را شامل شود؛ closed_count جداست. Real Summary count بسته است. open_trades در A:410 حتی currency/version را رعایت نمی‌کند. |
| Win Rate | `100*wins/closed_count`؛ breakeven داخل denominator است. D:475,545,598,980 مقدار backend را مستقیم format می‌کند؛ **ضرب دوباره در 100 وجود ندارد**. |
| Breakeven | net=0 نه برد است نه باخت. `today.losing_trades=td_count-today_wins_n` در A:530 آن را اشتباهاً باخت می‌شمارد. |
| Average R | A:367 میانگین Rهای non-null بسته؛ A:516 نبود R را صفر نمایش می‌دهد. TM:9–45 R فاصلهٔ قیمت نسبت به ریسک اولیه است، نه لزوماً net money/risk. IM:340–350 R ورودی را نگه می‌دارد یا محاسبه می‌کند. |
| Profit Factor | مثبت‌های net / قدر مطلق منفی‌های net. M:109–120 برای no-loss مقدار 999 و F:1512 مقدار 100 می‌دهد؛ D:484,987 هر عدد >=999 را infinity می‌نامد، حتی ratio متناهی. Finance قبل از تقسیم sums را round می‌کند. |
| Gross profit/loss | نام تاریخی این فیلدها به مجموع مثبت/منفی **net** اشاره دارد، نه gross پیش از هزینه؛ باید در schema روشن باشد. |
| Average/largest loss | Dashboard مقادیر مثبت magnitude می‌دهد (A:357,363)، helper پایه مقادیر منفی می‌دهد (M:149,151). D:506 مجموع gross_loss را «بزرگترین ضرر» می‌نامد. |
| Historical DD | A:393–419 از همان equity points محاسبه می‌کند؛ largest loss نیست. با initial point، peak-to-trough حداقل به‌اندازهٔ static DD است؛ max این دو در این مسیر الزاماً خطای عددی نیست. |
| Equity | closed-only، net و مرتب است؛ اما baseline مجموع initial حساب‌های حاضر در بازه یا fallback 10000 است (A:204–230). opening balance واقعی بازه یا ledger نیست؛ پیش‌تاریخ و cashflow را ندارد. |

### مرز Finance / Prop / Historical

PR:116–149 closed و floating را جدا می‌کند؛ equity-basis می‌تواند floating را به risk اضافه کند. PR:199 هدف سود را از closed_pnl می‌گیرد. این تفاوت **ذاتاً bug نیست** و نباید با حذف globally معاملات باز از PropRuleEngine اصلاح شود. EQ:34–51 فقط floating فعلی را به آخرین نقطه اضافه می‌کند، نه سری تاریخی intratrade drawdown. Dashboard historical باید از realized series استفاده کند و ادعای اندازه‌گیری floating drawdown تاریخی نکند.

برای یک جمعیت یکسان، انتظار می‌رود `last_equity-first_equity = sum(closed net)` باشد. امروز این مقدار می‌تواند با summary بدون تاریخ اختلاف داشته باشد؛ همچنین با کارت all-history Real، Finance net profit و دارایی فعلی الزاماً برابر نیست. اختلاف baseline ثابت، DD پولی را به‌خودی‌خود تغییر نمی‌دهد؛ درصد DD و برداشت کاربر از equity را تغییر می‌دهد.

Currency فعلی account-based است و simulation در filter برابر USDT فرض می‌شود (A:113–115). هیچ conversion لازم یا مجاز نیست. IRR و USDT باید جدا بمانند؛ EC:87 tooltip همیشه USDT است، حتی برای سری IRR.

## 4. PROPOSED DASHBOARD DATA CONTRACT

این بخش قرارداد پیشنهادی است، نه API پیاده‌شده.

### Population و context مشترک

1. یک سرویس/query سازندهٔ historical population برای summary، curve، distribution، period aggregation، recent trades و export؛ اختلاف مجاز فقط pagination جدول باشد.
2. eligibility همیشه `close_time != NULL AND close_time <= as_of`؛ زمان‌های ذخیره‌شده UTC-aware، زمان naive legacy با سیاست صریح UTC. open/floating حتی با pnl یا هزینهٔ غیرصفر حذف شوند.
3. `date_from/date_to` تاریخ ISO **Gregorian** باشند؛ تاریخ شمسی فقط در UI تبدیل شود. timezone گزارش `Asia/Tehran`؛ date_to شامل روز پایان، query به‌صورت `[start_local_to_UTC, next_day_local_to_UTC)` باشد. invalid/reversed range → خطای اعتبارسنجی، نه all-history خاموش.
4. Date همیشه روی close_time. scopeهای real/backtest/forward/all حفظ شوند؛ real = personal + funded prop. all باید اعلام کند شبیه‌سازی و challenge stages را نیز دربر می‌گیرد، نه اینکه «دارایی واقعی» نامیده شود.
5. Currency الزامی و بدون تبدیل؛ personal از حساب شخصی، prop از حساب مرحله، simulation با واحد صریح ثبت‌شده/legacy USDT. انتخاب IRR نباید اعداد USDT را relabel کند. دادهٔ بدون تعیین ارز از جمع پولی حذف و تعداد آن گزارش شود.
6. version_id، personal_account_id، prop_account_id و prop_stage_id در صورت ارائه روی همهٔ اجزا اعمال شوند؛ ناسازگاری account/stage/scope اعتبارسنجی شود. این selectorها در Dashboard فعلی همگی موجود نیستند.
7. response metadata شامل contract_version، generated_at/as_of، timezone، calendar، normalized filters، effective interval، currency، population_count و basis باشد. هر درخواست از یک as_of مشترک و consistency policy مشخص استفاده کند.

### متریک‌ها

- `closed_trades = wins + losses + breakeven`؛ همه بر حسب net. open_trades از payload تاریخی اصلی حذف شود.
- `net_pnl = sum(net)`، هزینهٔ signed یک‌بار؛ null اجزا صفر طبق رفتار فعلی، همراه quality count برای pnl ناقص تا فقدان داده با zero واقعی اشتباه نشود.
- Win Rate درصد 0–100، denominator تمام closed؛ برای empty مقدار null همراه status=no_data. هیچ ×100 اضافی در frontend.
- PF: اگر loss>0 مقدار finite (حتی >=999)، اگر profit>0 و loss=0 مقدار null/status=no_losses، اگر هیچ مثبت/منفی نیست null/status=undefined؛ empty به کمک count از all-breakeven متمایز شود. محاسبه از sums گردنشده؛ rounding فقط serialization/display.
- Average R میانگین non-null R روی همان جمعیت، با `r_sample_count` و `missing_r_count`؛ نبود داده null، R=0 معتبر حفظ شود. basis آن `price_distance_initial_risk` و fee-exclusive بودنش آشکار باشد؛ net R نیازمند قرارداد مستقل monetary risk است.
- loss aggregates و largest_loss به‌صورت magnitude مثبت با نام صریح؛ expectancy = net/closed_count، پولی نه R. رفتار breakeven برای streak روشن شود؛ پیشنهاد reset، مطابق M:87–106، نه رفتار متفاوت M:59–84.
- curve پیش‌فرض cumulative realized net با baseline صفر و عنوان عملکرد تاریخی؛ یا synthetic equity با baseline و منبع صریح. ادعای balance واقعی فقط با reconstruction جداگانه. ترتیب `close_time,id`؛ DD از همان سری کامل گردنشده، نه نمودار downsampled.
- max_drawdown_amount = بیشترین peak-to-trough تاریخی؛ درصد فقط با سرمایهٔ معتبر و denominator تعریف‌شده، در غیر این صورت null. largest_loss، gross_loss و floating DD فیلدهای جایگزین آن نیستند.
- امروز/دیروز و ماه/فصل/سال: Gregorian calendar در timezone تهران، مستقل از تاریخ انتخابی، با همان سایر فیلترها و interval metadata. دورهٔ جاری تا as_of. اگر محصول دورهٔ شمسی می‌خواهد باید تغییر قرارداد صریح باشد، نه تغییر پنهان label.
- export دقیقاً همان normalized filters و basis را چاپ کند. اگر قرار است snapshot نمایش‌داده‌شده صادر شود، snapshot/as_of آن نیز منتقل شود؛ وگرنه زمان generation جدید آشکار باشد.

### جداسازی مالکیت

Dashboard فقط historical trading performance. Finance مالک موجودی، cashflow، هزینه، دارایی و سود پس از هزینه‌های غیرمعامله‌ای؛ Prop مالک lifecycle و risk جاری و floating؛ Analysis مالک جزئیات تحلیل و مقایسهٔ نسخه‌ها. عددی با نام مشابه تا وقتی population/basis/interval/currency یکسان نشده، الزاماً قابل تطبیق نیست.

## 5. مسائل اولویت‌دار و تست پذیرش

### P0 — موانع قرارداد تاریخی (3)

| ID | محل و مشکل تأییدشده | اثر | اصلاح پیشنهادی | تست لازم |
|---|---|---|---|---|
| P0-01 | A:118–124,338–351؛ net/count بدون تاریخ شامل open | اختلاف KPI با curve/PF و آلودگی Backtest به stored floating | historical query همواره closed؛ یک population برای همهٔ متریک‌ها | closed + open با pnl/commission غیرصفر؛ بدون تاریخ، date_from-only و date_to-only؛ تغییر open هیچ historical KPI را عوض نکند؛ curve delta=net |
| P0-02 | D:203–215,263؛ F:1446–1492؛ T:347؛ کارت‌ها/جدول/curve context یکسان ندارند | اعداد all-history/دیگر scope به انتخاب فعلی نسبت داده می‌شوند | summary و recent از context مشترک؛ افزودن close-date mode یا endpoint تاریخی، بدون شکستن open-date قرارداد عمومی Trades | ماتریس Date×Scope×Currency×Version×Account×Stage؛ معامله بازشده خارج و بسته‌شده داخل بازه؛ جمعیت جدول با KPI یکسان |
| P0-03 | F:1325–1366؛ FM:56–89؛ closed eligibility و null pnl ناسازگار | open وارد realized Finance؛ هزینهٔ معاملهٔ بستهٔ pnl-null حذف می‌شود | shared realized population با test_type/closed/currency/stage صریح؛ Finance expense layer جدا بماند | open سوددار، closed fees-only، stage غیرfunded، لینک حساب ناسازگار؛ تطبیق component معاملاتی نه کل ledger با Dashboard |

### P1 — صحت زمان، عدد و خروجی (6)

| ID | محل و مشکل تأییدشده | اثر | اصلاح پیشنهادی | تست لازم |
|---|---|---|---|---|
| P1-01 | A:47–59,118–123,407–454,625–630؛ DR:25–50 | پایان کسری روز، timezone، future rows، period intersection و عنوان دیروز نادرست | یک parser نیمه‌باز، سقف as_of، interval metadata و local labels | مرز نیمه‌شب تهران/UTC، 23:59:59.999999، offset ISO، invalid/reversed، Gregorian year/quarter، future close، selected range خارج today |
| P1-02 | F:1508–1512؛ M:109–120؛ D:484,987 | PF 100/999 مبهم، finite بزرگ به infinity تبدیل می‌شود؛ rounding قبل ratio | discriminated PF status و sums دقیق | empty، breakeven-only، all-win، all-loss، PF=1000 واقعی، loss کوچک‌تر از 0.005 |
| P1-03 | X:439–448؛ C:181–182؛ D:319–321 | PDF با screen متفاوت است | انتقال context و reuse سرویس؛ چاپ فیلتر/as_of | IRR، backtest/version، date/account/stage؛ parity جمعیت و متریک export/API |
| P1-04 | A:204–230,393–418؛ EC:87 | baseline مصنوعی به‌صورت سرمایه تعبیر می‌شود؛ واحد IRR با USDT | baseline/basis/currency metadata؛ cumulative net پیش‌فرض؛ chart واحد را مصرف کند | فقط یک حساب در بازه، چند stage، بازه بدون trade، nonpositive initial، IRR؛ DD مستقل از translation ثابت، no floating |
| P1-05 | A:516,530؛ M:149,151؛ D:506؛ TM:9–45 | no-R با صفر، breakeven با loss و gross_loss با largest loss اشتباه می‌شوند | typed KPI contract، R coverage، breakeven، loss sign/name واحد | wins/losses/zero، R=[null,0,2]→avg=1 و sample=2؛ largest loss با چند باخت؛ درصد مستقیم backend |
| P1-06 | D:198–239 در برابر guard مستقل D:261–268 | پاسخ قدیمی می‌تواند دادهٔ انتخاب جدید را overwrite کند | request identity/cancellation و metadata تطبیق‌پذیر؛ stale state آشکار | دو پاسخ با ترتیب معکوس، تغییر currency/date حین load، partial failure؛ UI هیچ پاسخ context قدیمی را current نشان ندهد |

### P2 — تثبیت قرارداد و پاک‌سازی وابسته (3)

| ID | محل و مشکل تأییدشده | اثر | اصلاح پیشنهادی | تست لازم |
|---|---|---|---|---|
| P2-01 | EC:18–29 در برابر M:22–33 و prepared path | fallback chart هزینه‌ها را حذف می‌کند | حذف fallback مبهم یا استفاده از net صریح typed؛ تغییر بی‌دلیل prepared path ممنوع | pnl=100,commission=-10,swap=-5 → 85 در هر مسیر؛ empty series |
| P2-02 | F:1527–1540؛ M:59–106 | sparkline آخرین 30 روز فعال است نه 30 روز تقویمی؛ دو تعریف streak برای صفر | قرارداد series با dates/granularity؛ یک سیاست breakeven | روزهای خالی و >30 روز؛ [1,0,1] و [-1,0,-1] با سیاست reset |
| P2-03 | D:203–215؛ A:410,469–502؛ PR:116–149 | payload تاریخی با current exposure، Finance و lifecycle آمیخته است | جداکردن response ownership؛ بعداً حذف بخش‌های غیرتاریخی از Dashboard، حفظ صفحات مالک | نبود open/floating در historical response؛ Prop equity-basis regression و closed target؛ Finance balance بدون دوباره‌شماری |

## 6. تطبیق با گزارش قبلی

| ادعای قبلی / توصیه | نتیجهٔ ممیزی فعلی |
|---|---|
| OLD:930–935 دربارهٔ open net، filter mismatch، PF/export/date | با کد فعلی تأیید؛ به P0/P1 تبدیل شده، نه ادعای رفع شدن. |
| ادعای ضرب دوبارهٔ Win Rate | مردود و اصلاح قبلی حفظ شد؛ OLD:1011 نیز استفاده مستقیم درصد backend را ثبت کرده است. |
| equity از closed net و DD از domain | تأیید A:370–419؛ هزینهٔ دوگانه یا جایگزینی DD با single loss در این مسیر اثبات نشد. |
| OLD:881,907,1035,1051 حفظ Open Positions در Dashboard | با معماری جدید **ناسازگار و superseded**؛ از Dashboard اصلی حذف شود، نه از دیتابیس یا صفحات تخصصی. |
| OLD:869–871 حفظ active risk strip | در هدف جدید، lifecycle/risk/floating به Prop/Risk منتقل شود؛ صرفاً لینک ناوبری می‌تواند بماند. |
| OLD:1048 دربارهٔ جدا نگه‌داشتن ارزها | حفظ شود؛ هیچ تبدیل ارز پیشنهاد نمی‌شود. |
| OLD:1031 شمارش 7 High/14 Medium/7 Low | شمارش متعلق به audit گستردهٔ قبلی است؛ با 12 مسئلهٔ این گزارش جمع نشود. موارد UI/session/action خارج از دامنه‌اند. |
| مسیرهای `i:\trade` در بخش‌های قدیمی | شواهد فعلی از مسیرهای absolute همین گزارش در `C:\MokTradeDesk` گرفته شده است. |

گزارش قبلی و یافته‌های غیرمرتبط آن بازنویسی یا ابطال کلی نشده‌اند. تطبیق فوق محدود به data contract است.

## 7. ترتیب اجرای پیشنهادی پیش از redesign

1. تثبیت قرارداد پیشنهادی، به‌خصوص timezone/calendar، PF status، empty/R semantics و ownership.
2. پیاده‌سازی shared historical filter/query و typed response metadata؛ ابتدا P0-01 تا P0-03 و تست‌های population.
3. اصلاح زمان/as_of، PF، export، baseline و KPI semantics؛ یکسان‌سازی componentهای معاملاتی Finance/Analysis بدون یکسان فرض‌کردن ledger و journal.
4. اتصال درخواست‌های Dashboard به context مشترک و جلوگیری از stale response؛ تست parity API/export/chart/table و حفظ regressionهای Prop.
5. فقط پس از سبز شدن تست‌های پذیرش، redesign: header و controls → historical KPIs → دوره‌های روشن → realized performance curve → filtered closed trades. Backtest به‌عنوان scope همان قرارداد قابل استفاده است، نه پنل مستقل با فیلتر پنهان.

### مواردی که فعلاً باید دست‌نخورده بمانند

- فرمول signed net و adapter جلوگیری از هزینهٔ دوگانه؛ data خام و تاریخچهٔ معاملات.
- Win Rate 0–100 و format مستقیم frontend؛ محاسبهٔ درست peak-to-trough domain.
- منطق risk پراپ وابسته به balance/equity و target بسته؛ سهم سود، برداشت و ledger با دامنهٔ تخصصی خود.
- initial SL و R معتبر؛ تبدیل timezone منبع در import؛ تغییر parserها فقط با fixture معتبر منبع.
- فایل گزارش قبلی، UI layout فعلی و تمام کد اجرایی در این task.

### حذف/انتقال بعدی از Dashboard اصلی

Open Positions، floating/instantaneous PnL، active-stage limits/alerts/lifecycle، دارایی/موجودی/cashflow و expense-based Net Profit به صفحات مالک منتقل شوند. نمودار هدف بدون target واقعی و پنل مستقل Backtest با فیلترهای متفاوت حذف یا در Analysis قرار گیرد. حذف از Dashboard به معنی حذف feature، رکورد یا محدودکردن Prop risk نیست.

## 8. اعتبارسنجی انجام‌شده و باقی‌مانده

اجرا از `C:\MokTradeDesk\backend` با Python محیط موجود، `PYTHONDONTWRITEBYTECODE=1` و cacheprovider خاموش:

```powershell
C:\MokTradeDesk\backend\venv\Scripts\python.exe -m pytest -p no:cacheprovider C:\MokTradeDesk\backend\tests\test_metrics.py C:\MokTradeDesk\backend\tests\test_phase43_unified_metrics.py C:\MokTradeDesk\backend\tests\test_phase54_equity_engine.py C:\MokTradeDesk\backend\tests\test_phase54_drawdown_engine.py -q
```

**نتیجه: 28 تست موجود موفق؛ هشدارهای deprecation از FastAPI/Starlette، Pydantic و SQLAlchemy.** fixture در `C:\MokTradeDesk\backend\tests\conftest.py:11–38,41–61` دیتابیس موقت/درون‌حافظه و غیرفعال‌سازی startup را فراهم می‌کند. این تست‌ها regressionهای پایه را تأیید می‌کنند، نه همهٔ defectهای این گزارش یا صحت production.

تمام تست‌های پذیرش جدول مسائل هنوز باید در فاز اصلاح نوشته و اجرا شوند. هیچ unit test جدید یا اصلاح backend در این task انجام نشده است. تنها خروجی مجاز این task همین سند است؛ commit/push انجام نشده است.