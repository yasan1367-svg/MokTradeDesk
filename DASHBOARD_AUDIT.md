# Dashboard Audit — Task 1/13

## Structure & Files

### Files Found

مبنای بررسی: فایل‌های local در frontend؛ ستون Imports یعنی فایل‌های مصرف‌کننده (reverse imports)، نه وابستگی‌های خروجی. برای خوانایی، شناسه‌های جدول در Component Tree نیز استفاده می‌شوند و هر شناسه به مسیر absolute همین جدول اشاره دارد. نام‌های کوتاه مصرف‌کنندگان به فایل هم‌نام زیر `i:\trade\MokTradeDesk\frontend\src\pages` اشاره دارند؛ مسیرهای دیگر صریحاً مشخص شده‌اند. موارد test شامل import و mock reference هستند.

| File | Responsibility | Imports |
|---|---|---|
| D — `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx` | صفحه اصلی؛ مدیریت filter، دریافت داده، بخش‌های آماری/مالی/پراپ/معاملات و MiniPie/MiniBars داخلی | `i:\trade\MokTradeDesk\frontend\src\App.tsx` با lazy import و preload؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\dashboardPage.test.tsx` |
| SC — `i:\trade\MokTradeDesk\frontend\src\components\ui\StatCard.tsx` | کارت KPI با spark bars یا chart دریافتی | DashboardPage.tsx |
| C — `i:\trade\MokTradeDesk\frontend\src\components\ui\Card.tsx` | container مشترک Card و عنوان/اکشن CardHeader | DashboardPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\components.test.tsx` |
| B — `i:\trade\MokTradeDesk\frontend\src\components\ui\Badge.tsx` | نشان وضعیت با variant رنگی | DashboardPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\components.test.tsx` |
| P — `i:\trade\MokTradeDesk\frontend\src\components\ui\ProgressBar.tsx` | نمایش پیشرفت اهداف و مرحله پراپ | DashboardPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\components.test.tsx` |
| EQ — `i:\trade\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx` | منحنی Equity با AreaChart؛ دریافت series یا trades | DashboardPage.tsx، AnalysisPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\dashboardPage.test.tsx` |
| WL — `i:\trade\MokTradeDesk\frontend\src\components\charts\WinLossPieChart.tsx` | نمودار Pie برد/باخت | DashboardPage.tsx، AnalysisPage.tsx |
| PD — `i:\trade\MokTradeDesk\frontend\src\components\charts\PnLDistributionChart.tsx` | Histogram سطل‌های PnL؛ حالت سازگار Pie بر اساس symbol | DashboardPage.tsx، AnalysisPage.tsx |
| SK — `i:\trade\MokTradeDesk\frontend\src\components\Skeleton.tsx` | Skeleton پایه و DashboardSkeleton برای loading | DashboardPage.tsx، CalendarPage.tsx، ComparisonPage.tsx، FinancePage.tsx، PayoutHistoryPage.tsx، RiskManagementPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\components\BackupManager.tsx` |
| T — `i:\trade\MokTradeDesk\frontend\src\components\ToastProvider.tsx` | ToastContext، Provider و Hook مشترک useToast | DashboardPage.tsx، ComparisonPage.tsx، FinancePage.tsx، PayoutHistoryPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\App.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\main.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\components\BackupManager.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\dashboardPage.test.tsx` |
| DT — `i:\trade\MokTradeDesk\frontend\src\components\PersianDateInput.tsx` | ورودی تاریخ شمسی و تبدیل به ISO؛ conversion داخلی دارد | DashboardPage.tsx، FinancePage.tsx، PayoutHistoryPage.tsx، PropPage.tsx، StrategyPage.tsx، TradesPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\components\TransactionForm.tsx` |
| ES — `i:\trade\MokTradeDesk\frontend\src\components\ui\EmptyState.tsx` | حالت بدون داده با action اختیاری | DashboardPage.tsx، ComparisonPage.tsx، FinancePage.tsx، PayoutHistoryPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\components\BackupManager.tsx` |
| IT — `i:\trade\MokTradeDesk\frontend\src\components\ui\Tooltip.tsx` | Tooltip سبک برای actionها؛ در Dashboard با alias برابر InfoTooltip | DashboardPage.tsx، FinancePage.tsx |
| EB — `i:\trade\MokTradeDesk\frontend\src\components\ErrorBoundary.tsx` | گرفتن render error و نمایش fallback/reload/copy | DashboardPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\App.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\main.tsx` |
| FA — `i:\trade\MokTradeDesk\frontend\src\components\FinancialAssetBalances.tsx` | جدول دارایی شخصی به تفکیک محل نگهداری و USDT/IRR | DashboardPage.tsx، FinancePage.tsx |
| MS — `i:\trade\MokTradeDesk\frontend\src\components\MarketSessionWidget.tsx` | ساعت و وضعیت Sessionها به وقت Tehran، بازه‌های پورصمدی، خبر و هشدار؛ شامل NewsCollapsed/NewsExpanded | DashboardPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\dashboardPage.test.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\marketSessionWidget.test.tsx` |
| J — `i:\trade\MokTradeDesk\frontend\src\utils\jalali.ts` | تبدیل Gregorian/Jalali و helperهای تاریخ | DashboardPage.tsx، FinancePage.tsx، PayoutHistoryPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\components\BackupManager.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\utils.test.ts` |
| API — `i:\trade\MokTradeDesk\frontend\src\api\client.ts` | Axios instance، endpoint wrapperها و typeهای مشترک | AnalysisPage.tsx، CalendarPage.tsx، ComparisonPage.tsx، DashboardPage.tsx، FinancePage.tsx، ImportPage.tsx، JournalPage.tsx، PayoutHistoryPage.tsx، PropPage.tsx، RiskManagementPage.tsx، SettingsPage.tsx، StrategyPage.tsx، TradesPage.tsx؛ `i:\trade\MokTradeDesk\frontend\src\App.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\main.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\components\BackupManager.tsx`؛ FA (type-only)، MS؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\client.analysis.test.ts`؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\dashboardPage.test.tsx`؛ `i:\trade\MokTradeDesk\frontend\src\__tests__\marketSessionWidget.test.tsx` |

### Component Tree

شناسه داخل پرانتز، مسیر absolute جدول بالاست. R یعنی component کتابخانه `recharts`، نه فایل اختصاصی پروژه. درخت در سطح React Component کامل است؛ DOM/SVG ساده و تکرارهای یکسان خلاصه شده‌اند. شاخه‌های conditional الزاماً هم‌زمان render نمی‌شوند.

```text
DashboardPage (D)
├── loading: DashboardSkeleton (SK)
│   └── Skeleton (SK) × تکرارهای متن/کارت
├── ErrorBoundary: Dashboard header and filters (EB)
│   ├── MarketSessionWidget (MS)
│   │   ├── NewsCollapsed (MS؛ حالت بسته)
│   │   └── NewsExpanded (MS؛ حالت باز)
│   ├── InfoTooltip (IT) × 5 → دکمه‌های quick action / refresh
│   └── PersianDateInput (DT) × 2؛ بازه custom
├── ErrorBoundary: کارت‌های آماری (EB)
│   ├── Card (C) → EmptyState (ES)؛ بدون داده
│   └── StatCard (SC) × 4
│       ├── spark bars داخلی DOM
│       ├── chart prop: MiniPie (D)
│       │   └── ResponsiveContainer (R)
│       │       └── PieChart (R)
│       │           ├── Pie (R) → Cell (R) × داده‌ها
│       │           └── Tooltip (R)
│       └── chart prop: MiniBars (D) × 2
│           └── ResponsiveContainer (R)
│               └── BarChart (R)
│                   ├── XAxis (R)
│                   ├── Tooltip (R)
│                   └── Bar (R) → Cell (R) × داده‌ها
├── ErrorBoundary: Today (EB) → محتوای inline وضعیت امروز/ماه/فصل/سال
├── ErrorBoundary: Yesterday (EB)
│   └── Card (C)
│       ├── CardHeader (C)
│       └── MiniBars (D) → همان زیرشاخه کامل MiniBars بالا
├── ErrorBoundary: Active Prop Stage (EB)
│   └── Card (C)
│       ├── CardHeader (C)
│       ├── Badge (B)؛ مرحله و آماده پاس شدن
│       └── ProgressBar (P)؛ پیشرفت سود مرحله
├── Card: هشدارهای پراپ (C)
│   └── CardHeader (C)؛ لیست و دکمه خوانده‌شدن inline
├── ErrorBoundary: Finance (EB)
│   └── Card (C)
│       ├── CardHeader (C)
│       ├── Card: موجودی کل (C) → CardHeader (C)
│       ├── Card: جریان نقدی (C)
│       │   ├── CardHeader (C)
│       │   └── ResponsiveContainer (R)
│       │       └── BarChart (R) → XAxis، Tooltip، Bar درآمد، Bar هزینه (R)
│       ├── Card: تفکیک حساب‌ها (C) → CardHeader (C)
│       ├── Card: سود خالص (C) → CardHeader (C)
│       ├── Card: دارایی شخصی (C)
│       │   ├── CardHeader (C)
│       │   └── FinancialAssetBalances (FA)
│       └── Card: روند دارایی (C)
│           ├── CardHeader (C)
│           └── ResponsiveContainer (R)
│               └── AreaChart (R)
│                   └── CartesianGrid، XAxis، YAxis، Tooltip، Area USDT، Area IRR (R)
├── ErrorBoundary: Prop goals (EB)
│   └── Card (C) → CardHeader (C)، ProgressBar (P) × 3
├── ErrorBoundary: عملکرد بک‌تست (EB)
│   └── Card (C)
│       ├── CardHeader (C)؛ selector نسخه در action
│       ├── StatCard (SC) × 3؛ spark bars داخلی
│       └── EmptyState (ES)؛ نبود نسخه یا داده
├── ErrorBoundary: نمودارها (EB)
│   ├── Card (C)
│   │   ├── CardHeader (C)
│   │   └── EquityCurveChart (EQ)
│   │       └── ResponsiveContainer (R)
│   │           └── AreaChart (R)
│   │               └── CartesianGrid، XAxis، YAxis، Tooltip، Area × 2 (R)
│   ├── Card (C)
│   │   ├── CardHeader (C)
│   │   └── WinLossPieChart (WL)
│   │       └── ResponsiveContainer (R)
│   │           └── PieChart (R)
│   │               ├── Pie (R) → Cell (R) × 2
│   │               └── Tooltip، Legend (R)
│   └── Card (C)
│       ├── CardHeader (C)
│       └── PnLDistributionChart (PD)
│           ├── حالت buckets: ResponsiveContainer (R)
│           │   └── BarChart (R)
│           │       ├── CartesianGrid، XAxis، YAxis، Tooltip (R)
│           │       └── Bar (R) → Cell (R) × buckets
│           └── حالت سازگاری trades: ResponsiveContainer (R)
│               └── PieChart (R)
│                   ├── Pie (R) → Cell (R) × symbols
│                   └── Tooltip، Legend (R)
└── ErrorBoundary: معاملات (EB)
    ├── Card: آخرین معاملات (C) → CardHeader (C)، EmptyState (ES) یا جدول DOM
    └── Card: معاملات باز (C) → CardHeader (C)، EmptyState (ES) یا جدول DOM
```

