# پیشنهاد بازطراحی Dashboard ژورنال معاملات

**وضعیت:** مرحلهٔ کشف و وایرفریم؛ این سند طرح است، نه مجوز تغییر کد یا حذف قابلیت‌ها.  
**دامنهٔ بررسی:** `frontend/src/pages/DashboardPage.tsx`، API و محاسبات مرتبط، اجزای رابط، و `DASHBOARD_FULL_AUDIT_2026-10-09.md`.  
**محدودیت اجرا:** در این مرحله فقط همین گزارش ایجاد می‌شود. هیچ فایل کد/تست، migration، commit یا push در دامنه نیست.

## ۱) خلاصهٔ یافته‌ها

Dashboard فعلی یک صفحهٔ ترکیبی است: عملکرد معاملات (واقعی، دیروز/امروز و عملکرد دوره‌ای)، equity و نمودارهای توزیع، وضعیت/هشدار Prop، وضعیت چند نسخهٔ Backtest و چند پنل مالی در کنار Header و Market Session است. این بخش‌ها همگی دادهٔ واحد و context مشترک ندارند. ممیزی موجود نیز هشدار می‌دهد که تاریخ، دامنه و جمعیت بعضی کارت‌ها و جدول‌ها با هم فرق دارند؛ بازطراحی باید ابتدا context شفاف و closed-only را تثبیت کند، نه اینکه صرفاً چیدمان را عوض کند.

طرح توصیه‌شده: هدر فعلی عیناً حفظ شود؛ پس از آن فیلتر performance و برچسب context، پنج KPI هم‌دامنه، نمودار Equity بسته‌شده، و جدول معاملات بسته‌شده قرار گیرد. پنل‌های مفیدِ فعلی حذف نشوند: در فاز نخست به بخش‌های ثانویهٔ صفحه منتقل/گروه‌بندی شوند یا به صفحهٔ مالک لینک شوند، اما تصمیم حذف یا انتقال نهایی پس از تعیین مالک و کاربرد آن‌ها گرفته شود. هیچ open trade، floating PnL یا قیمت زنده وارد بخش ژورنال نشود.

## ۲) ساختار واقعی فعلی

### Header و کنترل‌ها

- در `DashboardPage.tsx` هدر داخلی شامل پیام خوش‌آمدگویی/تاریخ‌وساعت، `MarketSessionWidget`، دسترسی‌های مربوط به پلاگین/ویجت، تنظیمات/Theme، Refresh و PDF است. بخش هدر/فیلتر در `ErrorBoundary` مستقل قرار دارد.
- ساعت با timer یک‌ثانیه‌ای تازه می‌شود؛ `MarketSessionWidget` خودش زمان/بازار، بازه‌های معاملاتی، اخبار و بازه‌های Poursamadi را مدیریت می‌کند. این‌ها «دادهٔ تاریخی ژورنال» نیستند.
- فیلترهای بازه (today, yesterday, week, month, quarter, year, all, custom)، دامنه (real/backtest/forward/all) و ارز وجود دارند؛ بخشی از انتخاب‌ها در `localStorage` نگه‌داری می‌شود. تبدیل تاریخ سفارشی شمسی در صفحه انجام می‌شود.
- PDF از `/api/export/dashboard/pdf` با تاریخ، دامنه و ارز درخواست می‌شود؛ گزارش ممیزی موجود ناسازگاری context بین PDF و برخی پنل‌های مستقل را ثبت کرده است.

### بخش‌های داده‌محور موجود

1. عملکرد اصلی/آماری و نمودارهای win/loss و توزیع PnL؛ endpoint اصلی `GET /api/analytics/dashboard` است.
2. Today و Yesterday و خلاصهٔ Real که درخواست‌های جداگانه دارند.
3. وضعیت مراحل فعال Prop، progress و هشدارهای Prop.
4. کارت‌ها/نمودارهای مالی: موجودی، cashflow، حساب‌ها، net profit، دارایی شخصی و روند دارایی؛ با endpointهای `/api/finance/*` و component `FinancialAssetBalances`.
5. عملکرد Backtest مستقل: فهرست نسخه‌ها از `/api/strategies/versions/all` و درخواست dashboard جداگانه با `scope=backtest`, `currency=USDT`, `version_id`. فیلترهای اصلی الزاماً بر این درخواست اعمال نمی‌شوند.
6. Equity chart موجود `EquityCurveChart` از `equity_curve` آمادهٔ backend استفاده می‌کند؛ fallback آن در نبود دادهٔ آماده فقط `pnl` را جمع می‌کند و commission/swap را وارد نمی‌کند، پس برای قرارداد net نباید مسیر fallback مبنای دادهٔ جدید شود.
7. بخش‌های دیگری مانند اهداف/goal bars و ویجت‌های زمینه‌ای نیز در صفحه هستند؛ audit قبلی دربارهٔ hardcode/مبنای هدف و ناهمگونی context هشدار داده است.

