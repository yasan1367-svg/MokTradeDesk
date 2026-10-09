# FINANCE AUDIT — PART 4

ممیزی ایستای Trading PnL / Expenses / Net Profit؛ بدون اجرای برنامه، تست یا دسترسی به دیتابیس. فقط همین گزارش نوشته شد؛ هیچ Fix، تغییر کد، migration، Commit یا Push انجام نشد. «تأییدشده» یعنی اثبات از سورس فعلی، نه بازتولید runtime. مثال‌ها فرضی‌اند و یافته‌های گزارش‌های قبلی شاهد این بخش نیستند.

برای خوانایی، ارجاع‌های کوتاه زیر همگی به فایل‌های مطلق زیر اشاره می‌کنند و عدد بعد از نام، شمارهٔ خط است:

- **F**: `i:\trade\MokTradeDesk\backend\app\api\finance.py`
- **FM**: `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py`
- **M**: `i:\trade\MokTradeDesk\backend\app\services\metrics.py`
- **T**: `i:\trade\MokTradeDesk\backend\app\models\strategy.py`
- **A**: `i:\trade\MokTradeDesk\backend\app\api\analytics.py`
- **R**: `i:\trade\MokTradeDesk\backend\app\services\prop_rule_engine.py`
- **I**: `i:\trade\MokTradeDesk\backend\app\services\import_engine.py`
- **P**: `i:\trade\MokTradeDesk\backend\app\services\payout_service.py`
- **FR**: `i:\trade\MokTradeDesk\backend\app\services\financial_reporting.py`

## 1. Personal Broker PnL

### مسیر مبتنی بر معاملات

`/api/finance/real-pnl` از `_compute_real_pnl` استفاده می‌کند. بخش `broker.pnl` دقیقاً حاصل زیر است:

```text
round(SUM(COALESCE(pnl,0)+COALESCE(commission,0)+COALESCE(swap,0)), 2)
FROM trades JOIN personal_trading_accounts
  ON trades.personal_trading_account_id = personal_trading_accounts.id
WHERE personal_trading_accounts.currency = selected_currency
  AND trades.close_time IS NOT NULL
```

شاهد: F:1322–1324، 1450–1468، 1538–1544؛ M:27–33.

- ارز پیش‌فرض USDT است؛ ارز از حساب شخصی گرفته می‌شود، نه ستون ارز روی Trade.
- همهٔ معاملات بستهٔ متصل به حساب‌های آن ارز وارد می‌شوند؛ فیلتر تاریخ، بروکر خاص، strategy/version، فعال‌بودن حساب یا بروکر وجود ندارد.
- `pnl IS NOT NULL` شرط نیست: معاملهٔ بسته با pnl خالی ولی commission=-5، net=-5 دارد و در شمارش معاملات هم هست.
- در همین query شرط صریح `test_type=REAL_PERSONAL` وجود ندارد؛ اتکا به FK و قرارداد classification است. مدل DB، REAL_PERSONAL را فقط به حساب شخصی و REAL_PROP را فقط به مرحلهٔ پراپ مجاز می‌کند؛ BACKTEST/FORWARD نباید هیچ‌یک را داشته باشند (T:182–193). اجرای واقعی constraint در DB تأیید نشد؛ نبود شرط صریح به‌تنهایی اثبات اختلاط دادهٔ معتبر نیست.
- `/real-summary` شرط صریح REAL_PERSONAL، FK شخصی، ارز حساب و close_time را دارد؛ ولی خروجی آن جمع شخصی و FUNDED_REAL است. بازهٔ اختیاری روی close_time اعمال می‌شود (F:1567–1607).
- Open Trade با stored pnl، commission یا swap از این دو مسیر خارج می‌شود.