Chartها در نبود داده fallback متنی DOM دارند. ErrorBoundary نیز fallback داخلی DOM دارد. ToastProvider (T) ancestor سراسری است، نه child صفحه؛ `useToast` به Context آن متصل می‌شود. سایر leaf componentها child اختصاصی دیگری ندارند.

### API Calls

Base URL در API از `VITE_API_BASE_URL` گرفته می‌شود؛ fallback برابر `http://localhost:8000` است. جدول URLهای نسبی را نشان می‌دهد. Wrapperهای نام‌برده در فایل API جدول بالا قرار دارند؛ دو ردیف آخر مستقیم از MS هستند.

| Method / Endpoint URL | Client function | بخش Dashboard / پارامترهای واقعی |
|---|---|---|
| GET `/api/analytics/dashboard` | `getDashboardData` | داده اصلی: summary، today، periods، وضعیت پراپ/اهداف و نمودارها؛ `date_from`, `date_to`, `scope`, `currency`؛ فراخوان مستقل بک‌تست با `scope=backtest`, `currency=USDT`, `version_id` |
| GET `/api/analytics/yesterday` | `getYesterdayData` | کارت دیروز؛ `scope`, `currency` |
| GET `/api/finance/real-summary` | `getRealSummary` | کارت‌های آماری عملکرد Real؛ `currency` |
| GET `/api/strategies/versions/all` | `getAllVersions` | انتخاب نسخه برای بخش عملکرد بک‌تست |
| GET `/api/export/dashboard/pdf` | `exportDashboardPdf` | action خروجی PDF؛ responseType برابر blob؛ بدون ارسال filterهای صفحه |
| GET `/api/prop/alerts` | `getPropAlerts` | هشدارهای پراپ؛ `unread_only=true` |
| PATCH `/api/prop/alerts/{alertId}/read` | `markAlertRead` | دکمه خوانده‌شدن هشدار و حذف از لیست local |
| GET `/api/finance/summary` | `getFinanceSummary` | موجودی کل بخش مالی؛ بدون پارامتر |
| GET `/api/finance/charts/cashflow` | `getFinanceCashflow` | BarChart جریان نقدی؛ `currency`؛ نمایش شش مورد آخر |
| GET `/api/finance/accounts` | `getFinanceAccounts` | تفکیک حساب‌های مالی؛ بدون پارامتر |
| GET `/api/trades/` | `getTrades` | آخرین معاملات: `status=closed`, `limit=10`, `sort_by=close_time`, `sort_order=desc`, `currency`؛ معاملات باز: `status=open`, `sort_by=open_time`, `sort_order=desc`, `currency` |
| GET `/api/finance/spendable-assets` | `getSpendableAssets` | FinancialAssetBalances / دارایی شخصی؛ بدون پارامتر |
| GET `/api/finance/net-profit` | `getNetProfit` | سود Real، هزینه و سود خالص؛ `currency` |
| GET `/api/finance/asset-trend` | `getAssetTrend` | AreaChart روند دارایی USDT/IRR؛ بدون پارامتر |
| GET `/api/analytics/intervals/` | Wrapper اختصاصی استفاده نمی‌شود؛ `api.get` در MS | بازه‌های پورصمدی در MarketSessionWidget |
| GET `/api/news/upcoming?scope=today&limit=20` | Wrapper اختصاصی استفاده نمی‌شود؛ `api.get` در MS | NewsCollapsed، NewsExpanded و هشدار خبر در MarketSessionWidget |

### Notes

- دامنه Task 1 ساختار frontend و call siteهاست؛ صحت محاسبات backend یا رفتار runtime در این مرحله ارزیابی نشده است.
- صفحه اصلی ۱۱۳۳ خط دارد؛ MiniPie و MiniBars و Chartهای مالی inline هستند و فایل جدا ندارند.
- ۱۶ endpoint یکتا یافت شد: ۱۴ endpoint در صفحه و ۲ endpoint در widget. تعداد requestها بیشتر است؛ `getTrades` دو بار و `getDashboardData` برای دو context استفاده می‌شوند.
- `loadDashboard` دوازده request را با Promise.all اجرا می‌کند؛ نسخه‌ها، بک‌تست، PDF، تغییر وضعیت alert و requestهای widget مسیر جدا دارند.
- Dashboard از React `useState`, `useEffect`, `useCallback` و custom Hook برابر `useToast` استفاده می‌کند. MS از `useState`, `useEffect`, `useRef` استفاده می‌کند. Store اختصاصی یا اتصال Zustand در این dependency tree یافت نشد؛ state صفحه local و بخشی از filterها در localStorage است.
- InfoTooltip با Recharts Tooltip متفاوت است. FinancialAssetBalances فقط type را از API import می‌کند و خودش request ندارد.
- PersianDateInput conversion داخلی دارد و مصرف‌کننده فایل J نیست؛ تبدیل تاریخ صفحه مستقیماً از J استفاده می‌کند.
- Component Tree شاخه‌های conditional و chart propها را شامل می‌شود، نه internals کتابخانه Recharts یا DOM کامل.
- فقط `i:\trade\MokTradeDesk\DASHBOARD_AUDIT.md` برای این Task ایجاد/بازنویسی می‌شود؛ هیچ کد اجرایی تغییر نکرد. Git و GitHub استفاده نشدند.
- اعتبارسنجی با خواندن source، جست‌وجوی reverse imports و تطبیق call siteها با Client انجام شد؛ build/test اجرا نشد چون این Task صرفاً مستندسازی است.

## Task 2/13 — Dashboard Sections (Top to Bottom)

### مبنا و قرارداد خواندن گزارش

ترتیب زیر ترتیب JSX در `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx` است، نه ترتیب فهرست endpointها. در gridها ترتیب فرزندان کد ملاک است؛ چیدمان چندستونه روی موبایل به تک‌ستونه تبدیل می‌شود. ۱۳ بخش اصلی وجود دارد؛ ردیف ۱۴ حالت‌های جایگزین و موارد خارج از بدنه را روشن می‌کند، نه یک کارت اضافی در انتهای صفحه. بخش مالی شش زیرکارت دارد.

برای جلوگیری از تکرار مسیرهای طولانی، ارجاعات این Task به این مسیرهای absolute اشاره دارند:

- **D:** `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx`؛ تابع `DashboardPage` و بارگذار `loadDashboard`.
- **API:** `i:\trade\MokTradeDesk\frontend\src\api\client.ts`؛ wrapperهای درخواست جدول Task 1.
- **Backend:** `i:\trade\MokTradeDesk\backend\app\api\analytics.py`؛ تابع `get_dashboard_data` برای بررسی تفاوت پارامتر درخواست با اثر واقعی بر پاسخ.
- **Finance:** `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx`.
- **Prop:** `i:\trade\MokTradeDesk\frontend\src\pages\PropPage.tsx`.
- **Analysis:** `i:\trade\MokTradeDesk\frontend\src\pages\AnalysisPage.tsx`.
- **Trades:** `i:\trade\MokTradeDesk\frontend\src\pages\TradesPage.tsx`.
- **App:** `i:\trade\MokTradeDesk\frontend\src\App.tsx`.

**نکته مشترک فیلترها:** Date یعنی بازه انتخابی، نه ساعت هدر یا دوره ثابت دیروز. Scope یعنی real/backtest/forward/all. Currency یعنی USDT/IRR؛ انتخاب ارز لزوماً تبدیل ارز نیست. **Account selector در Dashboard وجود ندارد و هیچ‌کدام از درخواست‌های این صفحه شناسه حساب انتخابی ارسال نمی‌کنند.** تغییر Date/Scope/Currency کل `loadDashboard` را دوباره اجرا می‌کند؛ درخواست مجدد را نباید با فیلترشدن داده یکسان دانست. ستون Needed و توضیح Necessity ارزیابی پیشنهادی ممیزی هستند، نه نیازمندی تأییدشده محصول. «تکرار» نیز بین تکرار دقیق داده، اشتراک مفهوم و اشتراک صرفاً کامپوننت تفکیک شده است.

### فهرست به ترتیب نمایش

