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
## Task 3b/13 — Chart Data Flow

Source-only audit of the current local checkout at `C:\MokTradeDesk`. No application code was changed; no live API/DB execution was needed for this trace. Line references describe the inspected source. Earlier audit sections are preserved unchanged.

### Shared chart request and trade filters

The three trading charts read the main dashboard response, not `realSummary` and not the separate version-specific `backtestSummary`. `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:200-226` computes the date range, requests data, stores `dash.data` in `data`, stores cash flow in `finance.cashflow`, and stores `trendRes.data.trend || []` in `assetTrend`. Main response chart fields are destructured at line 300. The independent backtest request at line 263 does not feed these charts.

The analytics request passes optional `date_from/date_to` and selected `scope/currency`. `C:\MokTradeDesk\backend\app\api\analytics.py:81-124` applies scope and currency with joins to `personal_trading_accounts`, `prop_stages`, and `prop_accounts`: real means REAL_PERSONAL or REAL_PROP with FUNDED_REAL stage; backtest/forward select their own test types; all omits the scope-type restriction. Backtest/forward trades only pass the currency predicate for USDT. Currency is a filter, not FX conversion. `close_time` is filtered by supplied dates. `_parse_bound` at line 47 treats naive ISO dates as UTC and expands a date-only upper bound to 23:59:59 (not the following midnight, so fractional timestamps later in that last second are excluded). Invalid date strings silently become absent bounds. Invalid scope returns HTTP 400. The backend supports `version_id`, but the main chart request does not send it.

All chart loads are part of one `Promise.all` (`C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:203`): one rejected request prevents the subsequent state assignments. Initial failure displays the page error; refresh failure can retain previously loaded data (lines 229-235 and 290-298). Cash Flow and Asset Trend are refetched on dashboard filter changes, but receive only the parameters described below. API router prefixes are registered in `C:\MokTradeDesk\backend\app\main.py:189,194`.

### 1. Equity Curve

**Equity Curve**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:1020-1021` — reads `data.equity_curve`, passes `equity_curve || []` with height 240, and labels its length as days. Loaded through `getDashboardData` at line 204 and `setData(dash.data)` at line 217.
- **Component:** `C:\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx:11` — ready-made series is mapped to `{index, date, equity}` at lines 14-16, then rendered as a Recharts AreaChart.
- **API:** `GET /api/analytics/dashboard?scope={scope}&currency={currency}` plus optional `date_from={r.from}&date_to={r.to}`; wrapper `C:\MokTradeDesk\frontend\src\api\client.ts:142-148`. No `version_id` is sent by this chart's main request.
- **Backend:** `get_dashboard_data`, `C:\MokTradeDesk\backend\app\api\analytics.py:309`; closed-trade projection at 370-379, initial balance/domain call at 393-397, serialization at 412-418, response `equity_curve` at 533.
- **Service:** `_net_expr` (analytics.py:42) calls `net_pnl_sql` in `C:\MokTradeDesk\backend\app\services\metrics.py:27`: `COALESCE(pnl,0) + COALESCE(commission,0) + COALESCE(swap,0)`. `_scope_initial_balance` in `C:\MokTradeDesk\backend\app\api\analytics.py:204` obtains opening capital. `_equity_trade` at 233 wraps already-net PnL with zero commission/swap, avoiding double application. `calculate_equity_curve` in `C:\MokTradeDesk\backend\app\domain\risk\equity_engine.py:6` calls `metrics.net_pnl`, starts with an opening point, and cumulatively adds each closed trade. No AnalysisService or persisted analysis result is used for the curve.
- **DB:** `trades`, with the shared scope/date/currency joins and `close_time IS NOT NULL`; selects `close_time`, net expression, `id`, `personal_trading_account_id`, `prop_stage_id`, ordered by `close_time ASC, id ASC`, without pagination. Opening balance separately reads `personal_trading_accounts WHERE id IN (referenced personal IDs)` with currency filter and `prop_stages WHERE id IN (referenced stage IDs)` joined to `prop_accounts` for currency; Python sums each referenced account/stage's `initial_balance` once. Backtest/forward use 10000 directly; other scopes fall back to 10000 if the sum is nonpositive.
- **Notes:** Realized equity only; no floating PnL or deposit/withdrawal history is incorporated. Output is one initial point (`date: null`) plus one point per closed trade, not daily aggregation; equity rounds to two decimals. Date filtering changes which trades/accounts seed the curve and does not carry forward pre-range trading PnL. The frontend's days subtitle is therefore misleading. X-axis uses point index and tooltip says trade number, not date. Tooltip hardcodes USDT even when IRR is selected. The component type declares `date: string` although the opening point is null; this field is not used on the X-axis. Fewer than two points produces the no-data message. Its legacy fallback uses `trades`, raw `pnl`, and `initialBalance`, but Dashboard supplies none of those, so an empty series also results in no data.

### 2. Win/Loss Pie

**Win/Loss Pie**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:1024-1028` — reads `data.win_loss`, defaults missing wins/losses to zero, and labels their sum as closed trades. Loaded at lines 204/217 and destructured at 300.
- **Component:** `C:\MokTradeDesk\frontend\src\components\charts\WinLossPieChart.tsx:9` — constructs two count-based slices (wins and losses), renders a donut, legend, and trade-count tooltip.
- **API:** `GET /api/analytics/dashboard?scope={scope}&currency={currency}` plus optional `date_from/date_to`; `C:\MokTradeDesk\frontend\src\api\client.ts:142-148`. No chart-specific request or `version_id`.
- **Backend:** `get_dashboard_data`, `C:\MokTradeDesk\backend\app\api\analytics.py:309`; win/loss predicates at 329-331, aggregate at 338-348, counts at 354-355, `win_loss` object at 467 and response at 535.
- **Service:** `_scope_filter` and `_net_expr` in `C:\MokTradeDesk\backend\app\api\analytics.py:100,42`; the latter calls `C:\MokTradeDesk\backend\app\services\metrics.py:27` (`net_pnl_sql`). Classification is based on net PnL including commission/swap. Counts are aggregated directly in the endpoint; no analysis service is called for them.
- **DB:** `trades` plus the shared scope/currency joins; in one scoped aggregate, `SUM(CASE WHEN close_time IS NOT NULL AND net > 0 THEN 1 ELSE 0 END)` gives wins, and the analogous `net < 0` expression gives losses. Optional dates apply to `close_time`. NULL aggregate results become zero.
- **Notes:** Open trades and exact-net-zero breakeven trades are excluded from both slices. Consequently wins + losses (and the subtitle) may be less than the actual closed count, and the pie's proportions need not equal backend win_rate, whose denominator includes all closed trades. Both zero produces an empty-state message, including an all-breakeven dataset. Counts are passed directly: no win_rate or percentage multiplication is involved.

### 3. PnL Distribution