مدل trades دارای pnl nullable، commission و swap با default صفر و close_time nullable است؛ net_pnl property محاسباتی است و ستون ذخیره‌شده نیست (T:126–159، 218–224). حساب شخصی موجودی اولیه/فعلی و ارز مستقل دارد: `i:\trade\MokTradeDesk\backend\app\models\trading.py:44–61`.

### مسیر متفاوت با نام broker_pnl

`finance_metrics.broker_pnl` معاملات را اصلاً نمی‌خواند:

```text
SUM(current_balance) - SUM(initial_balance)
+ SUM(withdrawal_from_broker) - SUM(deposit_to_broker)
```

همهٔ اجزا به همان ارز محدودند؛ تاریخ/فعال‌بودن فیلتر نمی‌شود (FM:31–45). داشبورد این مقدار را با funded_pnl جمع می‌کند و در `spendable_money.net_pnl` می‌گذارد (A:484–491، 564–569). این عدد الزاماً برابر مجموع معاملات بسته نیست؛ اگر current_balance با واقعیت معاملات reconcile نباشد، دو PnL متفاوت می‌شوند. موجودی فعلی از API قابل ورود/ویرایش است؛ شرط بسته‌بودن برای این فرمول قابل اعمال نیست و از خود فرمول نمی‌توان realized-only بودن آن را تضمین کرد.

شاهد ورود/ویرایش موجودی: `i:\trade\MokTradeDesk\backend\app\api\trading.py:55–60,75–78,192–200,210–227`.

## 2. Funded Prop PnL

در `_compute_real_pnl`، بخش `prop_stage_3.pnl` جمع net معاملات بسته است با JOIN از Trade به PropStage و PropAccount و شرایط:

- `stage_type = FUNDED_REAL`
- ارز PropAccount برابر ارز انتخابی
- `close_time IS NOT NULL`

مرحلهٔ ۱ و ۲ وارد نمی‌شوند. status مرحله فیلتر نیست؛ دادهٔ مرحلهٔ غیرفعال/failed نیز اگر FUNDED_REAL باشد وارد می‌شود. فیلتر صریح REAL_PROP اینجا نیست، ولی constraint مدل آن را اقتضا می‌کند. تابع مستقل `FM.funded_pnl` علاوه بر سه شرط فوق، REAL_PROP را صریحاً اعمال می‌کند (F:1435–1448؛ FM:56–72).

**این PnL کل حساب فاندشده پس از commission/swap است، نه سهم خالص کاربر.** درصد Profit Share، payout دریافت‌شده و دریافت‌نشده در آن ضرب/کسر نمی‌شوند.

سه مفهوم متفاوت:

| مفهوم | فرمول/دامنه |
|---|---|
| Funded trading PnL | جمع net معاملات بستهٔ FUNDED_REAL؛ ۱۰۰٪ نتیجهٔ حساب |
| سهم اقتصادی کاربر | در RuleEngine: closed_pnl × share/100 |
| سود قابل‌برداشت باقی‌مانده | max(closed_pnl × share/100 − total_withdrawn, 0) در RuleEngine |

R:116–121 و 225–233، سهم پیش‌فرض ۸۰٪ فقط وقتی None است. ضرر معامله در funded PnL منفی می‌ماند، ولی withdrawable در صفر محدود می‌شود؛ این‌ها قابل جایگزینی با هم نیستند.

`FM.prop_stage_3` ظاهراً فرمول قابل‌برداشت را تکرار می‌کند، اما query داخلی شرط close_time ندارد و همهٔ مراحل FUNDED_REAL را بدون فیلتر ارز می‌گیرد (FM:80–106). API نتیجه را با برچسب USDT برمی‌گرداند (F:1521–1527). جزئیات نقص در بخش ۱۰.

## 3. Net PnL Formula

فرمول واقعی در Python، SQL و property مدل یکسان است:

```text
net_pnl = (pnl or 0) + (commission or 0) + (swap or 0)
```

M:22–33؛ T:218–224. `_trade_net_expr` فقط این SQL helper را برمی‌گرداند؛ از net دوباره commission/swap کم نمی‌کند (F:1322–1324).