| # | Section Name | Component | API Endpoint | Filter-Dependent? | Duplicated Elsewhere? | Needed? |
|---|---|---|---|---|---|---|
| 1 | Header — خوشامد / تاریخ / ساعت / سشن / میانبر / Refresh / PDF | JSX در D، MarketSessionWidget، InfoTooltip؛ Theme در App | GET `/api/analytics/intervals/`؛ GET `/api/news/upcoming?scope=today&limit=20`؛ GET `/api/export/dashboard/pdf`؛ Refresh درخواست‌های loadDashboard | ساعت/سشن/PDF خیر؛ Refresh پارامترهای هر بخش را حفظ می‌کند؛ Account ندارد | میانبرها در صفحات مقصد؛ Theme سراسری | مفید ولی غیرضروری |
| 2 | Filter bar — Date Range / Scope / Currency | JSX در D، PersianDateInput | مستقیم ندارد؛ بارگذاری مجدد endpointهای بخش‌ها | کنترل Date/Scope/Currency؛ بدون Account | فیلترهای مشابه در Analysis و Trades، با state مستقل | ضروری |
| 3 | Real Money — چهار KPI | StatCard ×4، MiniPie، MiniBars؛ یا EmptyState | GET `/api/finance/real-summary` | فقط Currency؛ Date/Scope/Account خیر | هم‌پوشانی PnL با Finance؛ KPIهای مشابه در Analysis | ضروری |
| 4 | Today + آمار ماه/فصل/سال | JSX در D | GET `/api/analytics/dashboard` | Date/Scope/Currency؛ استثنای شمارنده باز: فقط Scope؛ Account خیر | دوره‌ها عیناً در بخش 9؛ داده معاملات در Trades | ضروری |
| 5 | Yesterday Card | Card، CardHeader، MiniBars | GET `/api/analytics/yesterday` | Scope/Currency؛ Date/Account خیر | هم‌پوشانی با معاملات روز قبل در Trades؛ نه کارت یکسان تأییدشده | مفید ولی غیرضروری |
| 6 | Active Prop Stage — وضعیت پراپ | Card، Badge، ProgressBar، EmptyState | GET `/api/analytics/dashboard` → prop_progress | عملاً Currency؛ Date/Scope/Account خیر | وضعیت و قوانین مرحله در Prop | ضروری |
| 7 | Prop Alerts — فقط در صورت وجود هشدار | Card و JSX در D | GET `/api/prop/alerts`؛ PATCH `/api/prop/alerts/{alertId}/read` | هیچ‌کدام؛ unread_only=true ثابت | هشدارها در Prop؛ شمارنده در App | ضروری |
| 8 | Finance — وضعیت حال، سپس عملکرد | Card والد و شش Card داخلی | شش endpoint ردیف‌های 8.1 تا 8.6 | ترکیبی؛ Date/Scope/Account خیر | هم‌پوشانی گسترده با Finance | مفید ولی غیرضروری |
| 8.1 | وضعیت حال / موجودی کل | Card و JSX | GET `/api/finance/summary` | Currency فقط انتخاب مقدار پاسخ در UI | Finance؛ هم‌پوشانی با دارایی شخصی، نه برابری قطعی مجموع‌ها | مفید ولی غیرضروری |
| 8.2 | وضعیت حال / جریان نقدی | Card، Recharts BarChart | GET `/api/finance/charts/cashflow` | فقط Currency | همان منبع در نمودار Finance | متعلق به صفحه دیگر |
| 8.3 | وضعیت حال / تفکیک حساب‌ها | Card و فهرست JSX | GET `/api/finance/accounts` | هیچ‌کدام؛ ارز هر حساب مستقل | فهرست حساب‌های Finance | متعلق به صفحه دیگر |
| 8.4 | عملکرد / سود خالص | Card و سه مقدار JSX | GET `/api/finance/net-profit` | فقط Currency | همان منبع در Finance؛ متفاوت از net_pnl کارت Real | مفید ولی غیرضروری |
| 8.5 | عملکرد / دارایی شخصی | Card، FinancialAssetBalances | GET `/api/finance/spendable-assets` | هیچ‌کدام؛ هر دو ارز هم‌زمان | همان کامپوننت و endpoint در Finance | تکراری |
| 8.6 | عملکرد / روند دارایی | Card، Recharts AreaChart | GET `/api/finance/asset-trend` | هیچ‌کدام؛ هر دو سری USDT/IRR | تکرار دقیق این نمودار در صفحات بررسی‌شده تأیید نشد | متعلق به صفحه دیگر |
| 9 | Prop Goals / پیشرفت اهداف — در واقع عملکرد دوره‌ای | Card، ProgressBar ×3 | GET `/api/analytics/dashboard` → periods | Date/Scope/Currency؛ Account خیر | PnL ماه/فصل/سال دقیقاً تکرار بخش 4 | تکراری |
| 10 | Backtest Performance — نسخه منتخب | Card، select، StatCard ×3، EmptyState | GET `/api/strategies/versions/all`؛ GET `/api/analytics/dashboard` | فیلترهای سراسری خیر؛ version_id مستقل، scope=backtest و currency=USDT ثابت | خلاصه تحلیل نسخه در Analysis | متعلق به صفحه دیگر |
| 11 | Charts row — Equity / WinLoss / PnL Distribution | Card ×3، EquityCurveChart، WinLossPieChart، PnLDistributionChart | GET `/api/analytics/dashboard` | Date/Scope/Currency؛ Account خیر | سه کامپوننت در Analysis؛ ورودی/معنای توزیع الزاماً یکسان نیست | مفید ولی غیرضروری |
| 12 | Recent Trades — آخرین معاملات بسته | Card، جدول JSX، EmptyState | GET `/api/trades/` | فقط Currency؛ Date/Scope/Account خیر | ردیف‌های معاملات در Trades | مفید ولی غیرضروری |
| 13 | Open Trades — معاملات باز | Card، جدول JSX، EmptyState | GET `/api/trades/` | فقط Currency؛ Date/Scope/Account خیر | ردیف‌های معاملات در Trades | ضروری |
| 14 | سایر حالت‌ها؛ نه بخش محتوایی اضافی | DashboardSkeleton، ErrorBoundary، EmptyState، Toast | endpoint مستقل ندارد | تابع وضعیت بارگذاری/خطای بخش‌ها | اجزای عمومی مشترک؛ داده تکراری محسوب نمی‌شوند | ضروری |

### توضیح هر بخش

#### 1. Header

- **What it shows:** سلام متناسب با ساعت، تاریخ شمسی، ساعت زنده و MarketSessionWidget با سشن‌ها/بازه‌ها/خبرهای امروز. میانبر معامله جدید، تراکنش مالی، حساب جدید، جست‌وجو، Refresh و PDF نیز همین‌جا هستند؛ دکمه Theme برخلاف برداشت فهرست اولیه، فرزند DashboardPage نیست و در App قرار دارد.
- **Where it comes from:** D، خطوط 303–378؛ `getGreeting`، تبدیل تاریخ، timer یک‌ثانیه‌ای، `handleNewTrade`، `openSearch`، `loadDashboard(true)` و `handleExportPdf`. دو endpoint سشن/خبر و endpoint PDF مطابق جدول بالا؛ widget از `i:\trade\MokTradeDesk\frontend\src\components\MarketSessionWidget.tsx` می‌آید. Theme از `useTheme` در App است.
- **Filter behavior:** Date/Scope/Currency/Account بر ساعت و widget اعمال نمی‌شوند. PDF بدون پارامتر فیلتر صادر می‌شود، پس انطباق آن با نمای فیلترشده تضمین نشده است. Refresh فقط batch اصلی را اجرا می‌کند؛ فهرست نسخه‌ها، خلاصه مستقل بک‌تست و درخواست‌های widget داخل آن نیستند.
- **Duplicate check:** عملیات معامله و مالی مسیرهای میانبر به Trades و Finance هستند؛ دو دکمه مالی فقط به Finance می‌روند، نه اینکه در این کد فرم مشخصی باز کنند. Theme کنترل سراسری App است، نه تکرار داخل هدر D. تکرار دقیق widget در صفحه دیگری در ممیزی حاضر تأیید نشده است.
- **Necessity:** **مفید ولی غیرضروری**؛ سشن و Refresh کاربرد عملی دارند، اما خوشامد و تعدد میانبرها قابل کاهش‌اند. PDF باید نسبت خود با فیلترها را روشن کند.

#### 2. Filter bar

- **What it shows:** دکمه‌های بازه آماده، انتخاب دامنه معاملات و انتخاب ارز. در حالت custom دو ورودی شمسی «از تاریخ / تا تاریخ» ظاهر می‌شوند؛ کنترل Account وجود ندارد.
- **Where it comes from:** D، خطوط 164–177، 271–278 و 380–436؛ stateهای `rangeKey/customFrom/customTo/scope/currency`، `computeRange` و `loadDashboard`. ورودی از `i:\trade\MokTradeDesk\frontend\src\components\PersianDateInput.tsx` است؛ API مستقیم ندارد.
- **Filter behavior:** این بخش تولیدکننده Date/Scope/Currency است و مقادیر را در localStorage نگه می‌دارد. اثر آن بر تمام کارت‌ها یکسان نیست؛ Account در UI و requestها غایب است.
- **Duplicate check:** Analysis و Trades نیز ابزار انتخاب context/فیلتر دارند، ولی آن‌ها state این نوار را به اشتراک نمی‌گذارند؛ تشابه ابزار، تکرار داده نیست.
- **Necessity:** **ضروری**؛ برای تفسیر نمودارها لازم است، اما باید محدوده اثر هر فیلتر مشخص باشد تا کاربر همه کارت‌ها را هم‌دامنه تصور نکند.

#### 3. Real Money Section — چهار StatCard

- **What it shows:** سود خالص، نرخ برد، فاکتور سود و حداکثر ضرر معاملات پول واقعی (مرحله فاندد پراپ + بروکر شخصی)، همراه sparkline، Pie برد/باخت و MiniBars. اگر خلاصه موجود نباشد یا معامله‌ای نداشته باشد، کل ردیف با EmptyState و لینک پراپ جایگزین می‌شود.
- **Where it comes from:** D، خطوط 440–516؛ `loadDashboard → getRealSummary({ currency })` در API → GET `/api/finance/real-summary`. `StatCard` از `i:\trade\MokTradeDesk\frontend\src\components\ui\StatCard.tsx` است؛ MiniPie/MiniBars داخل D هستند.
- **Filter behavior:** Currency به endpoint فرستاده می‌شود؛ Date و Scope ارسال نمی‌شوند. حتی با Scope=backtest، این ردیف همچنان Real است. Account قابل انتخاب نیست.
- **Duplicate check:** PnL واقعی در تب Real PnL صفحه Finance نیز دیده می‌شود؛ KPIهای مشابه در Analysis وجود دارند، اما دامنه آن‌ها لزوماً همین تجمیع نیست. سود خالص مالی در 8.4 بعد از هزینه‌هاست و نباید با این net_pnl یکسان فرض شود.
- **Necessity:** **ضروری**؛ خلاصه عملکرد پول واقعی برای داشبورد مناسب است، به شرط حفظ برچسب مستقل‌بودن از Date/Scope.