**PnL Distribution**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:1031-1032` — reads `data.pnl_distribution` and passes `pnl_distribution || []` with height 240. Loaded at 204/217 and destructured at 300.
- **Component:** `C:\MokTradeDesk\frontend\src\components\charts\PnLDistributionChart.tsx:10` — Dashboard uses the ready-made bucket BarChart branch at 12-50: X=`range`, Y=`count`, integer Y ticks, per-bucket colors and trade-count tooltip.
- **API:** `GET /api/analytics/dashboard?scope={scope}&currency={currency}` plus optional `date_from/date_to`; `C:\MokTradeDesk\frontend\src\api\client.ts:142-148`. No separate distribution endpoint or `version_id` is used here.
- **Backend:** `get_dashboard_data`, `C:\MokTradeDesk\backend\app\api\analytics.py:309`; bucket definitions/query at 421-438, fixed-order zero-filled output at 439, response at 534.
- **Service:** `_scope_filter` and `_net_expr` in `C:\MokTradeDesk\backend\app\api\analytics.py:100,42`, using `net_pnl_sql` in `C:\MokTradeDesk\backend\app\services\metrics.py:27`. SQL CASE bucketing is implemented directly in the endpoint, not AnalysisService.
- **DB:** `trades` with shared scope/date/currency joins and `close_time IS NOT NULL`; `SELECT CASE ... END, COUNT(trades.id) ... GROUP BY CASE ... END`. Eight intervals are net < -500; [-500,-200); [-200,-50); [-50,0); [0,50); [50,200); [200,500); and net >= 500. No trade-row pagination or client-side binning.
- **Notes:** Counts all closed trades including zero-net trades (in `0..50`). Missing buckets are returned with count zero; all-zero buckets show no data. Last label is `> 500` although the predicate includes exactly 500. Thresholds remain the same numeric amounts for USDT and IRR, with no FX conversion or currency label in the bucket axis. Eight supplied buckets render a histogram, not the component's legacy symbol pie. If data is absent/empty, the fallback sees default empty `trades` and displays no data.

### 4. Cash Flow (finance)

**Cash Flow (finance)**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:208,220` — calls `getFinanceCashflow({ currency })`, stores `flow.data` in `finance.cashflow`; lines 777-784 render `finance.cashflow.slice(-6)` with `month`, `income`, and `expense`.
- **Component:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:776-789` — inline Recharts ResponsiveContainer/BarChart; no separate Cash Flow component file.
- **API:** `GET /api/finance/charts/cashflow?currency={currency}`; wrapper `C:\MokTradeDesk\frontend\src\api\client.ts:731-732` also supports optional Gregorian `year`, but Dashboard does not send it. No dashboard date range or trade scope is passed.
- **Backend:** `get_cashflow_chart`, `C:\MokTradeDesk\backend\app\api\finance.py:810`; target/base filter at 821-827, income/expense queries at 830-853, sorted merged month rows at 855-878.
- **Service:** `bank_income_filter` in `C:\MokTradeDesk\backend\app\services\financial_reporting.py:6` constructs the income SQL predicate. Expense types are `EXPENSE_TYPES_F` in `C:\MokTradeDesk\backend\app\api\finance.py:1282` (WITHDRAWAL, LOSS, FEE, PURCHASE). No WalletService calculation is invoked for this chart.
- **DB:** `transactions WHERE is_deleted = false AND currency = target` (default target USDT), optionally `EXTRACT(year FROM date) = year`. Two queries select extracted year/month and `SUM(amount)`, grouped and ordered by year/month. Income additionally requires amount > 0 and either DEPOSIT/PROFIT or a TRANSFER destination row (`account_id = to_account_id`, distinct source/destination) from a non-bank account into a bank account. The transfer predicate uses ORM relationship EXISTS checks against `accounts`. Expense query filters to the four expense types. Output merges both sets of month keys, fills a missing income/expense side with zero, and returns ascending Gregorian `YYYY-MM` rows.
- **Notes:** Shows financial-ledger inflows/outflows, not trade PnL and not net cashflow alone. DEPOSIT/PROFIT qualify regardless of destination account type; qualifying non-bank-to-bank transfers also count as income. No empty calendar months are generated: `slice(-6)` means last six populated months, not necessarily the last six calendar months despite the subtitle. No date/year restriction is requested, so old months can appear. Empty array shows no data. Currency filters rather than converts; amounts are summed directly without explicit rounding or absolute-value normalization in this endpoint.

### 5. Asset Trend (finance)

**Asset Trend (finance)**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:215,226` — calls `getAssetTrend()` without parameters and stores `trendRes.data.trend || []`. Lines 851-865 render the series with X=`date` and two areas, `total_usdt` and `total_irr`.
- **Component:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:849-870` — inline Recharts ResponsiveContainer/AreaChart; no separate Asset Trend component file.
- **API:** `GET /api/finance/asset-trend` with no query parameters from Dashboard. Wrapper `C:\MokTradeDesk\frontend\src\api\client.ts:822-825` and backend support optional ISO `date_from/date_to`; neither selected currency, scope, nor dashboard date range is sent.
- **Backend:** `get_asset_trend`, `C:\MokTradeDesk\backend\app\api\finance.py:1804`; signed transaction accumulation at 1812-1835, broker cash movement compensation at 1839-1849, chronological cumulative output at 1851-1862.
- **Service:** `filter_by_range` in `C:\MokTradeDesk\backend\app\utils\date_range.py:44` applies optional UTC bounds `[from midnight, day-after-to midnight)` to both queries. `_jalali_date_str` in `C:\MokTradeDesk\backend\app\api\finance.py:1288` converts timestamps to Tehran time using `to_tehran`, then to zero-padded Jalali dates; missing/unconvertible dates are skipped. No balance service, finance_metrics total, or WalletService is called for this series.
- **DB:** `transactions WHERE is_deleted = false`, optional date predicates, ordered by `date`, loaded with `.all()`; plus `broker_cash_movements` with the same optional date predicates, loaded with `.all()`. Both currencies are read. Transactions accumulate by Jalali day/currency: DEPOSIT, PROFIT, ADJUSTMENT add; WITHDRAWAL, LOSS, FEE, PURCHASE subtract; unlisted types (including TRANSFER and CONVERSION) are ignored. ADJUSTMENT preserves the amount's own sign. Broker movements add amount for `deposit_to_broker`, otherwise subtract amount, compensating the financial-ledger side of internal broker transfers. No account balance snapshot or trade table is queried for this chart.
- **Notes:** Starts each currency's cumulative total at zero, sorts populated Jalali days, and returns two-decimal totals. This is reconstructed transaction/movement flow, not a query of current aggregate assets; opening balances or trading PnL not represented in those inputs are not independently included. Optional date filtering would reset the cumulative series at the selected range instead of carrying in earlier balances. Days without contributing records are not filled. Null currency defaults to USDT. Both currencies share one Y-axis without conversion or normalization, so IRR magnitude can visually dominate USDT. The frontend requires more than one point, meaning a single day's valid result still displays the insufficient-data message. This chart remains all-history/both-currency regardless of Dashboard filters.

Validation: traced frontend callers, all five chart render paths, API wrappers/router prefixes, backend handlers, helper/domain functions, and ORM table names from local source. Only this audit document was updated. No Git/GitHub operations, application code edits, or database writes were performed for Task 3b.

## Task 3c/13 — Section Data Flow

Local source audit; no application code changes or live API/database writes. References use the current checkout. As traced in Task 3b, `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:198-243` loads the main sections in one Promise.all and assigns state only after all requests succeed. A failed request can prevent all main-section updates; refresh errors can leave old data displayed. Backtest versions and performance use independent effects. Dashboard date/scope controls do not automatically constrain every section.

### 1. Recent Trades

**Recent Trades**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:210,221` requests closed trades and stores `closed.data.trades || []`; lines 1041-1088 display symbol, direction, strategy, net PnL and close date.
- **Component:** Inline table in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:1058`; shared `C:\MokTradeDesk\frontend\src\components\ui\EmptyState.tsx` for an empty list.
- **API:** `GET /api/trades/?status=closed&limit=10&sort_by=close_time&sort_order=desc&currency={currency}`; wrapper `C:\MokTradeDesk\frontend\src\api\client.ts:489-511`. No date, scope, version or account filter is sent.
- **Backend:** `get_trades`, `C:\MokTradeDesk\backend\app\api\trades.py:276`; currency joins at 304-314, status at 342-343, count/paging/order at 353-388, response at 400-406.
- **Service:** Direct ORM query; `_serialize_trade_summary` in `C:\MokTradeDesk\backend\app\api\trades.py:181` resolves strategy/version names and returns stored PnL fields. `_get_screenshots_count_map` at 165 supplies counts even though this table does not display them. No AnalysisService or price feed is used.
- **DB:** `trades WHERE close_time IS NOT NULL`, LEFT JOIN `personal_trading_accounts`, `prop_stages`, `prop_accounts` for currency. Predicate allows REAL_PERSONAL with matching personal currency, REAL_PROP with matching prop-account currency, or BACKTEST/FORWARD when selected currency is USDT. No FUNDED_REAL-only restriction. Counts matching rows, then orders close_time DESC NULLS LAST, OFFSET 0 LIMIT 10. Eager loads `strategy_versions -> strategies` and personal account; batches `screenshots` counts by entity_id where entity_type='trade' and ID belongs to the returned page.
- **Notes:** Shows latest ten matching closed trades across test types, not necessarily the main dashboard scope. Frontend recomputes `(pnl || 0)+(commission || 0)+(swap || 0)`, displays two decimals and selected currency. Dates use browser `toLocaleDateString('fa-IR')`, not an explicit Tehran timezone. Any direction other than 'buy' renders as sell; missing strategy renders a dash. Subtitle is returned-row count, not API total. Equal close timestamps have no explicit ID tie-breaker. Empty list renders the new-trade action; View All navigates to trades.

### 2. Open Trades

**Open Trades**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:211,222` stores `open.data.trades || []`; lines 1091-1127 display symbol, direction, strategy and purported live PnL.
- **Component:** Inline table in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:1100`; shared `C:\MokTradeDesk\frontend\src\components\ui\EmptyState.tsx`.
- **API:** `GET /api/trades/?status=open&sort_by=open_time&sort_order=desc&currency={currency}` via `C:\MokTradeDesk\frontend\src\api\client.ts:489-511`. No explicit limit/page, date, scope, version or account parameter.
- **Backend:** `get_trades`, `C:\MokTradeDesk\backend\app\api\trades.py:276`; defaults page=1/page_size=50 at 293-294, open predicate at 340-341, serialization at 395-405.
- **Service:** Same direct ORM/serialization and batched screenshot-count helpers as Recent Trades; no market-data valuation service.
- **DB:** Same currency joins and test-type alternatives as Recent Trades, but `trades.close_time IS NULL`; count followed by ORDER BY open_time DESC NULLS LAST, OFFSET 0 LIMIT 50. Same eager-loaded strategy/account and screenshot-count queries.
- **Notes:** At most 50 rows are displayed; response total/pages are ignored and no pager exists here. Thus subtitle is not the total open-position count. Includes challenge-stage and simulation trades permitted by currency, regardless of selected dashboard scope. PnL comes from stored API values, not streaming quotes. Frontend adds commission/swap but displays a dash whenever raw `t.pnl` is null/undefined, even if costs exist. No periodic trade polling is configured in this page; the one-second timer only updates the clock. Empty list says there are no open trades.

### 3. Prop Stage

**Prop Stage**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:204,217,300` reads main response `prop_progress`; lines 640-724 render every stage's account/firm, stage badge, current_profit, profit_target, progress, trading days, DD limits and first violation.
- **Component:** Inline stage cards in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:656`; `C:\MokTradeDesk\frontend\src\components\ui\ProgressBar.tsx`, `C:\MokTradeDesk\frontend\src\components\ui\Badge.tsx`, and `C:\MokTradeDesk\frontend\src\components\ui\EmptyState.tsx`.
- **API:** `GET /api/analytics/dashboard` with optional date_from/date_to and selected scope/currency, via `C:\MokTradeDesk\frontend\src\api\client.ts:142-148`. Although sent to the endpoint, date/scope do not constrain the prop_progress branch.
- **Backend:** `get_dashboard_data`, `C:\MokTradeDesk\backend\app\api\analytics.py:309`; active-stage query at 479-484, bulk evaluation at 486, per-stage fallback/enrichment at 487-502.
- **Service:** `PropRuleEngine.evaluate_stages` in `C:\MokTradeDesk\backend\app\services\prop_rule_engine.py:70`, falling back to `evaluate_stage` at 52 if needed; `_evaluate_stage_with_trades` at 105 uses `metrics.net_pnl`, domain equity/drawdown engines, `_daily_drawdowns` at 639 and `_group_daily_pnl` at 613. Rule evaluation here computes output; it does not persist alerts or update stage status.
- **DB:** `prop_stages JOIN prop_accounts WHERE stage.status=ACTIVE AND account.currency={currency}`, eager-loading account and `prop_firms`. Bulk engine fetches stages WHERE id IN selected IDs and all `trades WHERE prop_stage_id IN selected IDs`; no date/test-type/closed-only query filter. Open/closed separation is performed in Python. Limits, modes, capital, share and withdrawal totals come from stage fields; no rule_violations table read is needed for displayed violations.
- **Notes:** Current profit and target progress use closed net PnL; floating net PnL affects equity-basis DD only. Opening capital falls back to 10000 when falsy. Daily grouping uses stage UTC offset (default +210 minutes); displayed max_daily_loss is maximum over evaluated days, not necessarily today. DD supports static/trailing and balance/equity modes. Missing limits/target or invalid modes fail closed as unconfigured; funded stages are never ready_to_pass. Frontend clamps only progress bar to 0..100, keeps numeric percentage unbounded, highlights DD utilization above 50%, and shows only the first violation. All active challenge/funded stages in the currency can appear even under backtest scope. No stages produces a navigation empty state. Separate goal bars at lines 877-940 use `periods` trading performance, not stage targets.

### 4. Prop Alerts

**Prop Alerts**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:212,223` fetches/stores alerts; lines 726-750 render message/count and a mark-read button. Line 740 removes the row locally only after PATCH succeeds.
- **Component:** Inline alert card in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:727`; no dedicated alert component.
- **API:** `GET /api/prop/alerts?unread_only=true`; interaction `PATCH /api/prop/alerts/{id}/read`, no body. Wrappers in `C:\MokTradeDesk\frontend\src\api\client.ts:116-120`. Dashboard supplies no stage_id and does not call the separate generate endpoint.
- **Backend:** `get_alerts` at `C:\MokTradeDesk\backend\app\api\prop.py:1109`; `mark_alert_read` at 1134.
- **Service:** Direct ORM reads/update; no rule-engine evaluation or alert regeneration occurs in these handlers.
- **DB:** `prop_alerts WHERE is_read=false ORDER BY created_at DESC`, all rows, no pagination or stage-status/currency join. PATCH queries by id, raises 404 if absent, sets is_read=true and commits.
- **Notes:** Alerts may belong to inactive stages or another currency and are not limited by date/scope. 'Active alerts' means unread stored rows, not freshly verified rule violations. Severity colors are inferred from message emoji (danger, warning, otherwise green), not a severity field. Zero alerts hides the whole card. PATCH errors are silently swallowed by the UI. The write path was inspected only, not invoked during this audit.

### 5. Finance sub-cards

**Finance — Total Balance**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:207,220,760-774` stores `sum.data`; reads `finance.summary.assets_by_currency[currency] || 0` and lists all currency totals underneath.
- **Component:** Inline card in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:759`.
- **API:** `GET /api/finance/summary` without parameters; wrapper `C:\MokTradeDesk\frontend\src\api\client.ts:713-714` supports currency, but Dashboard selects the returned currency map locally.
- **Backend:** `get_finance_summary`, `C:\MokTradeDesk\backend\app\api\finance.py:520`, asset accumulation at 532-536.
- **Service:** Asset totals are computed directly. Additional response fields call `_bank_income_sum`, `_tx_sum`, `_tx_count` in `C:\MokTradeDesk\backend\app\api\finance.py:1256,1242,1269`; these ledger statistics are not shown in this card.
- **DB:** Reads all `accounts`, sums balance by currency in Python; no is_archived filter. Additional per-currency transactions SUM/COUNT queries exclude deleted rows; income uses bank_income_filter, expenses use WITHDRAWAL/LOSS/FEE/PURCHASE, transfers use TRANSFER.
- **Notes:** Financial-wallet balance only, not personal trading-account balance or prop capital. Includes archived accounts unlike the breakdown card. Missing currency defaults to USDT during aggregation. No FX conversion/date/scope restriction. Missing summary displays loading.

**Finance — Account Breakdown**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:209,220,791-807` reads `finance.accounts.slice(0,6)` and displays name, balance and each account's currency.
- **Component:** Inline list in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:795`.
- **API:** `GET /api/finance/accounts` with no parameters; wrapper `C:\MokTradeDesk\frontend\src\api\client.ts:644-645` supports type/currency but neither is sent.
- **Backend:** `get_accounts`, `C:\MokTradeDesk\backend\app\api\finance.py:141`.
- **Service:** Direct ORM serialization, `_mask_card_number` for an unused response field; no balance recalculation service.
- **DB:** `accounts WHERE is_archived=false ORDER BY created_at DESC`; all rows returned, optional backend type/currency filters unused.
- **Notes:** Shows newest six nonarchived financial accounts across currencies, not largest balances or personal broker accounts. Client truncates; no pagination. Empty list displays no-accounts message; null balances become zero.

**Finance — Net Profit (Real PnL / Expenses / Net)**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:214,225,301` selects `netProfit.by_currency[currency] || netProfit`; lines 813-839 display real_pnl, expenses and net_profit.
- **Component:** Inline card in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:812-840`.
- **API:** `GET /api/finance/net-profit?currency={currency}`; `C:\MokTradeDesk\frontend\src\api\client.ts:784-788`; no dates/scope.
- **Backend:** `get_net_profit`, `C:\MokTradeDesk\backend\app\api\finance.py:1558`.
- **Service:** `_compute_real_pnl` and `_expenses_total` in `C:\MokTradeDesk\backend\app\api\finance.py:1325,1370`; `_trade_net_expr` at 1234 calls `net_pnl_sql` in `C:\MokTradeDesk\backend\app\services\metrics.py:27`.
- **DB:** SUM(net)/COUNT from `trades` joined to `prop_stages -> prop_accounts` WHERE stage_type=FUNDED_REAL, matching currency and pnl IS NOT NULL; separately trades joined to `personal_trading_accounts` WHERE matching currency and pnl IS NOT NULL. Expenses SUM(amount) from `transactions WHERE is_deleted=false AND type IN (FEE,PURCHASE) AND currency=target`. Both currency maps computed, rounding to two decimals.
- **Notes:** Unlike Real Summary, no explicit close_time or test_type condition: open trades with stored pnl can contribute. Includes full funded PnL, not profit-share or cash received. All-history; net equals combined broker/funded PnL minus expenses. Expenses exclude withdrawals/loss transactions counted in Cash Flow. Frontend prefixes expense with minus; missing response shows loading. No FX conversion.

**Finance — Personal Assets**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:213,224,841-847` passes spendRes.data as assets.
- **Component:** `C:\MokTradeDesk\frontend\src\components\FinancialAssetBalances.tsx:13`; seven account-type rows, by_currency values at 30, currency totals at 39-40.
- **API:** `GET /api/finance/spendable-assets`, no params; `C:\MokTradeDesk\frontend\src\api\client.ts:771-774`.
- **Backend:** `get_spendable_assets`, `C:\MokTradeDesk\backend\app\api\finance.py:1389`.
- **Service:** Direct grouped balance queries. Also calls `finance_metrics.prop_stage_3` in `C:\MokTradeDesk\backend\app\services\finance_metrics.py:92` for an unused legacy field, excluded from displayed totals.
- **DB:** `accounts`: SUM(balance) GROUP BY type,currency for exchange/trust_wallet/crypto_wallet/card/cash/bank; `personal_trading_accounts`: SUM(current_balance) GROUP BY currency for broker. No archived filter. Legacy field additionally reads FUNDED_REAL prop_stages and per-stage trade net through `_stage_net_pnl`, applying share minus total_withdrawn with zero floor.
- **Notes:** Always shows both currencies. Excludes prop capital/unreceived profit from personal total; received payouts already reside in account balances. Includes broker balances unlike Total Balance. Initializes missing values to zero; rounds components/totals. Missing response shows loading. Reads stored balances, not chart transaction reconstruction.