### وضعیت بارگذاری و خطا

- بارگذاری اصلی از چند درخواست موازی انجام می‌شود و guard برای پاسخ دیررس وجود دارد؛ backtest مسیر بارگذاری و guard جداگانه دارد.
- صفحه `DashboardSkeleton` دارد. شکست بارگذاری اصلی، toast و حالت خطای کل‌صفحه در نبود دادهٔ قبلی می‌دهد؛ خطاهای بعضی پنل‌های فرعی رفتار مستقل دارند. «دادهٔ صفر» و «خطا/دادهٔ بارگذاری‌نشده» باید متمایز بمانند.
- `ErrorBoundary` برای گروه‌هایی از کارت‌ها وجود دارد؛ آن را حفظ کنید تا خطای پنل فرعی صفحهٔ ژورنال را از کار نیندازد.

## ۳) نقشهٔ پیشنهادی صفحه، از بالا به پایین

1. **Header فعلی بدون تغییر**: هیچ جابه‌جایی، حذف یا بازطراحی؛ تمام اجزای تصریح‌شده در نیازمندی حفظ شوند.
2. **نوار فیلتر فشردهٔ ژورنال**: بازهٔ تاریخ، دامنهٔ موجود (real/backtest/forward/all)، ارز معتبر و انتخاب‌های موجود مرتبط با نسخه/حساب/مرحله در صورت پشتیبانی واقعی API. زمان منطقه/معنای تاریخ (تاریخ بسته‌شدن) در متن کم‌رنگ و واضح. کنترل PDF/Refresh همان رفتار فعلی و context یکسان.
3. **پنج KPI اصلی، همگی از یک مجموعهٔ معاملات بسته‌شده**: Net Closed PnL، Win Rate با برد/باخت، Profit Factor وضعیت‌دار، Max Drawdown با تعریف صریح، Closed Trades.
4. **Equity Curve اصلی**: از همان فیلترها و پاسخ هم‌دامنه؛ closed-only و مرتب‌شده با `close_time,id`. نقطهٔ سرمایهٔ شروع و مبنای آن مشخص باشد؛ عنوان محور X «معاملهٔ بسته‌شده» یا تاریخ واقعی، نه «روز» اگر هر نقطه یک معامله است.
5. **آخرین معاملات بسته‌شده**: جدول کوتاه با همان context؛ ترتیب `close_time DESC, id DESC`، محدودیت تعداد روشن، لینک مشاهدهٔ همه با فیلترهای قابل انتقال. ستون‌ها فقط دادهٔ موجود: زمان بسته‌شدن، نماد، جهت، استراتژی/نسخه، net PnL، ارز و در صورت کیفیت داده R. بدون open trades.
6. **بخش‌های تکمیلی حفظ‌شده، با جداسازی بصری و context مستقل**: امروز/دیروز، win-loss pie و PnL distribution، Prop/risk، Backtest نسخه‌ای، Finance/assets/cashflow، اهداف و ویجت‌های موجود. تصمیم دربارهٔ محل دقیق (پایین صفحه یا لینک به صفحهٔ مالک) پس از بررسی کاربرد، وابستگی و خواست کاربر انجام شود؛ تا آن زمان حذف نشوند. پنل‌هایی که با فیلتر بالایی هماهنگ نیستند باید برچسب «context مستقل» داشته باشند و در ردیف KPI/Equity/Recent Trades قرار نگیرند.

## ۴) حفظ/جابجایی/اصلاح/حذف پیشنهادی