#### 4. Today Section و آمار دوره‌ای

- **What it shows:** PnL امروز، تعداد و نرخ برد امروز، شمار معاملات باز و کل معاملات. سه کاشی کنار آن PnL ماه جاری، فصل جاری و سال جاری را نشان می‌دهند.
- **Where it comes from:** D، خطوط 518–578؛ `loadDashboard → getDashboardData` → GET `/api/analytics/dashboard`، فیلدهای `today`، `summary` و `periods`. Backend، خطوط 332–335 و 441–464، محاسبات today/periods را روی `closed_scope` انجام می‌دهد.
- **Filter behavior:** Date/Scope/Currency روی today، periods و total_trades اثر دارند؛ دوره‌های جاری با بازه انتخابی تقاطع پیدا می‌کنند و الزاماً کل ماه/فصل/سال نیستند. استثنا: `summary.open_trades` در Backend خط 410 فقط Scope می‌گیرد و Date/Currency را اعمال نمی‌کند. Account وجود ندارد.
- **Duplicate check:** سه مقدار دوره‌ای عیناً دوباره در بخش 9 مصرف می‌شوند؛ شمار باز نیز با جدول بخش 13 هم‌موضوع است ولی فیلترهای یکسان ندارد. Trades امکان مشاهده ردیف‌های مبنای معاملات را می‌دهد، نه همین کارت مرکب.
- **Necessity:** **ضروری** برای مرور روز؛ تکرار دوره‌ها در بخش 9 قابل حذف/ادغام است. نام «امروز» نباید این تصور را بسازد که از Date مستقل است.

#### 5. Yesterday Card

- **What it shows:** روز و تاریخ گذشته، تعداد معامله، PnL، نرخ برد، برد/باخت و تعداد به تفکیک پراپ/شخصی/شبیه‌سازی. MiniBars قدرمطلق PnL هر منبع را نمایش می‌دهد، نه جهت سود یا زیان را.
- **Where it comes from:** D، خطوط 580–638؛ `loadDashboard → getYesterdayData({ scope, currency })` → GET `/api/analytics/yesterday`؛ `yesterday.by_source` مبنای تفکیک است.
- **Filter behavior:** Scope/Currency اعمال می‌شوند؛ Date انتخابی به درخواست نمی‌رود و دوره دیروز مستقل است. Account ندارد.
- **Duplicate check:** داده مبنا با معاملات روز قبل در Trades هم‌پوشانی دارد؛ نمایش عین همین کارت در صفحه دیگر تأیید نشده است. این بخش تکرار Today نیست چون روز متفاوتی را نشان می‌دهد.
- **Necessity:** **مفید ولی غیرضروری**؛ مقایسه روزانه مفید است ولی می‌تواند فشرده‌تر کنار Today قرار گیرد.

#### 6. Active Prop Stage

- **What it shows:** برای هر مرحله فعال نام حساب و شرکت، نوع مرحله، آماده‌بودن برای پاس‌شدن، سود فعلی/هدف، درصد پیشرفت، روزهای معاملاتی و DD روزانه/کل نمایش داده می‌شود. در صورت تخلف، اولین پیام تخلف دیده می‌شود؛ نبود مرحله با EmptyState و لینک Prop مشخص است.
- **Where it comes from:** D، خطوط 640–724؛ `getDashboardData → prop_progress`. Backend، خطوط 478–502، مراحل ACTIVE را با ارز حساب انتخاب می‌کند و از `PropRuleEngine.evaluate_stages` نتیجه می‌گیرد؛ endpoint همان GET `/api/analytics/dashboard` است.
- **Filter behavior:** با اینکه درخواست اصلی Date/Scope/Currency دارد، query مراحل فقط وضعیت فعال و Currency را محدود می‌کند؛ Date/Scope بر این شاخه پاسخ اعمال نمی‌شوند. Account selector ندارد و همه مراحل فعال ارز منتخب نمایش داده می‌شوند.
- **Duplicate check:** جزئیات حساب، قوانین و وضعیت مراحل متعلق به Prop است؛ این خلاصه زمینه مشترک دارد، نه الزاماً نمایش دقیقاً یکسان. هشدار اولین تخلف ممکن است با بخش 7 نیز هم‌موضوع باشد.
- **Necessity:** **ضروری** برای کاربر دارای پراپ فعال؛ پایش ریسک فوری مناسب Dashboard است، درحالی‌که مدیریت جزئیات باید در Prop بماند.

#### 7. Prop Alerts

- **What it shows:** کارت شرطی پیام‌های خوانده‌نشده با تعداد هشدار، رنگ شدت بر اساس ایموجی پیام و دکمه «خواندم». وقتی `alerts.length === 0` است، این کارت اصلاً رندر نمی‌شود؛ در همان ErrorBoundary وضعیت پراپ قرار دارد.
- **Where it comes from:** D، خطوط 726–751؛ `loadDashboard → getPropAlerts({ unread_only: true })` → GET `/api/prop/alerts`. کلیک «خواندم» با `markAlertRead` به PATCH `/api/prop/alerts/{alertId}/read` می‌رود و سپس ردیف از state حذف می‌شود.
- **Filter behavior:** Date/Scope/Currency/Account ارسال نمی‌شوند؛ تنها unread_only ثابت است. بنابراین این هشدارها الزاماً به مراحل ارز منتخب در بخش 6 محدود نیستند.
- **Duplicate check:** Prop نیز `getPropAlerts/markAlertRead` دارد؛ App تعداد خوانده‌نشده‌ها را از همان منبع می‌گیرد. تکرار هشدار در نقطه ورود برنامه کاربردی است، هرچند همگامی state محلی این نماها در این Task ارزیابی نشده است.
- **Necessity:** **ضروری**؛ اعلان ریسک فوری با تکرار عادی گزارش تفاوت دارد و به‌دلیل شرطی‌بودن، در حالت بدون هشدار فضای دائمی نمی‌گیرد.

#### 8. Finance Section — ظرف و ترتیب داخلی

- **What it shows:** یک Card با عنوان «مالی»، ابتدا زیرعنوان «وضعیت حال» و کارت‌های موجودی کل، جریان نقدی و تفکیک حساب‌ها؛ سپس «عملکرد» با سود خالص، دارایی شخصی و روند دارایی. هر ردیف در نمایش بزرگ سه ستون دارد.
- **Where it comes from:** D، خطوط 753–875؛ stateهای `finance/spendable/netProfit/assetTrend` از شش wrapper در `loadDashboard` پر می‌شوند؛ endpoint هر زیرکارت در ادامه آمده است. ظرف مالی تابع دریافت مستقل ندارد.
- **Filter behavior:** Date/Scope/Account هیچ زیرکارت مالی را فیلتر نمی‌کنند. Currency روی برخی درخواست‌ها، روی موجودی کل فقط در UI و روی دو نمایش چندارزی اصلاً اعمال نمی‌شود.
- **Duplicate check:** بخش بزرگی از این محتوا در Finance نیز وجود دارد؛ اشتراک endpointهای summary/cashflow/accounts/net-profit/spendable-assets قابل مشاهده است. یکسان‌بودن همه مجموع‌ها از این اشتراک نتیجه نمی‌شود.
- **Necessity:** **مفید ولی غیرضروری** به شکل فعلی؛ خلاصه مالی کوتاه مناسب است، اما شش زیرکارت جای زیادی به مسئولیت صفحه Finance می‌دهند.

##### 8.1. موجودی کل

- **What it shows:** مقدار بزرگ `assets_by_currency[currency]` و در خط زیر فهرست همه ارزها و موجودی آن‌ها. انتخاب ارز فقط عدد برجسته را عوض می‌کند؛ خط تفکیک همچنان چندارزی است.
- **Where it comes from:** D، خطوط 759–775؛ `getFinanceSummary()` → GET `/api/finance/summary` → `finance.summary.assets_by_currency`.
- **Filter behavior:** Date/Scope/Account خیر؛ Currency در درخواست ارسال نمی‌شود و فقط کلید خواندن پاسخ در UI است.
- **Duplicate check:** Finance نیز summary را می‌گیرد؛ با مجموع دارایی شخصی 8.5 هم‌موضوع است، ولی بدون بررسی قرارداد محاسبات نباید این دو را برابر دانست.
- **Necessity:** **مفید ولی غیرضروری**؛ یک موجودی مرجع می‌تواند در خلاصه مالی بماند، مشروط به توضیح دامنه آن.

##### 8.2. جریان نقدی

- **What it shows:** نمودار ستونی درآمد و هزینه با زیرعنوان «۶ ماه اخیر». کد واقعاً شش مورد آخر آرایه پاسخ (`slice(-6)`) را نمایش می‌دهد، نه بازه تاریخ انتخابی Dashboard را.
- **Where it comes from:** D، خطوط 776–790؛ `getFinanceCashflow({ currency })` → GET `/api/finance/charts/cashflow` → `finance.cashflow`؛ BarChart از Recharts.
- **Filter behavior:** فقط Currency به API می‌رود؛ Date/Scope/Account خیر. year نیز از Dashboard ارسال نمی‌شود، بنابراین تعبیر دقیق «۶ ماه اخیر» به دامنه پاسخ backend وابسته است.
- **Duplicate check:** Finance همین endpoint را دریافت و cashflow را در LineChart نمایش می‌دهد؛ داده مشترک است، نوع نمودار متفاوت.
- **Necessity:** **متعلق به صفحه دیگر**؛ تحلیل جریان نقدی در Finance کامل‌تر است و در Dashboard می‌تواند به خلاصه‌ای کوتاه تبدیل شود.

##### 8.3. تفکیک حساب‌ها

- **What it shows:** نام و مانده شش حساب اول پاسخ با ارز اختصاصی هر حساب. این فهرست انتخاب‌گر Account نیست و کلیک انتخاب حساب نیز ندارد.
- **Where it comes from:** D، خطوط 791–808؛ `getFinanceAccounts()` → GET `/api/finance/accounts` → `finance.accounts.slice(0, 6)`؛ JSX inline.
- **Filter behavior:** Date/Scope/Currency/Account خیر؛ حتی Currency منتخب، حساب‌های نمایش‌داده‌شده را محدود نمی‌کند.
- **Duplicate check:** فهرست و مدیریت حساب‌ها در Finance وجود دارد؛ اینجا تنها زیرمجموعه‌ای از همان حساب‌ها بدون ابزار مدیریت نمایش داده می‌شود.
- **Necessity:** **متعلق به صفحه دیگر**؛ محدودیت شش حساب بدون معیار اولویت در UI ارزش خلاصه مدیریتی را محدود می‌کند.