**Finance — Cash Flow**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:208,220,777-784` reads finance.cashflow.slice(-6), income/expense by month.
- **Component:** Inline Recharts BarChart in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:780`.
- **API:** `GET /api/finance/charts/cashflow?currency={currency}`; `C:\MokTradeDesk\frontend\src\api\client.ts:731-732`; optional year not sent.
- **Backend:** `get_cashflow_chart`, `C:\MokTradeDesk\backend\app\api\finance.py:810`.
- **Service:** `bank_income_filter` in `C:\MokTradeDesk\backend\app\services\financial_reporting.py:6`; expense list in `C:\MokTradeDesk\backend\app\api\finance.py:1282`.
- **DB:** Two monthly SUM(amount) queries on nondeleted transactions in selected currency, grouped/ordered by Gregorian year/month. Positive DEPOSIT/PROFIT and qualifying non-bank-to-bank transfer destination rows count as income (EXISTS checks on accounts). WITHDRAWAL/LOSS/FEE/PURCHASE count as expenses. Sorted union of populated months, missing side zero-filled.
- **Notes:** Last six populated months, not necessarily six calendar months. No date/scope filtering or empty-month generation. Empty response shows no data. Full chart trace is in Task 3b.

**Finance — Asset Trend**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:215,226,851-865` reads assetTrend with date,total_usdt,total_irr.
- **Component:** Inline Recharts AreaChart in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:853`.
- **API:** `GET /api/finance/asset-trend`, no params; `C:\MokTradeDesk\frontend\src\api\client.ts:822-825` supports optional date bounds not sent here.
- **Backend:** `get_asset_trend`, `C:\MokTradeDesk\backend\app\api\finance.py:1804`.
- **Service:** `filter_by_range` in `C:\MokTradeDesk\backend\app\utils\date_range.py:44`; `_jalali_date_str` in `C:\MokTradeDesk\backend\app\api\finance.py:1288` converts Tehran dates to Jalali.
- **DB:** Nondeleted transactions ordered by date plus broker_cash_movements; optional dates unused here. Adds DEPOSIT/PROFIT/ADJUSTMENT, subtracts WITHDRAWAL/LOSS/FEE/PURCHASE, ignores other transaction types; broker deposit movements add, other directions subtract. Groups by Jalali day/currency, cumulatively sums from zero.
- **Notes:** All-history/both currencies, independent of main filters. Not a balance snapshot: absent opening balances/trading PnL are not independently included. More than one populated day required; no gap filling, one shared Y-axis without conversion. Full chart trace is in Task 3b.

### 6. Backtest Performance