نمونه: pnl=100، commission=-7، swap=-3 ⇒ net=90. اگر swap=+2 باشد ⇒ net=95. هیچ abs یا منفی‌کردن خودکار در فرمول نیست. خود helper نیز closed-only نیست؛ فراخواننده باید شرط close_time را اعمال کند.

در `/real-pnl` هر بخش شخصی/پراپ ابتدا تا ۲ رقم گرد می‌شود و total جمع همان دو مقدار گرد‌شده است. `/net-profit` هزینه را نیز ابتدا گرد و سپس تفریق می‌کند. `/real-summary` جمع net دامنهٔ مشترک را یک بار گرد می‌کند؛ اختلاف بسیار کوچک ناشی از ترتیب گردکردن ممکن است (F:1447–1468، 1601–1615، 1670–1685). این گزارش آن را بدون الزام دقت مالی بیشتر باگ اعلام نمی‌کند.

## 4. Commission / Swap

- commission هزینه باید با علامت منفی ذخیره شود؛ مقدار مثبت در فرمول سود را زیاد می‌کند. swap می‌تواند مثبت یا منفی باشد.
- در payload دستی commission/swap Optional[float] هستند، نه مقدار الزاماً منفی؛ هنگام create مقدار داده‌شده یا صفر ذخیره می‌شود (`i:\trade\MokTradeDesk\backend\app\api\trades.py:59–62,83–86,771–772`).
- نرمال‌سازی ImportEngine اعداد commission/swap را می‌گیرد و در نبودشان صفر می‌گذارد؛ تبدیل هزینهٔ مثبت به منفی دیده نمی‌شود (I:338–339، 368–369). Soft4x مقدار Commission ورودی را می‌گیرد و swap را صفر می‌گذارد؛ parser MT4 مقادیر ستون‌های commission/swap را می‌خواند (`i:\trade\MokTradeDesk\backend\app\services\import_service.py:117–124,314–315,345–346`).
- از سورس به‌تنهایی نمی‌توان تضمین کرد P/L فایل ورودی gross است یا از قبل net، یا علامت commission فایل درست است. اگر pnl ورودی از قبل هزینه‌ها را شامل کند، فرمول آن‌ها را دوباره اعمال خواهد کرد؛ وقوع این حالت در دادهٔ واقعی NOT VERIFIED است.
- در مسیرهای اصلی Trade→Real PnL هر commission/swap فقط یک بار جمع می‌شود. اما اگر همان commission به‌صورت FinancialTransaction با نوع FEE نیز ثبت شود، `/net-profit` آن را دوباره کم می‌کند؛ `_expenses_total` هیچ reconciliation با related_trade_id یا commission ندارد (F:1472–1484).
- FinanceSyncService هیچ transaction خودکاری تولید نمی‌کند و همیشه صفر برمی‌گرداند؛ بنابراین ثبت خودکار duplicate Fee از این سرویس اثبات نمی‌شود: `i:\trade\MokTradeDesk\backend\app\services\finance_sync_service.py:20–28`.

## 5. Expenses

سه تعریف مستقل هزینه وجود دارد. جدول تمام انواع TransactionType را پوشش می‌دهد؛ commission/swap ستون Trade هستند، نه TransactionType.