##### 8.4. سود خالص مالی

- **What it shows:** سود Real، هزینه‌ها و حاصل نهایی سود خالص با زیرعنوان «سود Real منهای هزینه‌ها». این تعریف با PnL معامله در کارت بالای صفحه متفاوت است.
- **Where it comes from:** D، خط 301 و خطوط 812–840؛ `getNetProfit({ currency })` → GET `/api/finance/net-profit`؛ `currencyProfit = netProfit.by_currency[currency] || netProfit`.
- **Filter behavior:** Currency به درخواست و انتخاب شاخه پاسخ اعمال می‌شود؛ Date/Scope/Account خیر.
- **Duplicate check:** Finance همین endpoint و مقادیر را در بخش سود خالص نمایش می‌دهد. با بخش 3 هم‌پوشانی در سود Real دارد ولی به‌دلیل کسر هزینه‌ها، تکرار دقیق net_pnl نیست.
- **Necessity:** **مفید ولی غیرضروری**؛ تمایز سود معامله با سود پس از هزینه‌ها برای خلاصه مالی مفید است، اگر برچسب‌ها واضح باشند.

##### 8.5. دارایی شخصی

- **What it shows:** جدول محل نگهداری شامل بروکر شخصی، صرافی، تراست ولت، کیف‌پول، بانک، کارت و نقد، با دو ستون USDT و ریال و مجموع هرکدام. توضیح زیر جدول تصریح می‌کند سرمایه و سود دریافت‌نشده پراپ در مجموع نیست.
- **Where it comes from:** D، خطوط 841–848؛ `getSpendableAssets()` → GET `/api/finance/spendable-assets` → کامپوننت `FinancialAssetBalances` در `i:\trade\MokTradeDesk\frontend\src\components\FinancialAssetBalances.tsx`. کامپوننت فقط props می‌خواند و API مستقل ندارد.
- **Filter behavior:** Date/Scope/Currency/Account خیر؛ همواره هر دو ارز نمایش داده می‌شوند.
- **Duplicate check:** Finance دقیقاً همان endpoint و همان کامپوننت را مصرف می‌کند؛ این مورد تکرار واقعی نمایش است، نه صرفاً اشتراک مفهوم.
- **Necessity:** **تکراری**؛ جدول کامل مناسب Finance است؛ اگر خلاصه دارایی در Dashboard لازم باشد، نمایش مجموع‌ها کافی‌تر است.

##### 8.6. روند دارایی

- **What it shows:** دو سری تجمعی `total_usdt` و `total_irr` روی نمودار Area با محور تاریخ. فقط با بیش از یک نقطه نمودار رندر می‌شود؛ نمودار دو ارز را هم‌زمان و روی یک محور Y نمایش می‌دهد.
- **Where it comes from:** D، خطوط 849–872؛ `getAssetTrend()` → GET `/api/finance/asset-trend` → `trendRes.data.trend` → Recharts AreaChart inline.
- **Filter behavior:** Date/Scope/Currency/Account خیر؛ با وجود پشتیبانی wrapper از date_from/date_to، D هیچ پارامتری ارسال نمی‌کند.
- **Duplicate check:** تکرار دقیق این endpoint/نمودار در Finance در بررسی حاضر تأیید نشد؛ نمودار جریان نقدی و روند سود/زیان همان روند دارایی نیستند.
- **Necessity:** **متعلق به صفحه دیگر**؛ ماهیت تحلیل دارایی به Finance نزدیک‌تر است. هم‌محورشدن دو واحد پول متفاوت نیز نیاز به توضیح دارد.

#### 9. Prop Goals / پیشرفت اهداف

- **What it shows:** PnL ماه، فصل و سال با سه ProgressBar؛ برای ماه درصد تغییر نسبت به ماه قبل و برای فصل/سال دوباره PnL نشان داده می‌شود. برخلاف label مرز خطا (`Prop goals`)، این بخش از `prop_progress` یا هدف سود مرحله استفاده نمی‌کند.
- **Where it comes from:** D، خطوط 877–940؛ `getDashboardData` → GET `/api/analytics/dashboard` → `periods`. نوار ماه از قدرمطلق `change_percent` و نوار فصل/سال از نسبت PnL آن دوره به PnL ماه ساخته و در 100 محدود می‌شود؛ هدف قابل‌تنظیم در این محاسبه نیست.
- **Filter behavior:** Date/Scope/Currency همانند periods بخش Today اعمال می‌شوند؛ Account خیر. متن «عملکرد واقعی» در UI ثابت است ولی Scope می‌تواند backtest/forward/all باشد، پس Real بودن داده از متن قابل استنتاج نیست.
- **Duplicate check:** PnL ماه/فصل/سال عیناً با بخش 4 مشترک است؛ تنها مقایسه ماه و نمایش نوارها افزوده شده‌اند. این کارت با اهداف واقعی مرحله در بخش 6 از نظر معنا متفاوت است.
- **Necessity:** **تکراری**؛ ادغام در Today مناسب‌تر است. عنوان اهداف و نسبت‌های نوارها بدون هدف واقعی، ارزش توضیحی محدودی دارند.

#### 10. Backtest Performance

- **What it shows:** انتخاب نسخه استراتژی، سود خالص بک‌تست، نرخ برد، Profit Factor، تعداد معاملات بسته، میانگین R-Multiple و لینک «برو به تحلیل کامل». حالت‌های نسخه‌نداشتن، loading و نبود داده مجزا هستند.
- **Where it comes from:** D، خطوط 191–196، 245–269 و 942–1014؛ `getAllVersions()` → GET `/api/strategies/versions/all`؛ effect مستقل `getDashboardData({ scope: 'backtest', currency: 'USDT', version_id })` → GET `/api/analytics/dashboard`. انتخاب در `mok_dashboard_version` نگهداری و برای ناوبری در `analysis_selected_version` نوشته می‌شود.
- **Filter behavior:** Date/Scope/Currency/Account نوار اصلی هیچ‌کدام اعمال نمی‌شوند؛ نسخه انتخابی فیلتر محلی است و ارز USDT/دامنه backtest ثابت‌اند. Refresh اصلی نیز این effect مستقل را مستقیماً دوباره فراخوانی نمی‌کند.
- **Duplicate check:** Analysis مقصد صریح تحلیل کامل نسخه و میزبان KPIهای مشابه است؛ خلاصه مستقل Dashboard نقش میانبر دارد، نه منبع تحلیلی منحصربه‌فرد.
- **Necessity:** **متعلق به صفحه دیگر**؛ برای داشبورد متمرکز بر پول واقعی، این کارت زمینه متفاوتی دارد؛ اگر نگه داشته شود باید استقلال فیلترش کاملاً روشن باشد.

#### 11. Charts row — Equity / WinLoss / PnL Distribution

- **What it shows:** به ترتیب کد: منحنی سرمایه با تعداد نقاط/روزهای اعلام‌شده، نمودار برد/باخت با تعداد معاملات بسته و histogram توزیع PnL با تعداد معامله در هر بازه. سه Card مستقل در یک grid و ErrorBoundary مشترک‌اند.
- **Where it comes from:** D، خطوط 1016–1035؛ `getDashboardData` → GET `/api/analytics/dashboard` → `equity_curve/win_loss/pnl_distribution`. کامپوننت‌ها در `i:\trade\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx`، `i:\trade\MokTradeDesk\frontend\src\components\charts\WinLossPieChart.tsx` و `i:\trade\MokTradeDesk\frontend\src\components\charts\PnLDistributionChart.tsx` قرار دارند و در این مصرف API نمی‌زنند.
- **Filter behavior:** هر سه به Date/Scope/Currency درخواست اصلی وابسته‌اند؛ Account وجود ندارد. نمودار برد/باخت عدد پول نشان نمی‌دهد، ولی Currency مجموعه معاملات مبنا را محدود می‌کند.
- **Duplicate check:** Analysis هر سه کامپوننت را استفاده می‌کند، اما Equity را از trades می‌سازد و PnLDistribution را در حالت مبتنی بر trades/تفکیک نماد به کار می‌برد؛ بنابراین اشتراک کامپوننت به معنی تکرار دقیق histogram نیست. برد/باخت نیز با KPI بخش 3 هم‌موضوع ولی با دامنه متفاوت است.
- **Necessity:** **مفید ولی غیرضروری**؛ منحنی سرمایه دید سریع خوبی می‌دهد؛ جزئیات توزیع و تحلیل برد/باخت را می‌توان در Analysis نگه داشت.

#### 12. Recent Trades

- **What it shows:** حداکثر ده معامله بسته، شامل نماد، جهت، استراتژی، PnL و تاریخ بسته‌شدن؛ لینک «مشاهده همه» به Trades می‌رود. PnL نمایشی در frontend از جمع `pnl + commission + swap` محاسبه می‌شود؛ در حالت خالی دکمه ثبت معامله دیده می‌شود.
- **Where it comes from:** D، خطوط 1037–1089؛ `loadDashboard → getTrades({ status: 'closed', limit: 10, sort_by: 'close_time', sort_order: 'desc', currency })` → GET `/api/trades/` → `recentTrades`.
- **Filter behavior:** فقط Currency ارسال می‌شود؛ Date/Scope/Account خیر. بنابراین این جدول لزوماً نماینده بازه و دامنه نمودارهای بالای آن نیست.
- **Duplicate check:** Trades همان موجودیت‌ها را با جدول کامل‌تر و ابزار مدیریت نمایش می‌دهد؛ اینجا عمداً پیش‌نمایش محدود همان اطلاعات است.
- **Necessity:** **مفید ولی غیرضروری**؛ مرور سریع فعالیت و دسترسی به صفحه معاملات مفید است، مشروط به توضیح دامنه مستقل از فیلترهای بالا.

#### 13. Open Trades