**Backtest Performance**
- **Frontend:** `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:160-161,192-196` restores version from localStorage and loads versions. Lines 245-269 select a valid version (otherwise newest created_at, then highest ID), persist it and request backtestSummary. Lines 942-1013 render selector, net_pnl, sparkline, win_rate, profit_factor, closed_trades and avg_r_multiple.
- **Component:** Inline section in `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:943`; `C:\MokTradeDesk\frontend\src\components\ui\StatCard.tsx` and `C:\MokTradeDesk\frontend\src\components\ui\EmptyState.tsx`.
- **API:** `GET /api/strategies/versions/all` without params (`C:\MokTradeDesk\frontend\src\api\client.ts:186`), then `GET /api/analytics/dashboard?scope=backtest&currency=USDT&version_id={selected.id}` (`C:\MokTradeDesk\frontend\src\api\client.ts:142-148`). No date range or main scope/currency.
- **Backend:** `get_all_versions`, `C:\MokTradeDesk\backend\app\api\strategies.py:188`; `get_dashboard_data`, `C:\MokTradeDesk\backend\app\api\analytics.py:309`, version filter at 333-334, aggregates at 338-367, sparkline at 393-402, summary at 506-524.
- **Service:** `_trades_count_by_version` in `C:\MokTradeDesk\backend\app\api\strategies.py:24`. Analytics uses `_scope_filter`/`_net_expr`, `net_pnl_sql` and `profit_factor_from_sums` in `C:\MokTradeDesk\backend\app\services\metrics.py:27,109`; sparkline uses `calculate_equity_curve` in `C:\MokTradeDesk\backend\app\domain\risk\equity_engine.py:6` with 10000 simulation capital. No AnalysisService analysis invocation.
- **DB:** All strategy_versions with select-in loaded strategies; trades counts grouped by version_id (not restricted to backtest). Performance reads trades WHERE test_type=BACKTEST AND version_id=selected through analytics currency joins (simulation accepted for USDT). SUM(net) includes all scoped rows, including open trades; win/loss aggregates condition on closed trades and net sign. Closed count includes breakevens. AVG(r_multiple) is over closed trades. Closed projection ordered by close_time,id feeds cumulative equity; sparkline contains last up to 20 cumulative net points. Full analytics endpoint executes other dashboard branches too, even though this section only reads summary/sparkline. No analysis_results/analysis_runs reads for these KPIs.
- **Notes:** Independent effect depends on versions/selectedVersionId, not main filters or main refresh callback. Cancellation guard prevents stale version responses from setting state. Versions failure becomes an empty list; summary failure becomes a no-data message. Successful zero-trade summary is truthy and displays zero KPIs. Win rate is already 0..100 and uses toFixed(1) without multiplication. PF helper returns 999 for profit/no losses, zero for neither; UI displays infinity for any PF >=999, including a finite high PF. Missing R-multiple displays 0.00. Only net PnL uses returned sparkline; other two use [0]. View Analysis writes analysis_selected_version and navigates, not an analyze API call.

Validation: traced all six requested section groups and all six Finance sub-cards through frontend callers, components, API handlers, helpers and ORM queries. Source audit only, not runtime balance reconciliation. Only this document was edited; no Git/GitHub operations, application code edits, builds or database writes were performed for Task 3c.

## Task 4/13 — Filter Analysis

Sources: `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:68-97,164-278`; `C:\MokTradeDesk\backend\app\api\analytics.py:47-124,309-555`. Yes means effective main-filter propagation, not just refetching. No account selector exists. Currency filters data, not FX conversion.

| Section | Date | Scope | Currency | Account | Independent |
|---|---|---|---|---|---|
| Real KPI cards / mini charts | No; all history | Fixed personal + funded real | Yes | None | real-summary request |
| Today PnL / win rate / day count | Selected range intersected with today | Yes | Yes | None | Main closed_scope |
| Banner total trades | Yes; bounds exclude open rows | Yes | Yes | None | Main scoped_q |
| Banner open trades | No | Yes | No | None | Scope-only count |
| Month / quarter / year / Goals | Selected range intersected with period | Yes | Yes | None | Main closed_scope |
| Yesterday | Fixed previous Tehran day | Yes | Yes | None | Separate request |
| Equity Curve | Yes; close_time | Yes | Yes; tooltip wrongly USDT | None | Main analytics |
| Win/Loss Pie | Yes | Yes | Yes | None | Main analytics |
| PnL Distribution | Yes | Yes | Yes | None | Main analytics |
| Recent Trades | No | No | Yes | None | Latest 10 closed |
| Open Trades | No | No | Yes | None | First 50 by default |
| Prop Stage | No | No; active stages | Yes | Stage association only | Own query inside analytics |
| Prop Alerts | No | No | No | Stored stage association | Unread stored alerts |
| Finance: Total Balance | No | No | Client map selection; both totals also shown | None | Summary request |
| Finance: Account Breakdown | No | No | All; per-row labels | No selector | Newest six nonarchived accounts |
| Finance: Net Profit | No | Fixed broker/funded coverage | Yes | None | Net-profit request |
| Finance: Personal Assets | No | No | Both | None | Spendable-assets request |
| Finance: Cash Flow | No; last six populated months | No | Yes | None | Cashflow request |
| Finance: Asset Trend | No | No | Both | None | Asset-trend request |
| Backtest Performance | No | Fixed backtest | Fixed USDT | None | Independent version selector/effect |

Defaults: all dates, real scope, USDT, persisted in localStorage. UI presets use Jalali month/quarter/year and Saturday week start. Backend period totals use Gregorian UTC period starts; Today uses Tehran day start. Date-only bounds are parsed as UTC; end is inclusive 23:59:59, excluding later fractional seconds. Invalid bounds silently become absent. Custom bounds may be one-sided. Period totals use the already filtered closed_scope: a narrow range can eliminate previous-month data and distort change percentage. Today/current-period predicates have no explicit upper-now bound, so future closes can contribute if stored.

Main requests share Promise.all; filter changes refetch independent sections without applying absent parameters. One failure blocks the whole batch's state assignments; stale data can remain. Main loader lacks a stale-response guard; Backtest has one and is not refreshed by the main refresh callback. PDF export receives no current filters, so filtered-screen equivalence is not established.

## Task 5/13 — Closed Trade Rule

Realized performance should require close_time IS NOT NULL. Open-position monitoring is a separate concern; stored pnl is not proof of live valuation.

| Check | Evidence | Assessment |
|---|---|---|
| Open Trade | Explicit open table and banner open count | Present intentionally. Table ignores main scope/date and is paginated; banner ignores currency/date. Counts need not agree. |
| Floating PnL | Open table adds stored pnl + commission + swap; Prop engine sums open net | Stored values, not a verified price feed. Null pnl displays a dash even if costs exist. |
| Live Equity | Main chart calls realized calculate_equity_curve | No standalone live-equity card. Prop risk engine can include floating net; Dashboard clock timer does not refresh valuation. |
| Open Exposure | Table shows symbol, direction, strategy, PnL | No aggregate notional, margin, size-at-risk or exposure KPI. |
| Unrealized PnL | Open table labels its stored net as instantaneous PnL | No separate unrealized-total card or market-price calculation on this path. |

**Closed-only passes:** Real Summary, Today, Yesterday, period totals, equity, win/loss, distribution, average R, streaks and Recent Trades use closed rows.

**Exceptions:** Analytics summary.net_pnl sums all scoped rows, including open stored net when no date bound is supplied. Independent Backtest always omits dates, so its Net PnL can disagree with its closed-only sparkline/PF/win rate. Finance Net Profit filters non-null pnl and account/stage coverage, not explicit close_time. PropRuleEngine separates closed and floating net: targets use closed_pnl; DD includes floating only for equity basis, not balance basis. This risk exception does not make the main curve floating-aware.

Sources: `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:198-269,1041-1127`; `C:\MokTradeDesk\backend\app\api\analytics.py:329-418`; `C:\MokTradeDesk\backend\app\api\finance.py:1325-1386,1445-1553`; `C:\MokTradeDesk\backend\app\services\prop_rule_engine.py:109-200`; `C:\MokTradeDesk\backend\app\domain\risk\equity_engine.py:6-51`.

## Task 6/13 — KPI Correctness

Table aliases: D = `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx`; A = `C:\MokTradeDesk\backend\app\api\analytics.py`; F = `C:\MokTradeDesk\backend\app\api\finance.py`; M = `C:\MokTradeDesk\backend\app\services\metrics.py`; P = `C:\MokTradeDesk\backend\app\services\prop_rule_engine.py`. Net n = coalesce(pnl,0)+coalesce(commission,0)+coalesce(swap,0). Signed costs are added once. W/L count positive/negative net; C includes all closed trades, including breakevens.