| بخش/کامپوننت فعلی | اقدام پیشنهادی | دلیل/قید |
|---|---|---|
| Header و `MarketSessionWidget` و پلاگین‌ها/ویجت‌ها، Theme/Settings، Refresh، PDF | حفظ عیناً | الزام قطعی؛ Market Session نمایندهٔ بازار زنده است نه محاسبهٔ PnL زنده. |
| نوار فیلتر تاریخ/دامنه/ارز | حفظ، فشرده‌سازی صرفاً در فاز طراحی نهایی | فیلترهای موجود باید منبع واحد KPI/Equity/جدول شوند؛ اعتبار دامنه و ارز نیاز به تطبیق backend دارد. |
| کارت‌های آماری فعلی / `StatCard` | جابه‌جایی و اصلاح محتوا | پنج KPI مشخص، بدون sparkline تزئینی یا مقادیر پیش‌فرض؛ بررسی `StatCard` چون در نبود داده sparkline ساختگی دارد و کارت clickable است. |
| `EquityCurveChart` | حفظ و اصلاح قراردادی/نمایشی | کامپوننت موجود است؛ محور/tooltip باید معاملهٔ بسته‌شده و شروع را درست توصیف کند؛ fallback مبتنی بر pnl تنها ناامن است. |
| `WinLossPieChart`, `PnLDistributionChart` | حفظ به‌عنوان تحلیل تکمیلی | معنادارند، اما اولویت بصری بعد از KPI و equity؛ دادهٔ بسته و context مشترک. |
| Today/Yesterday/period cards | حفظ در بخش ثانویه | APIهای مجزا دارند و ممکن است window/date semantics متفاوت داشته باشند؛ تا یکسان‌سازی، از KPIهای اصلی جدا. |
| Prop progress، alertها و بخش risk | حفظ مشروط به کاربرد ژورنال و دادهٔ واقعی | در زیربخش مجزا؛ مقادیر hardcoded یا state مالی جاری وارد performance نمی‌شوند. شرایط در بخش Prop/Risk آمده است. |
| پنل‌های Finance و assets/cashflow/net profit | حفظ به‌عنوان خلاصهٔ مالی جدا یا لینک به Finance | دفتر مالی و PnL ژورنال دو مفهوم‌اند؛ نباید payout، انتقال، سرمایه یا هزینه را دوباره به سود معامله اضافه کرد. |
| Backtest selector/summary مستقل | حفظ، اما context جدا و آشکار | فیلتر اصلی را فعلاً مستقل می‌گیرد؛ یا sync قراردادی لازم دارد یا عنوان/فیلتر مستقل. هیچ ادغام خام با Real مجاز نیست. |
| Open-trades table/banner و Floating PnL (اگر در مسیر فعلی/شاخهٔ فعال دیده شود) | از Dashboard ژورنال حذف از نمایش اصلی؛ قابلیت را در صفحهٔ معاملات/مالک حفظ کنید | محصول برای معاملات بسته‌شده است؛ این داده نباید KPI/نمودار یا وضعیت صفحهٔ اصلی را آلوده کند. حذف قابلیت از برنامه پیشنهاد نمی‌شود. |
| goal bars / مقادیر hardcoded | حذف از چیدمان نهایی فقط پس از اثبات بی‌منبع بودن؛ فعلاً قرنطینه و ردیابی | مقدار تزئینی/هدف بدون منبع قابل اتکا metric نیست. جایگزینی فقط با هدف واقعی تنظیم‌شده و فرمول/واحد آشکار. |
| News، ساعات سشن، plugin و ویجت‌های سفارشی | حفظ | الزام header و قابلیت موجود؛ مستقل از تاریخچهٔ معامله و بدون تأثیر بر شاخص‌ها. |

## ۵) تعریف KPIها و منبع داده

**قاعدهٔ مشترک:** فیلترهای تاریخ بر `close_time` اعمال شوند، فقط `close_time IS NOT NULL`، scope/currency و هر selector واقعی حساب/مرحله/نسخه روی همان query اعمال شود؛ برابری predicate بین KPI، equity، جدول و export معیار پذیرش است. پاسخ فعلی `GET /api/analytics/dashboard` در `backend/app/api/analytics.py` منبع اصلی این داده‌هاست؛ client در `frontend/src/api/client.ts` آن را صدا می‌زند.