- **What it shows:** نماد، جهت، استراتژی و ستون با عنوان «سود/زیان لحظه‌ای». اگر `pnl` تهی باشد خط تیره نشان داده می‌شود؛ در غیر این صورت جمع pnl/commission/swap است. در کد D اتصال قیمت زنده یا polling اختصاصی این جدول دیده نمی‌شود؛ ساعت یک‌ثانیه‌ای هدر داده معاملات را تازه نمی‌کند.
- **Where it comes from:** D، خطوط 1090–1128؛ `loadDashboard → getTrades({ status: 'open', sort_by: 'open_time', sort_order: 'desc', currency })` → GET `/api/trades/` → `openTrades`. limit صریحی ارسال نمی‌شود؛ نبود limit در caller تضمین دریافت نامحدود از backend نیست.
- **Filter behavior:** فقط Currency ارسال می‌شود؛ Date/Scope/Account خیر. شمارش عنوان، طول آرایه پاسخ است و با `summary.open_trades` بخش Today که فقط Scope دارد الزاماً برابر نیست.
- **Duplicate check:** Trades میزبان ردیف‌های معاملاتی و فیلتر وضعیت است؛ نمایش این ردیف‌ها تکرار اطلاعات است اما برای پایش سریع وضعیت باز کاربرد مستقل دارد.
- **Necessity:** **ضروری**؛ خلاصه مواجهه باز برای Dashboard مهم است. تعبیر «لحظه‌ای» باید از تضمین واقعی به‌روزبودن داده تفکیک شود.

#### 14. Any other section — حالت‌های جایگزین و مرز صفحه

- **What it shows:** پیش از بدنه، در loading فقط DashboardSkeleton؛ در خطای اولیه بدون data پیام خطا؛ و در نبود data خروجی null نمایش داده می‌شود. در بدنه نیز EmptyStateها و fallbackهای ErrorBoundary جایگزین بخش مربوط‌اند. پس از Open Trades بخش محتوایی دیگری در D نیست؛ اخبار داخل widget هدر است، نه بخش مستقل پایین صفحه.
- **Where it comes from:** D، خطوط 286–298 و پایان 1129–1133؛ `i:\trade\MokTradeDesk\frontend\src\components\Skeleton.tsx`، `i:\trade\MokTradeDesk\frontend\src\components\ErrorBoundary.tsx`، `i:\trade\MokTradeDesk\frontend\src\components\ui\EmptyState.tsx` و `i:\trade\MokTradeDesk\frontend\src\components\ToastProvider.tsx`. endpoint مستقل جدیدی ندارند؛ Toast بازخورد عملیات موجود است و بخش ثابت انتهای Dashboard نیست.
- **Filter behavior:** فیلتر مستقل Date/Scope/Currency/Account ندارند؛ تغییرات و خطاهای بارگذاری می‌توانند وضعیت نمایش را عوض کنند. Theme و سایر کنترل‌های پوسته در App خارج از درخت بخش‌های D هستند.
- **Duplicate check:** این اجزای عمومی در سایر صفحات هم استفاده می‌شوند، ولی reuse رابط کاربری «داده تکراری» نیست.
- **Necessity:** **ضروری**؛ برای نمایش وضعیت بارگذاری/خطا/نبود داده و جلوگیری از خراب‌شدن کل تجربه صفحه لازم‌اند.

### جمع‌بندی ممیزی Task 2 و محدوده اعتبارسنجی

- ترتیب واقعی ۱۳ بخش اصلی و شش زیرکارت Finance ثبت شد؛ شماره ۱۴ صرفاً تعیین تکلیف سایر حالت‌هاست.
- ناسازگاری‌های دامنه مهم: Real مستقل از Date/Scope؛ دیروز مستقل از Date؛ مراحل پراپ فقط وابسته به Currency؛ هشدارها بدون فیلترهای صفحه؛ بک‌تست نسخه‌ای با USDT ثابت؛ جداول معاملات فقط وابسته به Currency. Account filter در Dashboard وجود ندارد.
- مهم‌ترین تکرارهای دقیق: PnL دوره‌ها بین Today و «پیشرفت اهداف»، و جدول FinancialAssetBalances بین Dashboard و Finance. اشتراک نمودارها با Analysis به‌تنهایی تکرار دقیق داده نیست.
- Theme در App است؛ «Prop Goals» هدف پراپ نیست؛ Refresh و PDF همه contextهای صفحه را پوشش نمی‌دهند. این موارد فقط مستند شدند و هیچ اصلاح کدی انجام نشد.
- بررسی بر مبنای خواندن source محلی، تطبیق JSX، wrapperهای API، صفحات مقصد و شاخه‌های مربوط در backend انجام شد؛ صحت جامع محاسبات مالی و رفتار runtime خارج از دامنه این Task است. build/test اجرا نشد چون تغییر فقط Markdown است. Git/GitHub استفاده نشد و محتوای Task 1 برای افزودن این بخش بازنویسی نشد.

## Task 3a/13 — KPI Data Flow

### دامنه و مسیرهای مشترک

مبنای این بخش source محلی است؛ شماره خطوط به نسخه بررسی‌شده اشاره دارند. چهار کارت بالای Dashboard از **Real Summary** می‌آیند، نه `data.summary` درخواست اصلی. خلاصه بک‌تست، Today و شمارنده کلی از **Analytics Dashboard** می‌آیند. Average Win/Loss در پاسخ Analytics وجود دارند، اما در Dashboard مصرف نمایشی ندارند؛ برای آن‌ها مسیر دریافت ثبت شده، نه یک کارت فرضی. هیچ تغییر کد یا اصلاح محاسبه انجام نشده است.

برای خوانایی توضیحات، **R** یعنی `GET /api/finance/real-summary?currency={USDT|IRR}`، **A** یعنی `GET /api/analytics/dashboard` با `date_from/date_to` اختیاری حاصل `computeRange` و `scope/currency` انتخابی، و **B** یعنی همان endpoint با `scope=backtest&currency=USDT&version_id={selected.id}` و بدون تاریخ. این حروف صرفاً ارجاع به requestهای واقعی‌اند:

- R: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:206` → `getRealSummary` در `i:\trade\MokTradeDesk\frontend\src\api\client.ts:153` → `get_real_summary` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1446` → `setRealSummary` در `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:219`.
- A: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:204` → `getDashboardData` در `i:\trade\MokTradeDesk\frontend\src\api\client.ts:142` → `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309` → `setData` در `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:217`.
- B: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:263` → همان wrapper/endpoint A → `setBacktestSummary` در خط 264 همان فایل. Date/Scope/Currency نوار اصلی روی این request مستقل اعمال نمی‌شوند.
- Yesterday: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:205` → `getYesterdayData` در `i:\trade\MokTradeDesk\frontend\src\api\client.ts:150` → `GET /api/analytics/yesterday?scope={scope}&currency={currency}` → `get_yesterday_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:566`.

**DB مشترک R:** query پایه در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1483` روی `trades` با LEFT OUTER JOIN به `personal_trading_accounts`، `prop_stages` و `prop_accounts`؛ فقط `close_time IS NOT NULL` و یکی از دو شاخه REAL_PERSONAL با ارز حساب شخصی یا REAL_PROP با مرحله FUNDED_REAL و ارز حساب پراپ. Date/Scope/Account انتخابی ندارد. aggregate در خط 1495 با `COUNT/SUM/CASE/COALESCE` و `.one()` است؛ query جداگانه مرتب‌شده برای DD در خط 1515 اجرا می‌شود.

**DB مشترک A/B:** `_scope_filter` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:100` روی `trades`، با joinهای حساب شخصی/مرحله/حساب پراپ برای محدودکردن ارز و `_apply_scope` در خط 81 برای نوع معامله. شبیه‌سازی فقط با ارز USDT پذیرفته می‌شود؛ انتخاب ارز تبدیل ارز نیست. اگر هر مرز تاریخ وجود داشته باشد، خطوط 118–123 فقط معاملات بسته را با مقایسه `close_time` نگه می‌دارند؛ بدون تاریخ، `scoped_q` می‌تواند معاملات باز را نیز شامل شود. `version_id` در خط 333 فیلتر مستقیم `trades.version_id` است، نه query روی نتایج تحلیل ذخیره‌شده. aggregate خط 338 از `COUNT/SUM/CASE/MAX/MIN` و `.one()` استفاده می‌کند. این KPIها از `analysis_results` یا `analysis_runs` خوانده نمی‌شوند و وجود import مربوط به AnalysisService به معنی فراخوانی آن در این مسیر نیست.

نام جدول‌ها با مدل‌ها تطبیق داده شد: `i:\trade\MokTradeDesk\backend\app\models\strategy.py:127` → `trades`؛ `i:\trade\MokTradeDesk\backend\app\models\trading.py:46` → `personal_trading_accounts`؛ `i:\trade\MokTradeDesk\backend\app\models\prop.py:142` و `:160` → `prop_accounts/prop_stages`.

### 1. Net PnL

**Net PnL**
- Frontend: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:466` — کارت Real مقدار `realSummary.net_pnl` را با علامت مثبت شرطی و برچسب ارز می‌خواند؛ خط 973 مقدار `backtestSummary.summary?.net_pnl || 0` را با `Number(...).toLocaleString('en-US')` و USDT ثابت نشان می‌دهد. خط 538 از `today.pnl` و خط 593 از `yesterday.net_pnl` استفاده می‌کند؛ این‌ها contextهای متفاوت همین مفهوم‌اند.
- API: R یعنی `GET /api/finance/real-summary` با `currency`؛ B یعنی `GET /api/analytics/dashboard` با `scope=backtest,currency=USDT,version_id`؛ Today از A با `date_from,date_to,scope,currency` و دیروز از `GET /api/analytics/yesterday` با `scope,currency` می‌آید. wrapperها و callerهای دقیق در مسیرهای مشترک بالا ثبت شده‌اند.
- Backend: `get_real_summary` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1446`؛ `SUM(net)` در خط 1497 و گردکردن در 1505، خروجی `net_pnl` در 1543. `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309`؛ `SUM(net)` خط 341، `tnp` خط 351 و `summary.net_pnl` خط 507. Today از aggregate شرطی خط 448 و خروجی خط 526؛ `get_yesterday_data` خط 566 از جمع Python در 611–613 و خروجی 635 استفاده می‌کند.
- Service: R از `_trade_net_expr` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1234` و A/B از `_net_expr` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:42` به `net_pnl_sql` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:27` می‌رسند: `COALESCE(pnl,0)+COALESCE(commission,0)+COALESCE(swap,0)`. دیروز `metrics.net_pnl` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:22` را روی ORM rowها صدا می‌زند. AnalysisService برای این KPI فراخوانی نمی‌شود.
- DB: R و A/B همان جدول‌ها و queryهای مشترک بالا؛ R فقط بسته‌ها، ولی `SUM(net)` خلاصه A/B روی کل scoped_q است و بدون مرز تاریخ می‌تواند PnL ذخیره‌شده معاملات باز را نیز جمع کند. Today از `closed_scope` با شرط زمان شروع امروز استفاده می‌کند. دیروز در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:586` تمام معاملات بسته scope/ارز را با `.all()` می‌خواند و سپس بازه روز قبل تهران را در Python محدود می‌کند، نه با SQL SUM روزانه.
- Notes: nullهای سه جزء PnL صفر محسوب و خروجی‌ها تا دو رقم اعشار گرد می‌شوند؛ commission/swap با علامت ذخیره‌شده جمع می‌شوند، نه اینکه دوباره به‌عنوان هزینه کم شوند. fallback بک‌تست صفر است؛ نبود Real Summary یا `total_trades=0` در `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:442` کل ردیف Real را با EmptyState جایگزین می‌کند. Sparkline ردیف Real در backend آخرین ۳۰ روز **دارای معامله** از منحنی تجمعی است، نه تضمین ۳۰ روز تقویمی؛ frontend خط 470 در نبود سری `[0]` می‌گذارد. **«سود خالص» مالی همان net_pnl نیست**؛ مسیر جداگانه آن در یادداشت تکمیلی پایین آمده است.