| KPI | Formula | Backend | Frontend | Unit | Double calc / correctness |
|---|---|---|---|---|---|
| Real Net PnL | SUM(n), closed personal/funded | F 1463-1509 | D 466 | Currency | Formatting only; fixed all-history population. |
| Backtest Net PnL | SUM(n), selected version/backtest | A 332-351,507 | D 973 | USDT | Formatting only; open net can contribute. |
| Win Rate: Real, Backtest, Today, Yesterday | 100*W/C; empty=0 | F 1511; A 360,464,634 | D 475,545,598,980 | Percent 0..100 | No extra *100 in any of four displays. Pie excludes breakevens, so slice percentage can differ. |
| Gross Profit / Loss | SUM(positive n), ABS(SUM(negative n)), closed | F 1495-1509; A 342-353 | D 490-491,506 | Currency | No frontend recalculation. Gross labels actually use net trade results. D 506 labels total gross_loss as largest loss: incorrect. |
| Real Profit Factor | GP/GL; no losses =>100 if profit, else 0 | F 1512 | D 484, infinity at >=999 | Ratio | Backend policy differs from shared helper; no-loss Real PF shows 100.00 instead of infinity. Uses rounded GP/GL. |
| Backtest Profit Factor | GP/GL; no losses =>999 if profit, else 0 | A 361; M 109-120 | D 987 | Ratio | No client division. Finite PF >=999 also becomes infinity. |
| Real Max Drawdown | max(running peak - cumulative closed net), initial=0 | F 1515-1525; M 44-56 | D 500 prefixes minus | Currency, not percent | No client recalculation; possible -0 display. Not largest single loss. |
| Analytics Max DD | max(peak-to-trough DD, static DD) on domain equity | A 393-419,509 | Not the top Real DD card | Currency | Same main-curve points, different population from Real Summary. |
| Counts / W / L | COUNT with closed/sign predicates as applicable | A 338-355,410; F 1495 | D banner, Yesterday, Backtest, pies | Trades | Total can include open rows without dates. Open count ignores currency/date/version. Pie totals omit breakevens. |
| Average R | AVG(stored r_multiple), closed; ignores nulls; empty=0 | A 367,516 | D 994, two decimals | R | No frontend PnL/risk division. Missing and true zero are indistinguishable. |
| Today / Yesterday PnL | SUM(n) over respective closed day | A 447-458,586-635 | D 538,593 | Currency | Formatting only. Today intersects range; Yesterday does not. |
| Month / Quarter / Year | SUM(n) after Gregorian period start within closed_scope | A 441-462 | D 560-572,885-934 | Currency | Repeated display, not repeated calculation; can be partial periods. |
| Month change | 100*(month-prev)/ABS(prev); prev=0 => +100/-100/0 | A 463,546 | D 890,896 | Percent | No repeated scaling; bar uses min(abs(change),100), hiding sign/magnitude. |
| Quarter / Year goal bars | min(abs(period/(month or 1)*100),100) | No target KPI | D 909,928 | Display percent | Client-derived ratios, not actual goal completion; zero month substitutes 1 currency unit. |
| Prop profit / target / DD | Engine closed/floating separation; targets use closed; DD uses configured basis | P _evaluate_stage_with_trades | D 657-710 | Currency; progress percent | Returned values rendered. Local loss/limit*100 ratios only set warning styling; no second monetary DD. |
| Finance Total Balance | SUM stored financial balances by currency | F get_finance_summary | D 764-769 | Currency | Client selects map; includes archived, excludes broker balances. |
| Account Breakdown | Stored balance per nonarchived account | F get_accounts | D 791-807 | Row currency | No calculation; only newest six, not reconcilable to total by summing visible rows. |
| Finance Real PnL / Expenses / Net | broker+funded SUM(n); SUM(FEE,PURCHASE); subtract expenses | F _compute_real_pnl, _expenses_total, get_net_profit | D 813-839 | Currency | Display only, expense gets minus prefix. Coverage/closed/transaction semantics differ from Real Summary and Cash Flow. |
| Personal Assets | Group financial balances + broker current balances by currency | F get_spendable_assets | FinancialAssetBalances | USDT / IRR separately | Displays provided totals; excludes prop capital/legacy unreceived field. No FX. |
| Cash Flow / Asset Trend | Monthly qualifying income/expense sums; cumulative daily ledger deltas | F get_cashflow_chart / get_asset_trend | D chart dataKeys | Currency | No client reaccumulation; not trading PnL or balance snapshots. |
| Recent / Open row net | pnl+commission+swap | Trade API supplies raw fields | D 1070,1111 | Currency | Duplicated formula, not double charging; raw fields added once. Open null pnl hides fees-only net. |

Analytics also returns avg_win=GP/W, avg_loss=GL/L, expectancy=(W/C)*avg_win-(L/C)*avg_loss, largest win/loss and streaks; these are not standalone Dashboard cards. Zero-net resets analytics streaks. `C:\MokTradeDesk\frontend\src\components\ui\StatCard.tsx:70-77` normalizes spark bars to 12..100% height, not KPI values. Real sparkline is last 30 populated closing days of cumulative all-history net, not 30 calendar days. Backtest sparkline is last up to 20 closed-trade cumulative-net points.

## Task 7/13 — Equity Curve

Sources: `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:204,1020-1021`; `C:\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx`; `C:\MokTradeDesk\backend\app\api\analytics.py:204-240,329-418`; `C:\MokTradeDesk\backend\app\domain\risk\equity_engine.py`.

| Field | Verified behavior |
|---|---|
| Source | GET /api/analytics/dashboard; closed_scope ordered by close_time then id. Dashboard passes prepared equity_curve directly; no saved analysis or live prices. |
| Basis | Initial balances summed once per referenced personal account and prop stage in selected closed rows. Simulation uses 10000; real/all also fall back to 10000 if sum is nonpositive. Multiple stages can contribute capital. Not current balances or deposit/withdrawal reconstruction. |
| Closed | Initial capital plus cumulative closed net; balance equals equity, no floating. SQL net is adapted to pnl with commission/swap zero before engine use, avoiding double fees. |
| Date | UTC close-time bounds; one point per trade plus initial date=null. Naive closes assigned UTC; ISO output. Selected range restarts at initial capital, not actual range-opening equity. Referenced accounts and therefore baseline can change with range. |
| Currency | Backend currency filtering, no FX; simulation only USDT. IRR supported numerically but tooltip wrongly hard-codes USDT. Fallback capital is synthetic. |
| X | Zero-based trade index, equally spaced, not time. Dates unused. Dashboard subtitle incorrectly labels point count as days, including baseline. |
| Y | Absolute initial plus cumulative net, rounded to two decimals. No explicit Y unit. Two monotone Areas draw fill and line for the same equity. |
| Tooltip | USDT suffix and trade #index; no close date or selected currency. Baseline is trade #0. Incompatible labeling for IRR. |
| Compatibility | Prepared series mapped directly without recalculation. date=null conflicts with declared date:string, masked by Dashboard any typing. Fewer than two points shows no-data; one closed trade plus baseline renders. |

Alternative trades/initialBalance input filters closed trades but adds only pnl, omitting commission/swap; it is not equivalent unless callers normalize pnl. Dashboard normally uses prepared series. Empty series falls back to empty trades and zero initial, showing no-data.

Main analytics max_dd uses the same unrounded domain points. Top Real DD uses separate all-history Real Summary. Final minus initial equity equals selected closed net, subject to rounding, not necessarily undated summary.net_pnl with open net, Finance Net Profit, live equity or current assets.

Validation scope for Tasks 4-7: local static source tracing and document checks only; no Git, application code edits, builds, live API calls or database writes. Findings documented, not fixed.

## Task 8/13 — UX / Duplication

Method: static review of rendered section order and data bindings, not a timed usability study. Classifications describe Dashboard placement/value, not authorization to remove features. Header features are assumed to stay.

Source: `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:338-1120`; data-contract details are recorded in Tasks 3-7 above.

| Section | Classification | UX / duplication finding |
|---|---|---|
| Welcome, clock, sessions and header actions | مفید | Orientation and quick access; retain all. Concrete defects are separated into Task 10. |
| Date, scope and currency controls | ضروری | Required to interpret results, but apparent global scope does not match actual request coverage. |
| Leading Real Summary KPI cards | ضروری | Net PnL, win rate, PF and drawdown are valuable at a glance. Current cards represent real-money history, not a unified selected-range summary. Keep their source distinction explicit. |
| Today status and week/month/quarter/year PnL | ضروری | Immediate performance context; the mix of named periods and the selected filter needs explicit semantics. |
| Yesterday comparison | مفید | Useful context, but a full card with repeated win rate and W/L takes substantial space before current risk. Absolute-value source bars cannot convey profit versus loss without reading the caption. |
| Active Prop stage and limits | ضروری | Actionable for prop traders: progress, drawdown limits, trading days and violations. Detailed stage administration belongs on Prop; this summary is not redundant with historical drawdown. |
| Unread Prop alerts | ضروری | Prioritize actionable violations. Some overlap with stage violations is useful, but the same incident should not look like two independent risks. |
| Finance total balance and account breakdown | متعلق به صفحه دیگر | Detailed balances/account inventory belong primarily on Finance; a compact balance summary can remain useful. Not equivalent to trading equity. |
| Finance cashflow and asset trend | متعلق به صفحه دیگر | Cash management/history, not immediate trading performance. Asset trend is not the closed-trade equity curve; do not merge their meanings. |
| Finance Net Profit | مفید | Real trading result less expenses is useful, but the repeated net-profit label competes with Real Summary and differs in definition and filter coverage. |
| Personal assets / financial asset balances | تکراری | Overlapping balance information alongside total balance and account breakdown increases scan cost. Different account subsets are not numerically interchangeable. |
| Monthly/quarterly/yearly goal bars | کمارزش | Reuses period PnL and derived ratios, not configured target completion (Task 6). Apparent precision does not answer whether the trader is on plan. |
| Selected-version Backtest performance | متعلق به صفحه دیگر | Useful for Analysis/strategy review, but independent version, USDT and all-history data interrupt a real-trading overview. Not a duplicate of Real Summary. |
| Closed-trade equity curve | ضروری | Shows performance trajectory beyond headline PnL; currently appears after Finance, goals and Backtest. Not live account equity. |
| Win/loss pie | تکراری | Repeats the win-rate/W-L concept already shown above; populations can differ, so visual duplication is not proof of equal values. |
| PnL distribution | مفید | Adds payoff-shape context rather than repeating totals; secondary to risk and open positions for a quick read. |
| Latest closed trades | مفید | Compact recent-activity check and route to Trades; not a substitute for a selected-period performance summary. |
| Open trades | ضروری | Important exposure context, but near the end of the page. This table alone does not establish live marked-to-market risk. |

Priority recommendation (documentation only): make selected scope/period/currency and their applicable KPIs unambiguous, give current risk/open exposure early visibility, then show equity and secondary analysis. Distinguish repeated concepts from genuinely different financial populations before any future consolidation.

## Task 9/13 — Trader View (5-10 sec)

**Verdict: not reliably.** A trader can spot prominent profit, win-rate, PF and drawdown numbers quickly, but cannot reliably establish that they describe the selected trading population or answer all immediate risk questions within 5-10 seconds. This is a source-based assessment, not a measured completion time or viewport screenshot result.

Sources: `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:198-269,380-438,440-751,753-1120`; Tasks 4-7 document the underlying data differences.

| Trader question | Quick-read assessment | Reason |
|---|---|---|
| What account population, period and currency am I reviewing? | Partial / ambiguous | Controls are visible, but leading Real Summary ignores date/scope; Finance and Backtest have separate contracts. A Real label does not explain every exception. |
| Am I profitable today and in the chosen range? | Partial | Today is prominent, but the leading net-profit card is not selected-range PnL; several net-profit labels use different definitions. |
| Is performance improving? | Slow / qualified | Equity is far below intervening sections; its index spacing and synthetic range baseline require interpretation. It is not a live balance history. |
| How close am I to a risk limit? | Partial | Prop limits and violations exist, but follow Real Summary, Today and Yesterday. Historical maximum drawdown is not remaining daily risk capacity. |
| What positions are open now? | Slow | Open-trade table is near the end, after Finance, goals, Backtest and charts. No claim of live prices or complete current exposure is justified by that table. |
| Is the strategy robust? | Partial | Win rate and PF are readable, but the PF sentinel mismatch and misleading largest-loss label undermine interpretation; Backtest has an independent version and scope. |
| Are these values fresh? | Unclear | Refresh has a spinner/toast but does not refresh every visible data source; no unified data-as-of timestamp accompanies the metrics. The live header clock is not a data-freshness indicator. |

