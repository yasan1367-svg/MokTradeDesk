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