### 2. Win Rate

**Win Rate**
- Frontend: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:475` — `(realSummary.win_rate * 100).toFixed(1)`؛ خط 980 — `(Number(backtestSummary.summary?.win_rate || 0) * 100).toFixed(1)`. همین ضرب در 100 در Today خط 545 و Yesterday خط 598 نیز انجام می‌شود. MiniPie در خط 479 به‌جای این مقدار از تعداد برد/باخت با fallback صفر استفاده می‌کند.
- API: `GET /api/finance/real-summary?currency={currency}` برای Real؛ `GET /api/analytics/dashboard` با پارامترهای A برای Today و با پارامترهای B برای بک‌تست؛ `GET /api/analytics/yesterday?scope={scope}&currency={currency}` برای دیروز.
- Backend: `get_real_summary` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1446`، فرمول در خط 1511: `winning_trades / total_trades * 100`. `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309`، فرمول خلاصه در خط 360: `wins_n / closed_count * 100` و Today در خط 464؛ خروجی‌ها در خطوط 508 و 528. `get_yesterday_data` در همان فایل خط 566، فرمول/خروجی درصد در خط 634.
- Service: تشخیص برد با net خالص از `net_pnl_sql` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:27`؛ تقسیم و تبدیل به درصد داخل endpoint است، نه `AnalysisService` یا `calculate_basic_metrics`. دیروز از `net_pnl` در خط 22 همان سرویس و شمارش Python استفاده می‌کند؛ مرز روز از `tehran_day_bounds` گرفته می‌شود.
- DB: R از `COUNT(trades.id)` و `SUM(CASE net>0 THEN 1 ELSE 0)` روی query بسته‌های Real استفاده می‌کند. A/B برد را با `close_time IS NOT NULL AND net>0` می‌شمارد و مخرج تعداد بسته‌هاست؛ Today همین الگو را با شرط روز روی closed_scope اعمال می‌کند. جدول‌ها/joinها همان مسیر مشترک‌اند؛ دیروز SELECT ORM و شمارش در Python دارد.
- Notes: **ناسازگاری قطعی واحد در source:** backend هر چهار مسیر را در مقیاس 0–100 می‌فرستد ولی frontend دوباره ×100 می‌کند؛ مثلاً پاسخ 50 به `5000.0٪` تبدیل می‌شود. این یافته مستند شد و اصلاح نشد. معامله صفر در مخرج بسته‌ها هست ولی برد/باخت محسوب نمی‌شود؛ بنابراین Pie مبتنی بر wins/losses الزاماً مخرج یکسانی با نرخ برد ندارد. در نبود معامله نرخ backend صفر، و خروجی backend دو رقم اعشار است.

### 3. Profit Factor

**Profit Factor**
- Frontend: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:484` — `realSummary.profit_factor >= 999 ? '∞' : ...toFixed(2)`؛ خط 987 همین منطق را روی `Number(backtestSummary.summary?.profit_factor || 0)` اجرا می‌کند. MiniBars خطوط 490–491 از gross_profit/gross_loss با fallback صفر است، نه از PF.
- API: `GET /api/finance/real-summary` با `currency` برای Real؛ `GET /api/analytics/dashboard` با `scope=backtest,currency=USDT,version_id` برای کارت بک‌تست. A نیز `summary.profit_factor` را برمی‌گرداند، ولی چهار کارت بالای صفحه از آن نمی‌خوانند.
- Backend: `get_real_summary` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1446`؛ gross_profit/gross_loss در 1508–1509 گرد و PF در 1512 محاسبه می‌شود. `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309`؛ grossها در 352–353، فراخوان helper در 361 و خروجی گرد‌شده در 510.
- Service: R محاسبه PF را inline انجام می‌دهد و helper مشترک PF را صدا نمی‌زند. A/B از `profit_factor_from_sums` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:109` استفاده می‌کنند. هر دو برای net پایه به `net_pnl_sql` در خط 27 همان فایل متکی‌اند؛ سرویس‌ها DB query مجزا برای PF ندارند.
- DB: `trades` با joinهای مسیر R یا A/B؛ دو `SUM(CASE...)` برای net مثبت و net منفی معاملات بسته. قدرمطلق جمع منفی مخرج می‌شود. کل سود/زیان اینجا بر اساس net معامله بعد از commission/swap است، نه فقط ستون pnl.
- Notes: در وجود زیان، PF=سود بردها/قدر مطلق زیان باخت‌ها. **در نبود زیان و وجود سود، R مقدار 100.0 و A/B مقدار sentinel برابر 999.0 برمی‌گردانند**؛ UI اولی را `100.00` و دومی را ∞ نشان می‌دهد. اگر هیچ سود/زیانی نباشد هر دو صفرند. R قبل از تقسیم grossها را گرد می‌کند ولی A/B بعد از تقسیم PF را گرد می‌کنند؛ در مقادیر کوچک تفاوت ممکن است. آستانه UI هر PF واقعی ≥999 را نیز بی‌نهایت نشان می‌دهد، نه فقط sentinel را.

### 4. Max Drawdown

**Max Drawdown**
- Frontend: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:500` — `realSummary.max_dd` با پیشوند منفی و برچسب ارز، تحت عنوان «حداکثر ضرر». خط 507 همین max_dd را در MiniBars می‌گذارد. `data.summary.max_dd` و `backtestSummary.summary.max_dd` دریافت می‌شوند ولی کارت مستقلی در D آن‌ها را نمایش نمی‌دهد؛ بنابراین منبع عدد کارت visible، R است نه A/B.
- API: `GET /api/finance/real-summary?currency={currency}` مسیر کارت؛ `GET /api/analytics/dashboard` با پارامترهای A یا B مسیر max_dd موجود در پاسخ تحلیلی/منحنی سرمایه است. هیچ پارامتر انتخاب Account یا تبدیل ارزی در این callerها وجود ندارد.
- Backend: `get_real_summary` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1446`؛ SELECT مرتب در 1515–1518، equity تجمعی از صفر در 1521–1524، DD در 1525 و خروجی 1546. `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309`؛ query مرتب در 370–379، تعیین سرمایه اولیه در 393، engineها در 397–400 و `summary.max_dd` در 509.
- Service: R از `max_drawdown` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:44` استفاده می‌کند: بزرگ‌ترین فاصله peak قبلی تا equity جاری. A/B از `_scope_initial_balance` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:204` و adapter `_equity_trade` در خط 233، سپس `calculate_equity_curve` در `i:\trade\MokTradeDesk\backend\app\domain\risk\equity_engine.py:6`، `calculate_peak_to_trough_dd` در `i:\trade\MokTradeDesk\backend\app\domain\risk\drawdown_engine.py:35` و `calculate_static_dd` در همان فایل خط 23 استفاده می‌کنند؛ بیشینه دو dd برگردانده می‌شود. EquityEngine خود `metrics.net_pnl` را فراخوانی می‌کند؛ adapter چون net از قبل محاسبه شده، commission/swap را صفر می‌گذارد تا دوباره جمع نشوند.
- DB: query R روی همان چهار جدول، projection محدود close_time/net و `ORDER BY close_time ASC, id ASC` با `.all()`؛ aggregate SQL برای DD وجود ندارد و محاسبه در حافظه است. A/B نیز closed_scope را با net، id و شناسه حساب/مرحله می‌خوانند؛ برای سرمایه اولیه Real/all، SELECTهای جدا روی `personal_trading_accounts` و `prop_stages` (با join به `prop_accounts` برای ارز) انجام می‌شود و initial_balance هر شناسه متمایز یک‌بار جمع می‌شود. برای backtest/forward سرمایه فرضی 10000 است؛ نبود مجموع مثبت در مسیر دیگر نیز همین fallback را می‌دهد.
- Notes: خروجی DD مبلغ غیرمنفی و گرد‌شده تا دو رقم است، نه درصد؛ UI علامت منفی اضافه می‌کند و حتی صفر می‌تواند به‌شکل `-0` دیده شود. R به کل تاریخ Real و ارز محدود است؛ A/B فقط معاملات بسته دامنه منتخب را می‌گیرند و floating PnL وارد منحنی این مسیر نمی‌شود. **MiniBars با برچسب «بزرگترین ضرر» در `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:506` در واقع `gross_loss` یعنی مجموع زیان‌ها را می‌خواند، نه بزرگ‌ترین ضرر تک‌معامله.**