| KPI | تعریف دقیق پیشنهادی | داده/ریسک موجود |
|---|---|---|
| Net Closed PnL | `Σ net_i` فقط برای معاملات بسته‌شدهٔ فیلترشده؛ قرارداد net فعلی `net = pnl + commission + swap` (یا helper SQL معادل در پروژه). نمایش با ارز انتخاب‌شده، علامت و دقت مالی. | backend aggregation از `_net_expr()` استفاده می‌کند؛ اما در کد خوانده‌شده `tnp = SUM(net)` از `scoped_q` محاسبه می‌شود، یعنی ممکن است معاملهٔ باز هم وارد عدد شود؛ اصلاح/مصرف closed-only باید پیش از نمایش قطعی شود. net را از finance یا payout جمع نزنید. |
| Win Rate + برد/باخت | برد = تعداد closed با `net > 0`؛ باخت = closed با `net < 0`؛ سر‌به‌سر = closed با `net == 0`. `win rate = wins / closed_count × 100`؛ مخرج شامل breakeven است، مطابق API فعلی. نمایش wins/losses و در صورت نیاز breakeven به‌عنوان شمارش فرعی، نه تغییر پنهانی denominator. | `summary` endpoint، win/loss condition روی بسته و نرخ ۰–۱۰۰ را ارائه می‌کند؛ رفتار صفر-معامله به‌صورت «—/بدون داده» بهتر از القای عملکرد ۰٪ است. |
| Profit Factor | مجموع net مثبت معاملات بسته ÷ قدرمطلق مجموع net منفی معاملات بسته. زیان‌ها باید با همان net شامل کارمزد/سواپ باشند. | API `metrics.profit_factor_from_sums`: نسبت عادی در صورت loss؛ سود بدون loss sentinel عددی `999.0`؛ بدون سود و زیان `0.0`. helper وضعیت‌دار `profit_factor_status` نیز در کد هست اما response فعلی الزاماً آن را نمی‌دهد. UI نباید sentinel را با نسبت واقعی بسیار بزرگ اشتباه بگیرد؛ وضعیت `finite / no_losses / undefined / no_data` لازم است. |
| Max Drawdown | پیشنهاد label صریح: «بیشترین افت بسته‌شده از اوج» = بیشینهٔ `peak_equity - equity` در منحنی مرتب معاملات بسته؛ اگر نمایش percentage، همان افت ÷ peak ×100 در لحظهٔ افت. | `calculate_peak_to_trough_dd` این مقدار را می‌دهد؛ endpoint فعلی `max_drawdown = max(peak_to_trough.dd, static_dd.dd)`، یعنی ممکن است افت از سرمایهٔ شروع (static) را با peak-to-trough ترکیب کند. لازم است قرارداد محصول تعیین کند KPI برابر کدام تعریف است؛ نام مبهم «Max Drawdown» بدون تعریف پذیرفته نیست. baseline برای Real/All می‌تواند از initial balance حساب‌ها/مراحلِ معاملات انتخاب‌شده جمع شود و برای simulation مقدار فرضی 10,000/fallback داشته باشد (جزئیات در audit). baseline و منبعش باید همراه نمودار معلوم باشد. |
| Closed Trades | شمار رکوردهای بسته‌شده در مجموعهٔ مشترک (`close_time IS NOT NULL`)؛ شامل برد، باخت و breakeven؛ فاقد بازها. | API `summary.closed_trades`؛ از `total_trades` که در query فعلی ممکن است بسته و باز را بشمارد جداست. مقدار صفر با state خالی نمایش داده شود. |

**Equity:** backend در حال حاضر توالی معاملات بسته را مرتب و `equity_curve` را از سرمایهٔ اولیه + تجمع net آن‌ها می‌سازد؛ `EquityCurveChart` می‌تواند سری آماده را مصرف کند. باید بررسی و تست شود که خروجی API نقطهٔ شروع و داده‌های خارج از بازه را چگونه نمایش می‌دهد. فقط منحنی تحقق‌یافته، نه mark-to-market، floating یا محاسبهٔ زنده.

**آخرین معاملات:** API موجودِ dashboard (یا endpoint فهرست معاملات با فیلترهای هم‌ارز) باید closed-only، تاریخ، دامنه، ارز و selector واحد را اعمال کند. گزارش قدیمی `DASHBOARD_AUDIT.md` می‌گوید جدول قبلی ممکن است آخرین ۱۰ معامله را با predicate و scope متفاوت بگیرد؛ پیش از reuse parity را اثبات کنید. برای net سطر نیز از تعریف مشترک استفاده شود، نه جمع دوبارهٔ commission/swap روی net آماده.