Positive elements: large KPI values, explicit currency on many amounts, signed PnL, semantic profit/loss colors, risk badges, section headings and direct navigation actions support scanning. They do not resolve mixed scopes or calculation-label mismatches.

Main obstacles: (1) inconsistent filter propagation, (2) repeated labels with different definitions, (3) long section order delaying risk and open trades, (4) low-value goal bars and detailed financial/backtest content competing with immediate trading questions, and (5) correctness issues already recorded in Tasks 6-7. Responsive single-column KPI layouts can add vertical scanning; exact fold positions and accessibility/contrast outcomes were not measured.

Suggested future acceptance check: with a known dataset and selected range/scope/currency, ask a trader to identify applicable net PnL, today PnL, drawdown/remaining prop limit, open positions and data freshness in 5-10 seconds. Test desktop and narrow layouts. This check was not executed and no redesign was implemented.

## Task 10/13 — Header Review

**Assumption: keep Welcome, Date/Time, Market Sessions, Theme, Refresh, PDF and Controls.** Findings below are functional defects or concrete interpretation mismatches, not aesthetic objections or proposals to remove header features. Static verification only; no live API calls, exports or browser interactions were performed.

| Feature | Review result | Evidence / impact |
|---|---|---|
| Welcome | No concrete bug found in reviewed greeting logic | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:30-35,280-284,303-307,344`: greeting follows browser-local hour; timer is cleaned up. Retain. |
| Date/Time | Time-zone interpretation mismatch | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:303-306,347-350` uses browser-local date/time without a zone label, while adjacent sessions use Asia/Tehran. On a non-Tehran device these represent different local clocks without clearly identifying the header clock's zone. Local time itself is not inherently incorrect. |
| Market Sessions | Open/overlap flags ignore weekends; fixed schedules do not track session-city DST | `C:\MokTradeDesk\frontend\src\components\MarketSessionWidget.tsx:62-105`: calculations use only Tehran seconds of day, repeat every day, and hard-code London/New York overlap to 16:00-19:00. On Saturday within a listed interval a forex session is still marked open. These are fixed time windows, not dependable actual forex-open status; city DST changes are not represented. No assertion that they cover exchange holidays or all instruments. |
| Theme | No concrete header toggle bug found | `C:\MokTradeDesk\frontend\src\App.tsx:73-81,192-198` toggles state; `C:\MokTradeDesk\frontend\src\utils\theme.ts:12-29` applies the HTML dark class and persists the choice. Keep. This is not a rendered contrast/accessibility certification. |
| Refresh | Incomplete refresh despite Dashboard-wide success message | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:191-269,366-369`: button invokes loadDashboard only; versions load on mount and selected-version Backtest loads in a separate effect. An unchanged selected version can retain stale metrics after a successful header refresh. Market widget also has its own lifecycle. |
| Refresh / filter loading | Stale-response race and all-or-nothing update | Same loadDashboard block has no cancellation or latest-request guard. Rapid filter changes can allow an older request to overwrite newer data. Promise.all commits none of its results if any dependency fails; existing cards remain while the error toast appears. A successful subset must not be interpreted as a refreshed screen. |
| PDF | Export does not represent active filters | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:319-332`; `C:\MokTradeDesk\frontend\src\api\client.ts:181-182`: request sends no date/scope/currency/version. `C:\MokTradeDesk\backend\app\api\export.py:439-448` explicitly requests real/USDT with no selected version. Selecting IRR, Backtest or a custom period does not carry into the report. Keep PDF, but this is not a faithful export of the filtered view. No claim that PDF generation was runtime-tested. |
| Controls — New trade | Action promises a form that it does not open | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:309-312,354-355` navigates to Trades, dispatches mok-new-trade and announces the form is open. Source search finds only event dispatchers (also `C:\MokTradeDesk\frontend\src\App.tsx:141,167`), no listener. The event does not trigger a create form; the success-style informational message is misleading. |
| Controls — New financial account | Label/action mismatch | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:357-361`: transaction and new-account buttons both only navigate to Finance; no account-creation intent is passed. The new-account label promises more than the handler performs. |
| Controls — Search | No concrete wiring bug found | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:315-317,363-364` dispatches Ctrl+K; `C:\MokTradeDesk\frontend\src\App.tsx:117-147` handles it and toggles the command palette. Retain. |
| Controls — filters | Apparent global scope exceeds actual coverage | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:198-269,380-435`: main date/scope/currency controls are not propagated uniformly. Task 4 contains the detailed coverage audit. This is a functional interpretation issue, not a reason to remove controls. |

Additional concrete session-widget rendering defect: `C:\MokTradeDesk\frontend\src\components\MarketSessionWidget.tsx:513-520` assigns labelColor values such as `var(--profit)` and wraps them again as `var(${labelColor})`, yielding invalid `var(var(--profit))`. Expanded interval A/B/C label colors therefore do not apply as intended. Retain the widget and its controls; record the defect only.

Validation scope for Tasks 8-10: local source inspection and document integrity checks only. No Git, application code changes, builds, database writes or runtime UI tests. Classification and scan-time judgments are explicitly separated from source-demonstrable defects.

## Task 11/13 — Recommended Architecture

These are proposed changes, not implemented behavior. Preserve the existing React/Recharts components, API client and backend domain services; no new framework is needed. Separate three contracts: selected-period realized performance, current open-position/Prop risk, and financial balances/cash movements. Each visible block should declare its population, currency, period, valuation basis and data timestamp. A refetch is not evidence that a filter applies.

### A. Keep as-is

- Keep Welcome, Date/Time, Market Sessions, Theme, Refresh, PDF and quick controls as features. “Keep” does not exempt the functional defects in Task 12 from repair.
- Preserve explicit real/backtest/forward separation, currency filtering without implicit FX, persisted filter choices, Persian date entry and RTL presentation.
- Reuse StatCard, Card/CardHeader, badges, progress bars, empty/loading/error components and the existing chart library.
- Preserve signed net accounting: pnl + commission + swap, applied once. Preserve win-rate units of 0–100 and the distinction between closed-trade performance and open risk.

### B. Remove

Remove from the Dashboard presentation, not from stored data or the product: synthetic monthly/quarterly/yearly “goal completion” bars, redundant W/L visualizations once one authoritative view exists, and misleading labels such as points-as-days or cumulative loss-as-largest-loss. Do not delete legitimate KPI calculations, open trades, alerts, header functions or historical records. Do not remove the actual configured Prop target progress bar.

### C. Merge

- Combine Today and a compact Yesterday comparison in one explicitly fixed-period block; do not silently apply a selected historical range to “today.”
- Consolidate selected-period KPIs and their supporting mini charts under one response/population. Replace, rather than silently reinterpret, the leading all-history Real Summary cards; retain any all-history reference only with an explicit label.
- Present related Prop status and unread alerts together, preserving distinct incidents and read state. Deduplicate by incident identity, not merely similar text.
- Consolidate overlapping balance summaries in Finance. Never sum or merge unlike balances, trading equity and cumulative cash movements into a single “asset” metric.

### D. Move to Finance

Move detailed total-balance breakdowns, account inventory, cashflow, personal assets, expense-adjusted Net Profit and ledger asset trend to Finance. A compact, explicitly current balance link may remain secondary on Dashboard. Preserve currencies separately and show which account classes/archived accounts are included. Moving charts does not fix their incorrect units or labels.

### E. Move to Analysis

Move selected-version Backtest KPIs/sparkline, full payoff distribution, detailed win/loss analysis and extended strategy statistics to Analysis. Preserve independent version selection and simulation currency rules. Dashboard can retain a compact distribution as an optional secondary chart, not a competing primary section. No saved Analysis result should silently replace live aggregation of the selected trade dataset.

### F. Move to Prop

Move full stage histories, account/rule administration and detailed compliance review to Prop. Retain a compact Dashboard summary of active-stage target progress, daily/total limits and actionable violations. Current risk must remain independent of historical date filters, explicitly labeled and linked to its stage/currency.

### G. Final Dashboard order

1. Existing header features and actions, with truthful refresh/export behavior.
2. Date/scope/currency controls and an explicit data-context/freshness line; no claim that an account selector currently exists.
3. Urgent current-risk alerts, when present, followed by a compact active-stage risk strip.
4. Selected-period realized KPI row.
5. Compact Today/Yesterday context, with fixed day/time-zone labels.
6. Closed-trade equity/performance curve and its declared baseline.
7. Open-position table, clearly current and not historical-range filtered; keep a visible open-count/risk shortcut near the top.
8. Recent closed trades consistent with the selected historical filters.
9. Optional secondary distribution and compact links to Finance, Analysis and Prop.

Exact responsive layout and fold placement require browser validation; this order is a recommendation, not a tested mockup.

### H. Final KPIs

| KPI | Proposed contract |
|---|---|
| Realized Net PnL | Sum signed net of closed trades in selected scope/date/currency; costs applied once. |
| Win rate | 100 × wins / all closed trades, including breakevens in the denominator; show sample size. |
| Profit factor | Positive net sum / absolute negative net sum on the same closed population; explicit no-loss/empty state, not an ambiguous numeric sentinel. |
| Maximum drawdown | Clearly named monetary/percentage basis on the declared selected-performance curve; not largest single loss or remaining daily allowance. |
| Closed trade count | Same population as the four metrics above; expose W/L/breakeven detail compactly. |
| Today PnL / Yesterday comparison | Separate fixed Tehran-day closed performance for the selected scope/currency, independent of historical range. |
| Current risk context | Open count and applicable Prop limit consumption/remaining allowance, separately labeled; use the configured equity/balance rule. Do not invent aggregate live exposure from stored PnL. |