### 5. Trade Count

**Trade Count**
- Frontend: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:551` — `summary.total_trades`؛ خط 548 — `summary.open_trades`؛ خط 542 — `today.trades_count`؛ خط 585 — `yesterday.total_trades`؛ خط 994 — `Number(backtestSummary.summary?.closed_trades || 0)`. `realSummary.total_trades` در خط 442 شرط EmptyState است، نه کارت مستقل تعداد. عنوان جداول در خطوط 1044 و 1094 صرفاً `recentTrades.length/openTrades.length` را می‌خواند.
- API: A یعنی `GET /api/analytics/dashboard` با `date_from,date_to,scope,currency`؛ B با `scope=backtest,currency=USDT,version_id`؛ R یعنی `GET /api/finance/real-summary` با `currency`؛ دیروز `GET /api/analytics/yesterday` با `scope,currency`. طول جدول از `GET /api/trades/` می‌آید: recent با `status=closed,limit=10,sort_by=close_time,sort_order=desc,currency` و open با `status=open,sort_by=open_time,sort_order=desc,currency`؛ این طول آرایه، KPI aggregate فوق نیست.
- Backend: `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309`؛ total/closed در 339–340 و 349–350، open query در 410، Today در 449 و 457، خروجی در 511–513 و 527. `get_real_summary` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1446`؛ COUNT در 1496 و مقدار در 1504/1547. `get_yesterday_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:566`؛ `len(yt)` در 624 و خروجی 631.
- Service: شمارش داخل endpoint انجام می‌شود؛ helperهای `_scope_filter/_apply_scope` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:100` و `:81` دامنه را می‌سازند. helper محاسبه KPI یا AnalysisService برای COUNT فراخوانی نمی‌شود. مرز Today/Yesterday با `tehran_day_bounds` تعیین می‌شود.
- DB: R روی query بسته‌های Real، `COUNT(trades.id)` است. A/B total روی scoped_q و closed از `SUM(CASE close_time IS NOT NULL THEN 1 ELSE 0)` است؛ هر دو با joinهای مشترک. open query جدا `COUNT` روی `trades` و در scope=real با join مرحله، فقط `close_time IS NULL` و Scope دارد؛ **Currency/Date/version_id را اعمال نمی‌کند**. Today جمع شرطی روی closed_scope؛ دیروز SELECT تمام بسته‌های scope/ارز و سپس محدودکردن تاریخ و len در Python است.
- Notes: total در A/B بدون تاریخ می‌تواند باز+بسته باشد؛ با هر مرز تاریخ فقط بسته‌ها باقی می‌مانند. total در R همیشه بسته است و عدد بک‌تست در UI نیز صریحاً closed_trades است. معاملات سربه‌سر در count هستند؛ بنابراین total الزاماً wins+losses نیست. شمارنده open بالای صفحه ممکن است با طول جدول open متفاوت باشد چون اولی Scope دارد ولی Currency ندارد و دومی Currency دارد ولی Scope ارسال نمی‌کند؛ محدودیت پاسخ جدول نیز باید جدا از شمارش کل در نظر گرفته شود.

### 6. Average Win

**Average Win**
- Frontend: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:217` — پاسخ A شامل `summary.avg_win` در `data` ذخیره می‌شود؛ خط 264 پاسخ B را در `backtestSummary` نگه می‌دارد. **هیچ خواندن یا render مستقیم `avg_win` در DashboardPage وجود ندارد**؛ R نیز این فیلد را برنمی‌گرداند. این مسیر دریافت داده است، نه KPI قابل‌مشاهده فعلی.
- API: `GET /api/analytics/dashboard` با `date_from,date_to,scope,currency` برای A یا `scope=backtest,currency=USDT,version_id` برای B؛ wrapper `getDashboardData` در `i:\trade\MokTradeDesk\frontend\src\api\client.ts:142`. endpoint مجزای Average Win فراخوانی نمی‌شود.
- Backend: `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309`؛ gross_profit از aggregate خط 342 و wins_n از 344؛ فرمول خط 362: `gp / wins_n if wins_n else 0.0`؛ خروجی `summary.avg_win` در خط 517.
- Service: فقط net پایه از `_net_expr` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:42` → `net_pnl_sql` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:27`. تقسیم داخل endpoint است؛ با وجود helper `calculate_basic_metrics` در همان سرویس، این endpoint آن را برای avg_win صدا نمی‌زند.
- DB: `trades` و joinهای A/B؛ در همان aggregate مشترک دو `SUM(CASE...)` برای مجموع net بردها و تعداد بردها با شرط معامله بسته و net>0. query `AVG` مجزا برای avg_win وجود ندارد؛ AVG خط 367 مربوط به `r_multiple` است، نه این KPI.
- Notes: میانگین مبلغ net مثبت است، نه میانگین R یا PnL خام. معاملات صفر و زیان‌ها از مخرج حذف می‌شوند؛ اگر بردی نباشد صفر، خروجی تا دو رقم اعشار گرد می‌شود. Date/Scope/Currency/version_id همان query اصلی را محدود می‌کنند؛ frontend fallback نمایشی ندارد چون نمایش وجود ندارد.

### 7. Average Loss

**Average Loss**
- Frontend: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:217` و `:264` — پاسخ A/B حاوی `summary.avg_loss` ذخیره می‌شود، ولی **هیچ مصرف یا render مستقیم `avg_loss` در DashboardPage نیست**. R این فیلد را ندارد؛ عنوان «حداکثر ضرر» نیز avg_loss نیست و به max_dd وصل است.
- API: `GET /api/analytics/dashboard` با `date_from,date_to,scope,currency` برای A؛ همان مسیر با `scope=backtest,currency=USDT,version_id` برای B؛ `getDashboardData` در `i:\trade\MokTradeDesk\frontend\src\api\client.ts:142`.
- Backend: `get_dashboard_data` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:309`؛ جمع net زیان‌ها در خط 343، تعداد در 345، قدرمطلق مجموع در 353؛ فرمول خط 363: `gl / losses_n if losses_n else 0.0`؛ خروجی `summary.avg_loss` در 518.
- Service: net SQL از `net_pnl_sql` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:27`، با واسط `_net_expr` در `i:\trade\MokTradeDesk\backend\app\api\analytics.py:42`؛ قدرمطلق و تقسیم داخل endpoint‌اند، نه فراخوان AnalysisService یا `calculate_basic_metrics`.
- DB: `trades` و joinهای مشترک A/B؛ `SUM(CASE closed AND net<0 THEN net ELSE 0)` و `SUM(CASE closed AND net<0 THEN 1 ELSE 0)` در همان query aggregate. `AVG` مستقیم DB برای این فیلد استفاده نشده است.
- Notes: خروجی این endpoint **بزرگی مثبت میانگین زیان** است و تا دو رقم گرد می‌شود؛ بدون باخت صفر. این قرارداد را نباید با `calculate_basic_metrics` در `i:\trade\MokTradeDesk\backend\app\services\metrics.py:149` که میانگین علامت‌دار منفی برمی‌گرداند یکسان گرفت؛ آن helper در مسیر Dashboard استفاده نمی‌شود. معاملات صفر و برنده وارد مخرج نمی‌شوند؛ نمایش/fallback فرانت برای این KPI وجود ندارد.

### یادداشت تکمیلی Net PnL در برابر سود خالص مالی

کارت مالی در `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:833` از `currencyProfit.net_profit` می‌خواند؛ انتخاب شاخه ارز/fallback در خط 301 است. مسیر آن `getNetProfit` در `i:\trade\MokTradeDesk\frontend\src\api\client.ts:784` → `GET /api/finance/net-profit?currency={currency}` → `get_net_profit` در `i:\trade\MokTradeDesk\backend\app\api\finance.py:1558` است. این تابع `_compute_real_pnl` در خط 1325 و `_expenses_total` در خط 1370 همان فایل را صدا می‌زند و `real_pnl - expenses` را تا دو رقم گرد می‌کند؛ Service مستقل AnalysisService ندارد و net معامله باز هم از metrics.net_pnl_sql می‌آید.

DB این شاخه دو SUM/COUNT روی `trades` با INNER JOIN به مرحله/حساب پراپ یا حساب شخصی برای ارز است؛ شرط `Trade.pnl IS NOT NULL` دارد، **نه الزام close_time یا test_type معادل R**. هزینه‌ها SUM(amount) از جدول `transactions` برای typeهای FEE/PURCHASE، ارز منتخب و `is_deleted=False` هستند؛ نام جدول در `i:\trade\MokTradeDesk\backend\app\models\finance.py:133` تعریف شده است. پس اختلاف این کارت با Real Summary را نمی‌توان صرفاً به کسر هزینه نسبت داد؛ دامنه query سود پایه هم متفاوت است. پاسخ by_currency هر دو ارز را محاسبه می‌کند، ولی تبدیل ارز انجام نمی‌دهد.

### نتیجه و اعتبارسنجی Task 3a

- هفت KPI با Frontend/API/Backend/Service/DB/Notes ثبت شدند؛ دو KPI Average Win/Loss صریحاً «دریافت‌شده ولی نمایش‌داده‌نشده» هستند.
- یافته‌های مهم: ضرب دوباره Win Rate در 100، sentinel متفاوت PF، اختلاف دامنه شمار معاملات باز، اختلاف معاملات باز/بسته در Net PnL مسیرها، و برچسب «بزرگترین ضرر» روی gross_loss. هیچ‌یک در این Task اصلاح نشدند.
- اعتبارسنجی این Task، تطبیق source و queryها و کنترل سند است؛ برنامه، API زنده یا query واقعی DB اجرا نشده و build/test برنامه برای این تغییر مستنداتی اجرا نمی‌شود. شماره خطوط و محاسبات گزارش‌شده از source هستند، نه نتیجه آزمایش runtime.
- تنها فایل مجاز برای تغییر `i:\trade\MokTradeDesk\DASHBOARD_AUDIT.md` است؛ متن Taskهای قبلی حفظ و این بخش append شده است. فایل نهایی طبق درخواست با UTF-8 with BOM ذخیره می‌شود. Git/GitHub استفاده نشد.