## ۶) فیلترها و اثر آن‌ها

- **بازهٔ تاریخ:** today/yesterday/week/month/quarter/year/all/custom موجود حفظ شود. معنا: تاریخ بسته‌شدن، نه open date یا زمان import. KPIها، closed-only equity و recent table حتماً به‌روزرسانی شوند. مرز روز/ماه/سال باید timezone/تقویم مشخص و یکسان (پیشنهاد: `Asia/Tehran`، مطابق منطق تاریخ برنامه) داشته باشد؛ audit به اختلاف Tehran/UTC و inclusive end date اشاره می‌کند.
- **Scope:** real/backtest/forward/all موجود حفظ شود، اما semantics واقعی query و کدام گروه‌های real را شامل می‌کند باید از `_scope_filter`/تست‌ها مستند شود. scope روی KPI، curve و table یکی باشد. `all` نباید باعث جمع ارزهای ناهم‌جنس شود.
- **Currency:** فقط ارزهای سازگار با query موجود؛ از تبدیل ضمنی یا جمع USDT و IRR اجتناب شود. فیلتر روی هر سه بخش اصلی یکسان باشد. تعیین تکلیف simulation که معمولاً USDT است لازم است.
- **نسخه/حساب/مرحله:** فیلتر موجود نسخهٔ Backtest مستقل است؛ انتقالش به نوار اصلی فقط وقتی مجاز است که API، UX و real/account semantics آن روشن باشد. selector اختیاری باید context را آشکار کند و به curve/table/PDF منتقل شود.
- **Refresh:** refresh باید یک درخواست/نسخهٔ context برای همهٔ بخش‌های وابسته داشته باشد؛ پاسخ دیررس فیلتر قبلی نباید state جدید را overwrite کند. دادهٔ مستقل Finance/Prop/Widget فقط با برچسب context خود refresh شود.
- **بخش‌های غیر وابسته:** Market Session، خبر و ساعت از فیلتر ژورنال پیروی نمی‌کنند؛ مالیِ current balance نیز تاریخچهٔ بسته‌شدن نیست. جداسازی context صریح باشد.

## ۷) وایرفریم متنی

```text
┌──────────────────────────────────────────────────────────────┐
│ Header فعلی (بدون تغییر؛ greeting/time/session/plugins/theme │
│ settings/refresh/PDF و widgetهای موجود)                       │
├──────────────────────────────────────────────────────────────┤
│ فیلتر تاریخ | Scope | Currency | selector معتبر | context    │
├──────────────┬──────────────┬────────────┬─────────┬─────────┤
│ Net Closed   │ Win Rate     │ Profit     │ Max DD  │ Closed  │
│ PnL          │ W / L        │ Factor     │ تعریف‌شده│ Trades  │
├─────────────────────────────────────┬────────────────────────┤
│ Equity Curve (closed, محور دقیق)    │ راهنما: baseline/بازه │
├──────────────────────────────────────────────────────────────┤
│ آخرین معاملات بسته‌شده؛ همان فیلترها؛ مشاهدهٔ همه             │
├──────────────────────────────────────────────────────────────┤
│ تحلیل‌های تکمیلی و بخش‌های فعلی (Prop / Backtest / Finance /  │
│ Today-Yesterday / widgets) با context مستقل و بدون حذف خودکار │
└──────────────────────────────────────────────────────────────┘
```

## ۸) واکنش‌گرایی و Theme