| نوع/منبع | کسر در `/net-profit` | `/expenses` | `/reports/profit-loss` | تفسیر درست برای Personal Trading Net |
|---|---|---|---|---|
| Trade commission / swap | در net معامله از قبل اعمال شده | خیر | خیر | فقط یک بار؛ swap مثبت هزینه نیست |
| FEE | بله | بله | بله | هزینهٔ مستقل مرتبط؛ fee قبلاً داخل Trade نباید دوباره کم شود |
| PURCHASE | بله | بله | بله | خرید مرتبط با دامنه؛ خرید پراپ نباید بی‌تفکیک از سود شخصی بروکر کم شود |
| EXTERNAL_EXPENSE | خیر | بله | خیر | اگر هزینهٔ واقعی همان دامنه است باید در تعریف خالص لحاظ شود؛ خروج سرمایه لزوماً هزینه نیست |
| WITHDRAWAL | خیر | خیر | بله | برداشت اصل سرمایه/انتقال به مالک هزینهٔ معاملاتی نیست؛ withdrawal fee جداست |
| LOSS | خیر | خیر | بله | زیان Trade در net وجود دارد؛ کسر دوباره همان زیان غلط است؛ زیان مستقل نیازمند طبقه‌بندی است |
| TRANSFER | خیر | خیر | هزینه خیر؛ برخی مسیرها درآمد | انتقال داخلی نه هزینه است نه سود |
| CONVERT | خیر | خیر | خیر | تبدیل اصل پول هزینه نیست؛ fee واقعی جداست |
| ADJUSTMENT | خیر | خیر | خیر | اصلاح موجودی الزاماً هزینه نیست |
| DEPOSIT | خیر | خیر | درآمد | ورود اصل سرمایه سود نیست |
| PROFIT | خیر | خیر | درآمد | ثبت مالی سود/دریافت؛ معادل خودکار PnL معامله نیست |
| EXTERNAL_INCOME | خیر | خیر | درآمد فقط با حساب BANK | ورود خارجی می‌تواند سرمایه باشد، نه سود |

شواهد: enum در `i:\trade\MokTradeDesk\backend\app\models\finance.py:53–64`؛ F:1003–1008، 1242–1248، 1472–1484، 1770–1781؛ FR:33–51.

`/net-profit` تمام FEE/PURCHASE حذف‌نشدهٔ همان ارز را می‌گیرد: بدون فیلتر حساب شخصی، مرتبط‌بودن با بروکر، مرحلهٔ پراپ یا بازهٔ زمانی. انتخاب CategoryType.EXPENSE به‌تنهایی باعث ورود به این query نمی‌شود.

`/expenses` سه نوع FEE/PURCHASE/EXTERNAL_EXPENSE را به bucketهای prop_purchase، prop_subscription، exchange_fee، withdrawal_fee و other تقسیم می‌کند. تشخیص bucket از متن نام دسته/توضیح و نوع حساب است، نه یک ExpenseType دقیق؛ مثلاً هر مبلغ واجد شرایط در حساب EXCHANGE ممکن است exchange_fee نام بگیرد (F:1784–1819).

تعریف چهارم در خلاصهٔ Cash Flow، cash_flow=expense است: FEE/PURCHASE/LOSS/WITHDRAWAL/EXTERNAL_EXPENSE و انتقال BANK→غیربانک. این تعریف خروج وجه است، نه هزینهٔ اقتصادی معامله (`i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:154–186`؛ F:1369–1379). نباید آن را جایگزین Expenses در Net Profit کرد.

## 6. Net Profit

### `/api/finance/net-profit`

```text
Real = Closed Personal Broker Net PnL + Closed FUNDED_REAL Net PnL
Expenses = SUM(non-deleted FEE + PURCHASE, same currency)
Net Profit = round(Real - Expenses, 2)
```

ارز پیش‌فرض USDT و خروجی by_currency شامل USDT و IRR است؛ تبدیل نرخ ارز ندارد. بازهٔ زمانی یا فیلتر personal-only ندارد (F:1663–1688). UI همین مقدار را با عنوان «سود خالص» نمایش می‌دهد و فرمول دیگری روی آن اجرا نمی‌کند: `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:1255–1270`.

**نتیجه: این endpoint، Personal Broker Net Profit نیست.** هم ۱۰۰٪ PnL پراپ را شامل می‌شود و هم هزینه‌های پراپ/سایر حساب‌ها را کم می‌کند. بدون تخصیص هزینه به دامنه، محاسبهٔ دقیق Personal Net از این خروجی ممکن نیست.