Expectancy and average R are secondary Analysis metrics. Add live floating PnL or aggregate exposure only after defining a trustworthy valuation source and freshness contract; they are not currently established by the audited path.

### I. Final Charts

Primary: one closed-trade performance curve with explicit baseline, currency and trade-index or true-time axis. Prefer a clearly labeled cumulative realized-PnL curve if actual range-opening account equity cannot be reconstructed. Do not call synthetic capital plus PnL a live balance. Secondary: optional net-PnL distribution and small KPI sparklines sharing the same population. Remove the redundant W/L pie from the default overview or include breakevens and an explicit denominator. Finance retains currency-separated cashflow/ledger trend; Analysis retains Backtest/detail charts.

### J. Final Tables

Two distinct tables: (1) current open positions with relevant scope/currency, total count, pagination/view-all and stored-versus-live valuation disclosure; (2) recent closed trades respecting selected period/scope/currency with close time, symbol, direction, strategy and signed net result. Keep current exposure independent of historical close-date filters. Move full account inventories and detailed stage lists to their owning pages. Display loading, partial failure and stale-data states per block rather than presenting an old table as current.

## Task 12/13 — Bugs with Severity

Severity is audit prioritization, not observed financial loss: **Critical** = demonstrated catastrophic loss/security/data-integrity failure; **High** = materially misleading performance, risk or report context; **Medium** = incorrect metric/label or functional workflow; **Low** = presentation/secondary contract issue. No Critical defect was established by this static audit. Rows describe source-confirmed behavior; impacts requiring specific data or timing are conditional. Fixes are recommendations only.

Location aliases (absolute paths):
- D: `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx`
- A: `C:\MokTradeDesk\backend\app\api\analytics.py`
- F: `C:\MokTradeDesk\backend\app\api\finance.py`
- E: `C:\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx`
- S: `C:\MokTradeDesk\frontend\src\components\MarketSessionWidget.tsx`
- X: `C:\MokTradeDesk\backend\app\api\export.py`
- M: `C:\MokTradeDesk\backend\app\services\metrics.py`

### Critical

None demonstrated. This does not certify the application free of Critical defects; no runtime security, execution or financial-loss investigation was performed.

### High

| ID | Severity | Location | Problem | Impact | Recommended fix |
|---|---|---|---|---|---|
| H01 | High | A:329-351; D:263,973 | Analytics Net PnL sums scoped open and closed rows when dates are absent; Backtest uses this undated result. | Open stored net can contaminate realized PnL and disagree with closed-only PF/curve. | Aggregate realized net from closed_scope; expose open net separately; test open trades with nonzero PnL/costs. |
| H02 | High | F:_compute_real_pnl/get_net_profit, 1325-1386 | Finance Net Profit lacks an explicit closed-trade predicate. | Open stored PnL can be reported as realized profit after expenses. | Require close_time for realized trading input and specify expense coverage; test reconciliation against the same closed population. |
| H03 | High | D:198-269,380-438; Task 4 coverage table | Main controls appear global while Real Summary, tables, Finance and Backtest use different filters. | User may attribute all-history/other-scope results to the selected period. | Define block-level filter contracts; align primary KPIs/tables and label intentional current/all-history exceptions. |
| H04 | High | D:198-243 | Main loader has no latest-response guard/cancellation. | Slow old requests can overwrite results after newer filter selections. | Guard response commits by request identity or cancellation; test reversed response order. |
| H05 | High | D:319-332; X:439-448 | PDF receives no active filter context and forces real/USDT. | Export can materially differ from the visible IRR/Backtest/date-selected screen. | Pass/validate supported filters and print them in the report; explicitly distinguish any fixed global report. |
| H06 | High | A:47-124,441-462; D:68-97 | Jalali/local UI periods, UTC bounds and Gregorian backend periods are inconsistent; named totals intersect the selected range. | “This month/year/today” may represent a different or partial interval, distorting comparisons. | Define calendar/time zone once, use explicit interval metadata, and calculate fixed-period comparisons independently where intended. |
| H07 | High | D:1090-1127; Task 5 | Open row net is presented as instantaneous PnL although it is stored pnl/costs, not a verified live valuation. | Users may mistake stale stored results for current exposure/risk. | Label stored values and timestamps; use a validated price source before claiming live PnL. Preserve configured Prop floating-risk semantics. |

### Medium

| ID | Severity | Location | Problem | Impact | Recommended fix |
|---|---|---|---|---|---|
| M01 | Medium | F:1512; D:484,987; M:profit_factor_from_sums | Real no-loss PF sentinel is 100 while UI infinity threshold is 999; threshold also mislabels finite PF >=999. | Incorrect ratio interpretation. | Use one explicit finite/no-loss/empty contract rather than numeric threshold inference. |
| M02 | Medium | D:499-507 | “Largest loss” uses cumulative gross_loss; maximum drawdown label is ambiguous. | Single-trade loss and peak-to-trough loss are confused. | Bind largest closed loss to its own metric and label DD precisely. |
| M03 | Medium | D:878-934 | Goal bars use period ratios/absolute change, including a one-unit fallback denominator, not configured targets. | False apparent target completion, even for losses. | Remove pseudo-goals or introduce real targets with signed progress and explicit denominators. |
| M04 | Medium | E; D:1020 | Equity tooltip hard-codes USDT and point count is labeled days, including baseline. | Wrong IRR unit and duration interpretation. | Pass currency and label trade steps correctly or render actual timestamps. |
| M05 | Medium | A:204-240,393-418; E | Filtered equity restarts from account/synthetic capital without actual range-opening balance disclosure. | Can be mistaken for actual account equity or comparable range-opening wealth. | Disclose baseline or show cumulative realized PnL; reconstruct true opening equity only from a defined ledger contract. |
| M06 | Medium | D:203-235,290-298 | One Promise.all failure prevents all data commits; prior data remains on refresh failure. | Partial endpoint outage hides valid updates and leaves stale values under changed filters. | Isolate section loads/errors and display retained-data context/freshness. |
| M07 | Medium | D:191-269,366-369 | Header Refresh does not reload versions or unchanged-version Backtest metrics. | Success toast overstates refresh coverage. | Refresh all intended sources or explicitly state refresh scope and per-block timestamps. |
| M08 | Medium | D:309-312; `C:\MokTradeDesk\frontend\src\App.tsx`:141,167 | New-trade event has dispatchers but no listener. | Navigation occurs without the promised create-form event behavior. | Carry an explicit create intent to Trades and consume it after mounting; announce only actual form opening. |
| M09 | Medium | D:357-361 | “New financial account” only navigates to Finance. | Shortcut does not convey its advertised creation intent. | Add a supported creation intent or label it as navigation. |
| M10 | Medium | S:62-105 | Session open/overlap calculations repeat daily and use fixed Tehran windows without weekends/city DST. | Forex market can be shown open on Saturday or with seasonally incorrect timing. | Use session-zone calendar rules or label as fixed reference windows rather than actual market status. |
| M11 | Medium | A:47-64 | Date upper bound ends at 23:59:59; invalid bounds silently become absent. | Fractional-second closes are omitted; invalid input can silently broaden reports. | Validate bounds/order and use an exclusive next-midnight upper bound in the agreed zone. |
| M12 | Medium | A:Today/period predicates, 441-462 | Current-period queries have no explicit upper-now bound. | Future-dated closes can contribute to current results if present. | Reject invalid future close data or cap current-period calculations at the defined as-of instant. |
| M13 | Medium | D:210-211, banner/open table; A:open count | Open count ignores currency/version; table ignores main scope and defaults to a limited page. | Count/table disagreement and incomplete apparent position inventory. | Align current scope/currency, show total vs displayed rows and pagination; intentionally exclude historical close-date filtering. |
| M14 | Medium | F:get_asset_trend; D:849-865 | Cumulative ledger deltas are presented as asset trend; both currencies share a magnitude axis. | Cash movement can be mistaken for wealth, with IRR visually overwhelming USDT. | Name the ledger basis and separate currency axes/panels; use reconciled snapshots for actual assets. |

### Low

| ID | Severity | Location | Problem | Impact | Recommended fix |
|---|---|---|---|---|---|
| L01 | Low | D:777-788; F:get_cashflow_chart | Last six populated months labeled “last six months.” | Gaps can make old data appear recent. | Generate the actual six-month interval with zero-filled months or label populated months. |
| L02 | Low | D:1024-1029; win/loss chart | Pie omits breakevens while subtitle describes W+L as closed trades. | Denominator differs from headline win rate. | Include breakevens or explicitly label decisive trades and denominator. |
| L03 | Low | E:series typing and trades fallback | Initial date=null conflicts with string type; raw-trades fallback adds pnl without costs. | Latent reuse/type-contract risk; prepared Dashboard series is not double-charged. | Type nullable initial date and require normalized net or shared net calculation for fallback. |
| L04 | Low | S:513-520 | Nested var(var(--profit)) style expression. | Expanded interval label colors fail. | Use the already-formed CSS variable expression directly. |
| L05 | Low | D:303-306; S:69-78 | Header clock is browser-local while sessions are Tehran-based, without explicit header zone. | Non-Tehran users may compare unlike local times. | Label both zones or use one declared display zone. |
| L06 | Low | D:1111 and open-row formatting | Null pnl hides a fees-only net value. | Stored costs can disappear behind a dash. | Distinguish unavailable valuation from known commission/swap; do not invent a live total. |
| L07 | Low | D:500; average-R display/API contract | Negative zero DD and missing-R-as-zero presentation. | Minor ambiguity in empty/zero states. | Normalize signed zero and represent unavailable R separately from actual zero. |

Not defects by themselves: open trades being visible; floating PnL in equity-basis Prop risk; independent current-risk periods; synthetic performance curves when clearly disclosed; different account totals with explicit coverage; shared UI components; repeated alerts at useful entry points. Long layout and proposed moves are architecture recommendations, not automatically calculation bugs. No duplicate fee application or extra win-rate ×100 was found on the audited prepared Dashboard paths.

## Task 13/13 — Final Report

### 1. Executive Summary