- **دسکتاپ عریض:** پنج KPI در یک ردیف در صورت عرض کافی؛ در عرض میانی ۳+۲ یا ۲+۲+۱ بدون کارت باریک؛ Equity تمام‌عرض یا نسبت تقریبی 2:1 با context/legend کوچک. جدول تمام عرض با ستون‌های ضروری و بدون overflow صفحه.
- **صفحهٔ کوچک:** کنترل‌ها wrap/stack و دسترس‌پذیر؛ KPI در grid دو ستونه (آخرین کارت تمام‌عرض یا جریان طبیعی)، متن اعداد با `tabular-nums` و شکستن امن ارزهای طولانی؛ نمودار تمام‌عرض با ارتفاع مناسب و tooltip قابل لمس؛ جدول به کارت‌های سطری/scroll افقی محدودِ داخل container، نه overflow کل صفحه. Header همان رفتار کنونی/واکنش‌گرای خودش را حفظ کند.
- **Theme:** از tokenهای موجود استفاده شود: `--bg-card`, `--bg-elevated`, `--border-subtle`, `--text-primary/secondary/muted`, `--accent`, `--profit`, `--loss`, و soft variants. رنگ مثبت/منفی معنای ثابت و همراه علامت/متن داشته باشد؛ در dark mode هیچ background سفید/گرادیان hardcoded نباشد. Recharts grid, axes, tooltip و fill با CSS variables. audit قبلی hardcoded light gradient و PF display را خطر می‌داند.
- **تایپوگرافی/فاصله:** فونت موجود Vazirmatn و RTL حفظ؛ عنوان بخش حدود ۱۵–۱۶px، label حدود ۱۱–۱۲px، مقدار KPI برجسته اما محدود به اندازهٔ قابل‌خواندن؛ spacing منظم ۱۶–۲۰px و padding کارت ۱۶–۲۰px. از سایه/gradient/glow مکرر، آیکون‌های تزئینی و hover پرتحرک بکاهید؛ فضای خالی برای سلسله‌مراتب و خوانایی باشد نه کارت‌های کم‌ارزش. `Card` فعلی border/radius/token دارد و می‌تواند پایه بماند.

## ۹) Loading، خطا و نبود داده

- بارگذاری نخست: skeleton متناسب با پنج KPI، نمودار و جدول؛ `DashboardSkeleton` فعلی اکنون چهار KPI فرض می‌کند و در اجرا باید هماهنگ شود، نه اینکه در مرحلهٔ کشف تغییر کند.
- Refresh/تغییر فیلتر: context قبلی تا رسیدن پاسخ فقط با نشانگر refresh (یا skeleton موضعی) نمایش داده شود؛ فیلتر جدید روی اعداد قدیمی با برچسب جدید نشان داده نشود. برای پاسخ‌های موازی از request id/cancel و context key استفاده شود.
- خطای endpoint اصلی: پیام قابل فهم، retry و حفظ امکان دیدن دادهٔ قبلی فقط با نشان «قدیمی/آخرین دریافت»؛ خطای KPI/curve/table باید در سطح هم‌دامنه گزارش شود. خطای پنل ثانویه نباید کل داشبورد را از کار بیندازد (`ErrorBoundary`های فعلی حفظ).
- صفر معامله: حالت empty صریح با CTA موجود برای ثبت/ورود معامله؛ KPIها صفر/بدون داده را مطابق تعریف نمایش دهند، نه اینکه صفر مصنوعی را performance تفسیر کنند. PF در نبود نمونه `—`، در سود بدون زیان «بدون زیان مشاهده‌شده» (نه عدد 999 یا ∞ بی‌توضیح).
- نمودار با یک نقطه/بدون معامله: empty state؛ نقطهٔ شروع به‌تنهایی منحنی عملکرد تلقی نشود.
- پنل اختیاری: loading/error/empty مستقل و برچسب scope خود؛ error با empty اشتباه نشود.

## ۱۰) Prop/Risk: تناسب و ابهام

Prop stage/alerts بخشی از دامنهٔ واقعی برنامه‌اند و ممیزی، stage و personal account را در baseline curve ذکر می‌کند؛ بنابراین حذف خودکارشان درست نیست. اما کارت «وضعیت جاری/هدف/ریسک» با ژورنال تاریخی یکی نیست. فقط خلاصه‌ای نمایش داده شود که مالک داده، stage فعال، ارز، timestamp، منبع و تعریف قابل اتکا داشته باشد و به صفحهٔ Prop راه بدهد.

در مرحلهٔ discovery بازبینی کنید: progress ثابت/نمونه‌ای (در گزارش قدیمی به `ProgressBar value={65}` اشاره شده)، محاسبهٔ هدف/نسبت با denominator ساختگی، نیاز Prop engine به open/floating exposure، تفاوت challenge با funded، و اینکه داده‌های شامل floating یا current equity باید در Dashboard بسته‌محور نمایش داده نشوند. بخش risk historical تنها از closed outcomes مشتق شود؛ هر نیاز به ریسک جاری باید در صفحه/ویجت جدا و صریحاً خارج از KPIهای این طرح بماند.