مثال بدون هزینه: شخصی=100، funded=1000، share=80٪، payout=0 ⇒ API عدد 1100 می‌دهد؛ personal trading net برابر 100 است و سهم تحقق‌یافتهٔ پراپ در معیار سهم کاربر 800، نه 1000. در معیار دریافت نقدی نیز هنوز payout صفر است. این تفاوت، چند قرارداد مالی متفاوت است؛ سود تجمیعی حساب‌ها را نباید سود نقدی یا شخصی نامید.

### `/api/finance/reports/profit-loss`

فرمول متفاوت: درآمد تراکنش‌های `is_bank_income` منهای WITHDRAWAL/LOSS/FEE/PURCHASE. هیچ Trade PnL مستقیماً جمع نمی‌شود. DEPOSIT و PROFIT برای همهٔ حساب‌ها، EXTERNAL_INCOME بانکی و TRANSFER غیربانک→بانک درآمدند. بنابراین شارژ سرمایه یا انتقال داخلی می‌تواند «net_profit» را افزایش دهد؛ این خروجی در بهترین حالت گزارشی با قواعد جریان پول است، نه Trading Net Profit (F:1220–1316؛ FR:33–51).

پارامتر year فقط سال monthly را انتخاب می‌کند؛ total_income/total_expense/net_profit و trend از همهٔ سال‌ها محاسبه می‌شوند. این دامنهٔ متفاوت در کنار year باید در تفسیر اعداد لحاظ شود (F:1235–1256، 1275–1315).

## 7. Closed Trade Compliance

| مسیر بررسی‌شده | اجرای شرط بسته‌بودن | نتیجه برای Open Trade + stored pnl |
|---|---|---|
| F._compute_real_pnl شخصی و پراپ | SQL close_time IS NOT NULL | حذف |
| F./net-profit | به‌واسطهٔ _compute_real_pnl | حذف از جزء Trade |
| F./real-summary | SQL is_closed در base_q | حذف |
| FM.funded_pnl | SQL close_time IS NOT NULL | حذف |
| Analytics dashboard aggregation | _scope_filter قبل از SUM شرط closed دارد | حذف؛ صرف نگاه به SUM کافی نیست |
| PropRuleEngine closed_pnl/withdrawable | فیلتر Python close_time is not None | حذف؛ floating_pnl جدا برای equity محاسبه می‌شود |
| FM._stage_net_pnl → prop_stage_3 | **ندارد** | **وارد سود قابل‌برداشت می‌شود** |
| I.sync_prop_stage_profit | **ندارد** | **وارد current_profit ذخیره‌شده می‌شود** |
| FM.broker_pnl | مبتنی بر balance، نه Trade | تضمین realized-only از این تابع ممکن نیست |
| reports/profit-loss | فقط transactions | شرط Trade موضوعیت ندارد؛ PROFIT دستی قابل ورود است |

شواهد: F:1443،1457،1593،1670؛ FM:68،80–105؛ A:103–126،337–350؛ R:116–121،232–233؛ I:818–829.

پاسخ به «آیا در تمام مسیرها اعمال می‌شود؟»: **خیر**. مسیرهای اصلی Real PnL مالی رعایت می‌کنند؛ helper سود قابل‌برداشت و sync سود مرحله نقض دارند. نمونهٔ فرضی funded با فقط معاملهٔ باز pnl=100، commission=-10 و share=80٪: Real PnL=0 و RuleEngine withdrawable=0؛ اما FM.prop_stage_3 بدون برداشت قبلی 72 گزارش می‌کند. sync مرحلهٔ ACTIVE نیز current_profit=72 می‌نویسد.