The Dashboard combines useful trading, Prop and financial information, but is not yet a reliably coherent 5–10-second trading overview. The principal risks are inconsistent data populations/filter coverage, realized PnL that can include open stored values on some paths, asynchronous stale-state behavior, and misleading metric/chart labels. It is not established as a live exposure or live equity monitor. Correct semantics and freshness before undertaking visual consolidation.

Tasks 1–10 supply the inventory and detailed traces; Task 11 proposes architecture; Task 12 is the severity-sorted issue register. No Critical issue was demonstrated. Findings are static-source observations, with data/timing-dependent impacts explicitly conditional. Recommendations have not been implemented or runtime-validated.

Historical references in the preserved early sections use an older workspace root. For this final consolidation the inspected root is `C:\MokTradeDesk`; old sections were not rewritten. Relative file identities, rather than historical drive letters or potentially shifting line numbers, should guide follow-up navigation.

### 2. Dashboard Structure

Current source order: header → main filters → Real Summary KPIs → Today/period context → Yesterday → active Prop stages/alerts → six Finance subcards → derived goal bars → selected-version Backtest → equity/W-L/distribution charts → recent closed/open tables. Conditional empty/error/loading states and global App controls supplement this body. The broad financial and analytical content delays access to current positions and the primary performance curve. See Tasks 2 and 8 for the full inventory and usefulness classification.

### 3. Component Map

| Responsibility | Current component/source |
|---|---|
| Page orchestration, loaders, filters, inline financial charts/tables, mini charts | `C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx` |
| App shell, Theme and command navigation | `C:\MokTradeDesk\frontend\src\App.tsx`; `C:\MokTradeDesk\frontend\src\utils\theme.ts` |
| Sessions, intervals and news | `C:\MokTradeDesk\frontend\src\components\MarketSessionWidget.tsx` |
| KPI/card primitives | `C:\MokTradeDesk\frontend\src\components\ui\StatCard.tsx`; `C:\MokTradeDesk\frontend\src\components\ui\Card.tsx`; `C:\MokTradeDesk\frontend\src\components\ui\ProgressBar.tsx`; `C:\MokTradeDesk\frontend\src\components\ui\Badge.tsx` |
| Trading charts | `C:\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx`; `C:\MokTradeDesk\frontend\src\components\charts\WinLossPieChart.tsx`; `C:\MokTradeDesk\frontend\src\components\charts\PnLDistributionChart.tsx` |
| Financial balances and date controls | `C:\MokTradeDesk\frontend\src\components\FinancialAssetBalances.tsx`; `C:\MokTradeDesk\frontend\src\components\PersianDateInput.tsx` |
| Loading, errors and notifications | `C:\MokTradeDesk\frontend\src\components\Skeleton.tsx`; `C:\MokTradeDesk\frontend\src\components\ErrorBoundary.tsx`; `C:\MokTradeDesk\frontend\src\components\ToastProvider.tsx` |

The proposal is to separate responsibilities using these existing patterns, not to replace the UI framework or introduce a second financial calculation layer in components.

### 4. API / Data Flow

`C:\MokTradeDesk\frontend\src\api\client.ts` wraps requests. The main loader batches analytics/dashboard, analytics/yesterday, finance/real-summary, finance summary/cashflow/accounts/spendable-assets/net-profit/asset-trend, closed/open trades and unread Prop alerts. Strategy versions and version-specific Backtest analytics load separately. Market intervals/news have a widget lifecycle; PDF uses its own export endpoint.

Backend ownership: `C:\MokTradeDesk\backend\app\api\analytics.py` handles filtered trade aggregates and chart inputs; `C:\MokTradeDesk\backend\app\api\finance.py` handles distinct finance/Real Summary populations; `C:\MokTradeDesk\backend\app\services\metrics.py` centralizes net-related helpers; `C:\MokTradeDesk\backend\app\domain\risk\equity_engine.py` builds closed equity; `C:\MokTradeDesk\backend\app\services\prop_rule_engine.py` evaluates configured stage rules; `C:\MokTradeDesk\backend\app\api\export.py` constructs the PDF. Main chart points come from current backend trade aggregation, not saved Analysis results or live price sampling. Tasks 3a–3c retain endpoint/query details.

### 5. Filter Analysis

Main controls are date, scope and currency; no account selector exists. Main charts respect these controls, but the leading Real Summary is fixed all-history real-money coverage. Yesterday uses its own fixed day. Current Prop stages are currency-associated but not historical-range scoped. Tables apply currency but not main date/scope. Finance coverage is mixed, and Backtest uses independent version/backtest/USDT. Currency selection is filtering, not conversion. Date/calendar/zone inconsistencies and request races compound this mismatch. Task 4 is the authoritative per-section matrix; H03, H04, H06 and M11–M13 describe fixes.

### 6. KPI Analysis

Net means signed pnl + commission + swap. Win rate is already 0–100, with breakevens included in closed-count denominator. The four visible win-rate displays do not multiply it again. Main concerns: undated Analytics/Backtest and Finance realized-net exceptions, inconsistent PF sentinels, total loss mislabeled largest loss, ambiguous DD naming and ratios mislabeled goal completion. Average R is stored R aggregation, not a fresh frontend risk calculation. Different balance/profit definitions must not be reconciled by label alone. Task 6 provides formulas, units and ownership.

### 7. Chart Analysis

Closed equity is ordered by close time/id and passed through as prepared points; net costs are not charged twice. It starts with an initial point, uses equally spaced trade indices, and can restart from synthetic/account capital for filtered ranges. It is neither a cash-adjusted balance history nor live equity. Currency/day labels need repair. W/L excludes breakevens; distribution is net-result frequency; financial cashflow and asset trend represent different ledger concepts. The last-six-populated-month and shared-currency-axis caveats remain even if charts move to Finance. Tasks 3b and 7 provide detailed traces.

### 8. Closed Trade Compliance

Passes on reviewed realized paths: Real Summary, Today, Yesterday, period aggregates, prepared equity, W/L, distribution, closed average R/streaks and recent closed trades. Exceptions: undated analytics.summary.net_pnl and Finance Net Profit can include nonclosed stored PnL. Backtest's undated Net PnL inherits the first exception. Open tables are intentionally separate; Prop equity-basis drawdown may correctly use floating net while profit targets use closed PnL. Do not “fix” realized compliance by deleting legitimate open-risk monitoring. Test fees-only/open trades and zero/breakeven results before changing shared metric helpers.

### 9. UX / Information Architecture

Large values, semantic colors, Persian labels, badges and direct links support scanning. Reliable interpretation is weakened by competing contexts, repeated labels and delayed risk/position visibility. The 5–10-second verdict is qualitative, not a measured usability result. Current risk should be visibly separate from selected historical performance, with explicit as-of/valuation status. Preserve header features; repair their functional issues without treating aesthetics as bugs. See Tasks 8–10.

### 10. Duplications

True repeated information includes period PnL reused in goal bars and repeated W/L concepts. Financial balance cards overlap but use different account coverage. Backtest and Real Summary are not duplicate datasets; neither are ledger asset trend and closed equity. Prop alerts can intentionally repeat actionable information at an entry point. Consolidate display only after establishing population/definition equivalence; do not merge distinct financial meanings merely because their labels resemble one another.

### 11. Bugs / Issues with Severity

Task 12 records **7 High, 14 Medium and 7 Low** issues, with location, problem, conditional impact and proposed fix for each; no Critical finding was established. High priority: realized-net compliance, filter/report consistency, latest-response protection, coherent period semantics and truthful stored-versus-live labeling. Medium priority: KPI/curve correctness, independent refresh/error handling, action wiring, session status and count/ledger interpretation. Low priority: secondary captions, reusable chart contracts and minor presentation states. Severity does not imply any exploit, executed trade or observed financial loss.

### 12. Recommended Dashboard Structure

Use Task 11's order: retained header → explicit filters/context → urgent current-risk summary → coherent realized KPIs → compact daily comparison → primary closed-performance curve → current positions → recent filtered closed trades → optional secondary visualization/navigation. Move financial detail to Finance, strategy detail to Analysis and stage administration to Prop, while retaining concise actionable summaries. Account selection is a potential future extension, not a capability this audit claims to exist.

### 13. Recommended Changes

1. **Data contract first:** define realized closure, net sign conventions, PF empty/no-loss handling, breakeven denominator, period calendar/zone and curve baseline; keep risk valuation separate.
2. **Trust/freshness:** align main KPI/table filters, protect against stale responses, expose per-block loading/error/as-of states and make Refresh/PDF honor declared coverage.
3. **Correctness:** repair misleading labels/goals, date boundaries, currency presentation, session status and shortcut actions using the existing stack.
4. **Information architecture:** perform the moves/merges only after data definitions are stable; retain specialist functionality and historical data.
5. **Future verification:** test open/closed/fees-only/breakeven trades, empty/no-loss/large finite PF, IRR vs USDT, midnight/fractional and Jalali boundaries, selected-range capital, reversed request completion, partial failure, export parity, refresh coverage, weekend/DST sessions and shortcut navigation. Then perform desktop/mobile 5–10-second usability checks. These tests were not executed as part of this documentation-only task.

### 14. Things that should NOT change

- Keep Welcome, Date/Time, Market Sessions, Theme, Refresh, PDF and Controls; fix real defects rather than remove them.
- Preserve real/backtest/forward separation and explicit version context; never mix currencies without an intentional conversion contract.
- Preserve signed costs once, closed-only realized curves and 0–100 win-rate formatting; no blanket extra subtraction or percentage scaling.
- Preserve floating-aware Prop risk where required by its configured equity basis, alongside closed-profit target rules.
- Preserve open-position visibility, actionable alerts, accessible empty/error/loading feedback, RTL/Persian support and specialist-page functionality.
- Do not equate financial balances, realized trading performance, ledger flows and live equity; do not claim stored PnL is a live feed.
- Do not rewrite historical audit evidence to imply that recommendations were implemented or that a browser/API/database test occurred.

**Final status:** Dashboard audit documentation consolidated through Task 13. Only `C:\MokTradeDesk\DASHBOARD_AUDIT.md` was changed for Tasks 11–13. No Git, application source changes, builds, database writes or live calls were performed. Validation is limited to source review and document integrity/completeness; all recommended fixes remain pending implementation and runtime verification.