## ۱۱) ریسک‌ها و پرسش‌های لازم پیش از اجرا

1. **Net API:** `summary.net_pnl` فعلی در query دیده‌شده از `scoped_q` (باز و بسته) می‌آید؛ درحالی‌که PF و win/loss بر closed شرط دارند. آیا اصلاح API/افزودن فیلد closed-only لازم است؟ پاسخ باید با تست قرارداد روشن شود.
2. **PF وضعیت‌دار:** helper وضعیت‌دار موجود (`profit_factor_status`) در response dashboard استفاده نمی‌شود؛ sentinel 999 با نسبت متناهی ≥999 مبهم است. طرح UI بدون تغییر قرارداد نمی‌تواند این دو را مطمئن تشخیص دهد.
3. **Max DD:** endpoint بزرگ‌ترِ peak-to-trough و static DD را می‌گیرد. انتخاب «peak-to-trough» یا «افت از baseline» باید تصمیم محصولی باشد؛ مقدار و درصد، baseline و دامنهٔ چندحسابی صریح شوند.
4. **Equity baseline:** initial balance از حساب‌ها/مراحل اشاره‌شده در معاملات بازه‌ای ساخته می‌شود و simulation/fallback ممکن است از 10,000 استفاده کند. در بازهٔ بدون معامله، سرمایهٔ شروع چگونه تعیین می‌شود؟ baseline واقعی/تاریخی و ارز در چند حساب چگونه تفکیک/تجمیع می‌شوند؟
5. **Scope/currency predicate:** رفتار `real` شامل چه classificationهایی است؛ BACKTEST/FORWARD چگونه با USDT فیلتر می‌شوند؛ `all` در چند ارز چه می‌کند؟ currency conversion خودکار فرض نشود.
6. **تاریخ:** تفاوت timezone محلی مرورگر و تهران، parsing مرز تاریخ شمسی و inclusive/exclusive انتهای روز؛ UI، API و PDF باید یک قرارداد داشته باشند.
7. **Recent trades:** endpoint و predicate فعلی، تعداد، tie-break، net، screenshot/strategy metadata و تطبیق آن با KPIها پیش از reuse بررسی شود.
8. **Finance/Prop/Payout:** Net Closed PnL فقط PnL معاملات است. payout درآمد نقدی/برداشت و finance net profit دارایی/ledger هستند؛ نباید به Net Closed PnL اضافه شوند. کارمزد معامله در net معامله یک‌بار لحاظ می‌شود؛ finance expense مرتبط با همان کارمزد نباید بار دیگر کسر شود مگر قرارداد accounting صریح باشد.
9. **فیلترها و PDF:** فیلترهای مستقل Backtest/Finance/Today و export فعلی الزاماً snapshot یکسان نیستند. context خروجی و UI باید با هم parity داشته باشند.
10. **Header و Theme:** مالکیت header (ممکن است بخشی از layout بیرونی باشد)، plugin/theme/settings و breakpointهای فعلی را پیش از پیاده‌سازی از دست ندهید.
11. **کارایی و خطا:** endpoint dashboard شاخه‌های متعدد محاسبات دارد؛ صفحهٔ کوتاه‌شده هنوز ممکن است تمام queryها را اجرا کند. بعد از تثبیت صحت، profiler/SQL count و خطای جزئی بررسی شود، نه بازنویسی پیش‌دستانه.
12. **پذیرش محصول:** آیا کارت‌های مستقل Finance، اخبار، Prop، Today/Yesterday و Backtest باید پایین Dashboard بمانند یا به صفحهٔ مالک لینک شوند؟ تا پاسخ، حذف نشوند.

## ۱۲) برنامهٔ اجرای مرحله‌ای، کوچک و قابل تست