sync در import و مسیرهای تغییر Trade فراخوانی می‌شود (I:1019؛ `i:\trade\MokTradeDesk\backend\app\api\trades.py:581,653,684,788`). گزارش پراپ current_profit ذخیره‌شدهٔ مراحل FUNDED_REAL را جمع می‌کند (`i:\trade\MokTradeDesk\backend\app\api\prop.py:1281–1283`). پس این صرفاً helper بلااستفاده نیست.

## 8. Personal vs Prop Separation

- مدل Trade با constraint دو دامنه را جدا می‌کند؛ در دادهٔ مطابق مدل، یک معامله هم‌زمان در هر دو دسته نیست (T:182–193).
- `/real-pnl` دو بخش broker و prop_stage_3 را جدا نمایش می‌دهد؛ UI نیز جدول تفکیکی دارد (`i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:1225–1247`).
- `/net-profit` عمداً total دو دامنه را می‌گیرد و هزینه‌ها را بدون تخصیص دامنه کم می‌کند؛ جداسازی سطح مدل به معنی جداسازی سود خالص نیست.
- Profit Share و total_withdrawn وارد broker.pnl نمی‌شوند. payout به FinancialAccount می‌رود، نه PersonalTradingAccount؛ لذا در broker trade PnL ورود مستقیمی ندارد.
- اجرای واقعی PayoutService در RECEIVED نوع **PROFIT برای هر مقصد** ثبت می‌کند؛ برخلاف docstring قدیمی که برای غیربانک ADJUSTMENT می‌گوید. سپس total_withdrawn را افزایش می‌دهد (P:149–152،182–204). معیار این گزارش بدنهٔ اجراست، نه کامنت.
- payout به `/net-profit` اضافه نمی‌شود، چون PROFIT در expense query نیست و income transaction نیز در فرمول آن جمع نمی‌شود؛ بنابراین جمع مستقیم «funded trade PnL + payout» در این endpoint رخ نمی‌دهد. ولی سود دریافت‌نشدهٔ کل پراپ از ابتدا در جزء Real حضور دارد.
- F./spendable-assets مقدار prop_stage_3 را جدا برمی‌گرداند و در total موجودی‌های شخصی وارد نمی‌کند؛ FM helper آن همچنان ایراد closed/currency دارد (F:1521–1528).

## 9. Double Counting

### کنترل‌های صحیح

۱. commission/swap در helperهای اصلی هرکدام یک بار اعمال می‌شوند؛ هیچ تفریق مجدد خودکار در `_compute_real_pnl` دیده نشد.

۲. LOSS و WITHDRAWAL در هزینهٔ `/net-profit` نیستند؛ زیان معاملاتی قبلاً در net وارد شده و برداشت اصل سرمایه هزینهٔ اضافی نمی‌شود.

۳. payout به PnL معاملات در `/net-profit` اضافه نمی‌شود. FinanceSyncService no-op است و transaction آینه‌ای خودکار نمی‌سازد.

۴. در analytics.total_balance، broker_balance دوباره با broker_pnl جمع نشده است؛ فرمول broker_balance+funded_pnl است (A:564–569). این کنترل عدم تکرار بروکر، برابری عدد با «پول قابل خرج شخصی» را تضمین نمی‌کند.

### خطرها و مثال‌های شرطی

- commission=-10 در Trade و FEE=10 بابت همان هزینه: برای pnl=100، net معامله=90 ولی Net Profit=80. هیچ شرط related_trade_id برای حذف fee تکراری در F:1477–1483 نیست. وقوع دادهٔ تکراری تأیید نشده است.
- pnl فایل از قبل net باشد و commission/swap جدا هم پر باشند: اعمال دوبارهٔ هزینه؛ قرارداد فایل واقعی بررسی نشده است.
- payout=80 به Wallet با PROFIT و انتقال همان 80 به Bank: در reports/profit-loss هر دو رویداد income می‌شوند و درآمد=160. این مسیر از P:190–204 و FR:37–50 قابل استنتاج است؛ در `/net-profit` این تکرار خاص وجود ندارد.
- جمع دستی `/net-profit` با payout یا profit-loss صحیح نیست: نتایج معاملاتی، سهم کاربر و دریافت نقدی ممکن است یک رویداد را با مبناهای مختلف نشان دهند.
- Funded PnL کامل به‌جای share، «دوباره‌شماری» ریاضی نیست؛ **بیش‌برآورد سهم شخص در صورت تفسیر شخصی** است. این دو نقص نباید یکی نامیده شوند.