1. **قرارداد و inventory بدون تغییر UI:** پاسخ fixtureهای dashboard، predicate scope/date/currency، source هر panel، PDF و recent trades را مستند کنید. با دادهٔ بسته/باز، scopeها، currencies، timezone و edge caseها parity را تست کنید.
2. **تصمیم KPI و API:** Net Closed را از query بسته تفکیک/تضمین کنید؛ PF status/value و max DD definition/baseline را قرارداددهی کنید. تست unit/API برای breakeven، بدون loss، بدون داده، loss ریز، بازها و چندحساب اضافه کنید. هیچ payout/finance aggregate وارد این محاسبات نشود.
3. **یکپارچه‌سازی context فیلتر:** request context یکتا (تاریخ، scope، ارز و selector مجاز) برای KPI/curve/table بسازید؛ guarding پاسخ قدیمی، timezone و PDF parity را تست کنید.
4. **وایرفریم/ساختار layout:** Header بدون تغییر؛ ابتدا فقط جابه‌جایی و گروه‌بندی عناصر موجود با CSS responsive/tokenها. snapshot/RTL و dark/light در breakpointهای کوچک و بزرگ بررسی شود.
5. **KPIها:** پنج کارت را به پاسخ قراردادی وصل کنید؛ skeleton/empty/error و دسترسی‌پذیری/format عدد را تست کنید. sparkline پیش‌فرض یا metric ساختگی ممنوع.
6. **Equity Curve:** دادهٔ آمادهٔ backend و baseline/status را استفاده کنید؛ محور/tooltip/empty و closed-only را تست کنید؛ fallback pnl-only حذف/غیرفعال شود فقط پس از مشخص شدن مسیر سازگار و با تست عدم دوباره‌شماری commission/swap.
7. **Recent closed table:** endpoint/fetch هم‌فیلتر، sort پایدار و لینک «همه»؛ تست برابری count/net با KPI و عدم نمایش open.
8. **بخش‌های ثانویه:** یک‌به‌یک Prop، Backtest، Finance، Today/Yesterday، alerts و widgetها را به جایگاه مستقل منتقل/گروه‌بندی کنید؛ هر پنل آزمون context/error خود داشته باشد. فقط قابلیت‌های تأییدشدهٔ بی‌منبع/تکراری پس از تصمیم محصول حذف شوند.
9. **Regression و نهایی‌سازی:** theme، responsive، date boundaries، out-of-order response، PDF، Refresh، accessibility و کل suiteهای موجود اجرا شوند؛ عدم تغییر قرارداد finance/payout و عدم نمایش open/floating در Dashboard شرط پذیرش است.

### معیار پایان طراحی/پذیرش اجرا

- هدر بدون تغییر بصری/عملکردی باقی بماند.
- Net PnL، win/loss، PF، DD، count، curve و جدول بر یک مجموعهٔ closed و context واحد تکیه کنند.
- هیچ open trade، floating PnL یا قیمت زنده در performance Dashboard حضور نداشته باشد.
- هر شاخص تعریف، ارز، baseline/وضعیت لازم و source قابل ردیابی داشته باشد.
- Finance/payout دوباره‌شماری نشوند؛ فیلترهای مستقل برچسب‌گذاری شوند.
- حالت‌های loading، error، empty و dark/light و layout صفحهٔ کوچک قابل آزمون باشند.
- قابلیت‌های مفید کنونی یا حفظ شوند یا تصمیم انتقال/حذف با دلیل ثبت شود.

## ۱۳) منابع بررسی‌شده

- `DASHBOARD_FULL_AUDIT_2026-10-09.md` (شامل نقشهٔ ارتباط، یافته‌های ۴۲گانه، قرارداد پیشنهادی و اولویت اصلاح).
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/api/client.ts` (`getDashboardData`, `exportDashboardPdf`)
- `backend/app/api/analytics.py` (`get_dashboard_data` و aggregation closed/equity)
- `backend/app/domain/risk/drawdown_engine.py`
- `backend/app/services/metrics.py` (PF numeric/status helpers)
- `frontend/src/components/charts/EquityCurveChart.tsx`
- `frontend/src/components/ui/Card.tsx`, `StatCard.tsx`, `Skeleton.tsx`
- `frontend/src/components/MarketSessionWidget.tsx`

**محدودیت بررسی:** این سند براساس کد و ممیزی موجود تهیه شده است؛ اجرای برنامه، مرورگر یا دادهٔ عملیاتی برای این فاز انجام نشده است. قبل از پیاده‌سازی، موارد ابهام بالا و وضعیت جاری working tree باید جداگانه بازبینی شوند.