## 10. Confirmed Bugs

### B1 — Open Trade در سود قابل‌برداشت پراپ (High)

FM._stage_net_pnl شرط closed ندارد و prop_stage_3 از آن استفاده می‌کند؛ برخلاف RuleEngine و Real PnL. مثال 72 واحد بخش ۷ از سورس مستقیماً به دست می‌آید. شواهد: FM:80–106؛ R:116–121،232–233؛ F:1523.

### B2 — Open Trade در current_profit مرحله (High)

sync_prop_stage_profit تمام معاملات مرحله را جمع می‌کند و برای ACTIVE ذخیره می‌کند؛ stored pnl باز وارد سود می‌شود. گزارش مجموع سود پراپ نیز این فیلد را می‌خواند. شواهد: I:818–829؛ `i:\trade\MokTradeDesk\backend\app\api\prop.py:1281–1283`. این نقص broker trade PnL اصلی را آلوده نمی‌کند.

### B3 — هزینه‌های نمایش‌داده‌شده با هزینهٔ Net Profit برابر نیست (High)

`/expenses` شامل EXTERNAL_EXPENSE است ولی `/net-profit` آن را حذف می‌کند. مثال: broker net=100، EXTERNAL_EXPENSE=30، سایر اجزا صفر ⇒ expenses.total=30 ولی net-profit.expenses=0 و net_profit=100. ناسازگاری مجموعهٔ هزینه‌ها قطعی است؛ اینکه هر خروج خارجی باید هزینهٔ سود خالص باشد نیازمند قرارداد مالی است. شواهد: F:1472–1484،1668–1685،1773–1779،1814–1819.

### B4 — اختلاط ارز در سود قابل‌برداشت پراپ (High، مشروط به وجود مراحل چندارزی)

FM.prop_stage_3 هیچ فیلتر/تبدیل ارزی ندارد؛ F:1523 خروجی را USDT معرفی می‌کند. سود مرحلهٔ IRR می‌تواند با USDT جمع و USDT نامیده شود. شواهد: FM:99–105؛ F:1521–1527. این نقص در `_compute_real_pnl` که ارز را فیلتر می‌کند وجود ندارد.

### B5 — سهم صفر در sync به ۸۰٪ تبدیل می‌شود (Medium)

I:826 از `(profit_share_percentage or 80.0)` استفاده می‌کند؛ مقدار صفر را ۸۰ تفسیر می‌کند. R:228 و FM:103 فقط None را default می‌کنند و صفر را حفظ می‌کنند. اختلاف فرمول سورس قطعی است؛ وجود/امکان ثبت صفر در دادهٔ محیط اجرا بررسی نشده است.

### B6 — درآمد تکراری payout غیربانکی و انتقال بعدی در profit-loss (High)

ثبت payout به غیربانک نیز PROFIT است و گزارش هر PROFIT و سپس TRANSFER غیربانک→بانک را درآمد می‌شمارد. net_profit گزارش تراکنشی برای همان دریافت می‌تواند دو برابر شود. شواهد: P:182–204؛ FR:37–50؛ F:1242–1256،1302–1310. این یافته مربوط به گزارش تراکنشی است، نه فرمول Trade Net PnL.

**محدودیت معنایی مهم:** `/net-profit` یک شاخص ترکیبی Personal+Funded است و Personal-only نیست. این رفتار قطعی است؛ «اشتباه بودن جمع» وابسته به عنوان/قرارداد محصول است، اما استفاده از آن به‌عنوان Personal Broker Net Profit با خواستهٔ تفکیک شخصی سازگار نیست. برداشت اصل سرمایه به‌عنوان هزینه یا واریز سرمایه به‌عنوان profit در گزارش تراکنشی نیز برای سنجش سود اقتصادی معتبر نیست.

## 11. NOT VERIFIED

- هیچ DB query، API call، اجرای برنامه یا تست انجام نشد؛ تمام مثال‌ها تحلیل شرطی سورس‌اند.
- وجود معاملات باز با pnl ذخیره‌شده، feeهای تکراری، سهم صفر، مراحل چندارزی و میزان اثر مالی واقعی مشخص نیست.
- اجرای migration و constraint classification در دیتابیس واقعی، orphan/legacy records و یکپارچگی داده بررسی نشدند. بدون شاهد داده، اختلاط REAL_PERSONAL/REAL_PROP به علت نبود شرط صریح test_type اعلام نمی‌شود.
- reconciliation موجودی بروکر با معاملات بسته و گردش‌ها، و ورود floating PnL احتمالی به current_balance تأیید نشد؛ فقط اختلاف روش محاسبه ثابت شد.
- gross/net بودن P/L فایل‌های واقعی، قرارداد علامت commission، رفتار فایل‌های خاص بروکر و ازقلم‌افتادن هزینه در ورودی‌ها تأیید نشد.
- طبقه‌بندی اقتصادی هر PURCHASE/EXTERNAL_EXPENSE و تخصیص هزینه به شخصی یا پراپ از type به‌تنهایی قابل تعیین نیست؛ قرارداد هزینه‌های سرمایه‌ای/مصرفی خارج از این سورس بررسی نشد.
- بررسی حاضر مسیرهای مالی، helperهای متصل، داشبورد مرتبط و تولید/مصرف سود پراپ را پوشش می‌دهد؛ ادعای ممیزی جامع همهٔ exportها، محاسبات ریسک، اسکریپت‌های خارجی یا هر مسیر تحلیلی پروژه مطرح نمی‌شود.
- هیچ نتیجهٔ گزارش قبلی به‌عنوان شاهد مستقل استفاده نشد. کامنت‌های ناسازگار با بدنهٔ کد، به‌ویژه payout، مبنای نتیجه‌گیری نیستند.

## 12. Risk Level

**Overall: High — صحت سود قابل‌برداشت، تعریف هزینه و تفسیر Personal Net Profit.**

- هستهٔ Real PnL شخصی و فاندشده: فرمول net درست و closed-only است؛ Open Trade دارای stored pnl را حذف می‌کند.
- ریسک بالا: ورود open pnl به helper سود قابل‌برداشت و current_profit پراپ؛ اختلاف هزینهٔ `/expenses` و `/net-profit`؛ ترکیب چندارزی helper؛ درآمد تکراری payout در گزارش تراکنشی.
- ریسک تفسیری بالا: سود کل FUNDED_REAL معادل سهم/دریافت کاربر نیست؛ endpoint سود خالص شخصی مستقل با تخصیص هزینه در مسیر بررسی‌شده وجود ندارد.
- ریسک وابسته به داده: FEE تکراری با commission، pnl ازقبل-net، موجودی بروکر reconcile‌نشده و دادهٔ legacy؛ وقوع واقعی تأیید نشد.

نتیجهٔ نهایی: **Personal Broker PnL را از بخش broker گزارش Real PnL بگیرید، نه از total یا net-profit ترکیبی.** Funded PnL، Profit Share، payout و unreceived profit چهار مفهوم جدا هستند. فرمول پایهٔ `pnl + commission + swap` تأیید شد، اما یکسان‌بودن نام «Net Profit» در خروجی‌ها به معنی یکسان‌بودن تعریف یا دامنه نیست. این ممیزی هیچ Fix انجام نداده است.