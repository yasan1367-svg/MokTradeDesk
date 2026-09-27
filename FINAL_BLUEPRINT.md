# 🧭 MokTradeDesk — بلوپرینت نهایی

> **نسخه:** ۱.۰
> **تاریخ:** ۱۴۰۵/۰۷/۰۵ (2026-09-27)
> **وضعیت:** ✅ کامل (فاز ۱ تا ۲۵)
> **آخرین کامیت:** `e33a658` — *Phase 25: Soft delete trades + filters*
> **زبان رابط کاربری:** فارسی (RTL) · **زبان کد و مستندات فنی:** انگلیسی/فارسی

---

## فهرست مطالب

| # | بخش |
|---|---|
| ۱ | [خلاصه اجرایی](#۱-خلاصه-اجرایی) |
| ۲ | [معماری کلی](#۲-معماری-کلی) |
| ۳ | [ساختار پروژه](#۳-ساختار-پروژه) |
| ۴ | [بخش‌های اصلی (۱۴ بخش)](#۴-بخشهای-اصلی) |
| ۵ | [مدل‌های دیتابیس](#۵-مدلهای-دیتابیس) |
| ۶ | [API Endpoints](#۶-api-endpoints) |
| ۷ | [فازهای انجام‌شده (۱-۲۵)](#۷-فازهای-انجامشده) |
| ۸ | [تست‌ها](#۸-تستها) |
| ۹ | [قابلیت‌های کلیدی](#۹-قابلیتهای-کلیدی) |
| ۱۰ | [امنیت](#۱۰-امنیت) |
| ۱۱ | [پرفرمنس](#۱۱-پرفرمنس) |
| ۱۲ | [راه‌اندازی](#۱۲-راهاندازی) |
| ۱۳ | [فازهای باقی‌مانده](#۱۳-فازهای-باقیمانده-اختیاری) |
| ۱۴ | [پیشنهادات آینده](#۱۴-پیشنهادات-برای-آینده) |
| ۱۵ | [پیوست‌ها](#۱۵-پیوستها) |

---

## ۱. خلاصه اجرایی

### معرفی پروژه

**MokTradeDesk** یک نرم‌افزار **دسکتاپ/وب لوکال (Local-First)** برای مدیریت کامل چرخهٔ معاملاتی یک تریدر حرفه‌ای است: از ثبت و تحلیل بک‌تست/فوروارد استراتژی‌ها، مدیریت چالش‌های پراپ (Prop Firm)، تا حسابداری شخصی و گزارش‌های مالی.

شعار پروژه: **Analyze • Improve • Grow**

### هدف

| هدف | توضیح |
|---|---|
| **تحلیل کمّی استراتژی** | تحلیل ۶گانه در دامنه‌های مستقل: نسخه (Backtest/Forward)، مرحلهٔ پراپ، حساب بروکر |
| **مدیریت پراپ** | موتور قوانین پراپ (Daily DD، Total DD، Profit Target، Min Days، Payout) |
| **حسابداری یکپارچه** | پل بین معاملات ↔ حسابداری (Transaction) + ۹ گزارش مالی |
| **ژورنالینگ** | ثبت مرور معاملات، امتیاز، درس‌ها + اسکرین‌شات |
| **حریم خصوصی** | همه‌چیز روی سیستم کاربر (SQLite) — بدون سرور ابری |

### وضعیت فعلی

| شاخص | مقدار |
|---|---|
| فازهای تکمیل‌شده | **۲۵ فاز** (+ ۸ Sprint جانبی) |
| مسیرهای API (unique paths) | **۱۰۸** |
| عملیات API (operations) | **۱۳۷** |
| صفحات Frontend | **۱۳ صفحه** |
| کامپوننت‌ها | **۳۱ کامپوننت** (۱۴ ui/charts + ۱۷ اختصاصی) |
| مدل‌های دیتابیس | **۲۱ مدل** در ۵ فایل |
| Migrationها | **۸** |
| تست‌های Backend (pytest) | **۹۰ پاس** |
| تست‌های Frontend (vitest) | **۹ پاس** |
| خطوط کد Backend (`app/`) | ~**۹٬۱۴۸** خط |
| خطوط کد Frontend (`src/`) | ~**۱۳٬۰۰۰** خط |
| گزارش‌های مستند | **۳۲ فایل** `PHASE*` + ۲۰ سند دیگر |

### نمودار وضعیت

```
فاز ۱  ████████████  Backend Models + API            ✅
فاز ۲  ████████████  Trade Contract                  ✅
فاز ۳  ████████████  Trades API + Pagination         ✅
فاز ۴  ████████████  Trades Frontend                 ✅
فاز ۵  ████████████  Import Pipeline (Soft4X/MT4)    ✅
فاز ۶  ████████████  Prop Rule Engine                ✅
فاز ۷  ████████████  Analysis Engine + AnalysisRun   ✅
فاز ۸  ████████████  Journal / Screenshots           ✅
فاز ۹  ████████████  ادغام Personal → Finance        ✅
فاز ۱۰ ████████████  UI معاملهٔ دستی (حساب مالی)     ✅
فاز ۱۱ ████████████  گزارش‌های مالی پیشرفته          ✅
فاز ۱۲ ████████████  Testing Suite (pytest+vitest)   ✅
فاز ۱۳ ████████████  بهبودهای UX (Toast/Dialog/…)    ✅
فاز ۱۴ ████████████  داشبورد + ریسک + Empty State    ✅
فاز ۱۵ ████████████  P0/N+1/SQL/Bundle/Rate-Limit    ✅
فاز ۱۶ ████████████  Payout History                  ✅
فاز ۱۷ ████████████  Backup خودکار                   ✅
فاز ۱۸ ████████████  Auto-Migrate Protection          ✅
فاز ۱۹ ████████████  جداسازی REAL از تحلیل            ✅
فاز ۲۰ ████████████  تحلیل ۶گانه + پول واقعی          ✅
فاز ۲۱ ████████████  Finance Bridge                   ✅
فاز ۲۲ ████████████  گزارش‌های مالی (۹ گزارش)         ✅
فاز ۲۳ ████████████  استقلال تحلیل (Backtest/Forward) ✅
فاز ۲۴ ████████████  Fork + Launcher (VBS/HTA)        ✅
فاز ۲۵ ████████████  Soft Delete + حذف گروهی          ✅
```

---

## ۲. معماری کلی

### نمای کلان

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Launcher Layer                               │
│   start.vbs  ──►  splash.hta  ──►  (uvicorn + pnpm dev)  ──► Browser│
│   stop.vbs   ──►  Kill win32 processes (uvicorn/vite/mshta)         │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
┌───────▼────────────────────────┐        ┌─────────────▼──────────────┐
│   Backend :8000 (FastAPI)      │◄──────►│  Frontend :5173 (Vite)     │
│                                │  REST  │                            │
│  api/      (13 router)         │  JSON  │  pages/   (13 صفحه)        │
│  services/ (5 سرویس)           │        │  components/ (31)          │
│  models/   (21 مدل)            │        │  api/client.ts (axios)     │
│  utils/    (6 ابزار)           │        │  utils/jalali.ts           │
│  core/     (config/db/rate)    │        │  App.tsx (lazy + Suspense) │
└───────┬────────────────────────┘        └────────────────────────────┘
        │ SQLAlchemy ORM
┌───────▼────────────────────────┐
│   SQLite : trading_desk.db     │
│   + storage/screenshots/       │
│   + backend/backups/           │
└────────────────────────────────┘
```

### Backend — Python 3.12 + FastAPI

| لایه | مسئولیت | فایل‌ها |
|---|---|---|
| **API (Router)** | endpointها، اعتبارسنجی ورودی، HTTP | `app/api/*.py` (۱۳ فایل) |
| **Service** | منطق کسب‌وکار، موتورها | `app/services/*.py` (۵ فایل) |
| **Model** | ORM، روابط، enumها | `app/models/*.py` (۵ فایل) |
| **Schema** | Pydantic models | `app/schemas/*.py` (۳ فایل) |
| **Utils** | ابزارهای مشترک | `app/utils/*.py` (۶ فایل) |
| **Core** | config, database, rate-limit | `app/core/*.py` (۳ فایل) |

**کتابخانه‌های کلیدی:** `fastapi` · `uvicorn[standard]` · `sqlalchemy` · `alembic` · `pydantic-settings` · `slowapi` · `reportlab` · `jdatetime` · `arabic-reshaper` · `python-bidi` · `beautifulsoup4` · `openpyxl`

### Frontend — React 19 + TypeScript 6 + Vite 8

| لایه | مسئولیت | فایل‌ها |
|---|---|---|
| **Pages** | ۱۳ صفحهٔ اصلی | `src/pages/*.tsx` |
| **Components** | UI عمومی + charts | `src/components/**` (۳۱) |
| **API Client** | لایهٔ ارتباط با بک‌اند (axios) | `src/api/client.ts` (۶۸۴ خط) |
| **Utils** | تاریخ شمسی | `src/utils/jalali.ts` |
| **Shell** | Sidebar + Header + Routing + Theme | `src/App.tsx` |

**کتابخانه‌های کلیدی:** `react@19` · `react-dom@19` · `recharts@3` · `axios` · `lucide-react` · `zustand` · `tailwindcss@3` · `vitest@5` + `@testing-library/react`

### Database — SQLite

| ویژگی | مقدار |
|---|---|
| فایل | `backend/trading_desk.db` |
| ORM | SQLAlchemy 2.x (declarative) |
| Migration | Alembic (۸ نسخه) |
| Auto-migrate | در `startup` (`main.py:88-119`) |
| Backup | SQLite Online Backup API (هر ۳۰ دقیقه بررسی) |

> ⚠️ **نکته مهم:** در SQLAlchemy/`Enum` روی SQLite، مقدار به‌صورت **NAME** ذخیره می‌شود (`'REAL'`, `'PROP_STAGE'`) نه value (`'real'`). این نکته در `Trade.test_type` و `AnalysisScope` حیاتی است.

### Launcher — VBScript + HTA

| فایل | زبان | نقش |
|---|---|---|
| `start.vbs` | VBScript | اجرای بی‌پنجرهٔ migration → uvicorn → pnpm dev → باز کردن مرورگر + نوشتن فایل وضعیت در `%TEMP%` |
| `splash.hta` | HTML/JS (UTF-8) | پنجرهٔ Splash با نوار پیشرفت؛ وضعیت را از فایل temp می‌خواند |
| `stop.vbs` | VBScript | پایان همهٔ پروسه‌ها با تطبیق `CommandLine` از WMI (+ kill درخت فرزندان) |
| `cleanup.ps1` | PowerShell | پاک‌سازی فایل‌های موقت/کش |

---

## ۳. ساختار پروژه

### درخت کامل (به‌جز `venv/`, `node_modules/`, `__pycache__/`, `dist/`)

```
MokTradeDesk/
│
├── start.vbs                          # لانچر اصلی (بی‌پنجره)
├── stop.vbs                           # توقف همهٔ سرویس‌ها
├── splash.hta                         # پنجرهٔ Splash + Progress bar
├── cleanup.ps1                        # پاک‌سازی
├── .env.example                       # نمونهٔ متغیرهای محیطی
├── .gitignore / .clineignore
│
├── logs/                              # backend.log, frontend.log, stop.log
│
├── backend/
│   ├── alembic.ini                    # sqlalchemy.url = sqlite:///./trading_desk.db
│   ├── requirements.txt               # ۱۵ وابستگی پایتون
│   ├── trading_desk.db                # دیتابیس SQLite
│   ├── venv/                          # virtualenv (کامیت نمی‌شود)
│   ├── backups/                       # Backupهای خودکار
│   ├── storage/screenshots/           # فایل‌های اسکرین‌شات
│   │
│   ├── app/
│   │   ├── main.py                    # (166 خط) FastAPI + CORS + RateLimit + startup
│   │   ├── core/
│   │   │   ├── config.py              # (11) Settings (pydantic-settings)
│   │   │   ├── database.py            # (20) engine + SessionLocal + Base + get_db
│   │   │   └── rate_limit.py          # (19) slowapi limiter
│   │   ├── models/
│   │   │   ├── strategy.py            # (284) Strategy, StrategyVersion, Trade, AnalysisResult, AnalysisRun, ...
│   │   │   ├── prop.py                # (138) PropFirm, PropAccount, PropStage, PropWithdrawal, PropCost, PropAlert
│   │   │   ├── finance.py             # (124) Account, Category, Transaction
│   │   │   ├── personal.py            # (37)  JournalReview, Screenshot
│   │   │   └── settings.py            # (17)  UserSettings
│   │   ├── schemas/
│   │   │   ├── analytics.py · prop.py · strategy.py
│   │   ├── api/
│   │   │   ├── strategies.py          # (475)  استراتژی/نسخه/Fork/stats
│   │   │   ├── prop.py                # (1197) پراپ: firms, accounts, stages, payouts, alerts
│   │   │   ├── trades.py              # (761)  معاملات + screenshots + batch-delete
│   │   │   ├── analytics.py           # (1156) تحلیل ۶گانه + dashboard + risk + calendar
│   │   │   ├── finance.py             # (1545) حسابداری + ۹ گزارش
│   │   │   ├── broker.py              # (123)  برداشت‌های بروکر
│   │   │   ├── export.py              # (500)  CSV/PDF
│   │   │   ├── imports.py             # (191)  Soft4X + MT4
│   │   │   ├── personal.py            # (201)  Journal + Screenshots
│   │   │   ├── backup.py              # (95)   Backup/Restore
│   │   │   ├── symbol_mappings.py     # (112)
│   │   │   └── settings.py            # (69)
│   │   ├── services/
│   │   │   ├── analysis_service.py    # (677)  موتور تحلیل + ذخیرهٔ AnalysisResult/Run
│   │   │   ├── prop_rule_engine.py    # (246)  موتور قوانین پراپ
│   │   │   ├── import_service.py      # (425)  Soft4XImporter + MT4Importer
│   │   │   ├── finance_sync_service.py# (121)  پل معامله → Transaction
│   │   │   └── backup_service.py      # (215)  Backup/Restore/cleanup
│   │   └── utils/
│   │       ├── trade_validator.py     # (101)  اعتبارسنجی Classification/Numbers/Dates
│   │       ├── trade_scope.py         # (56)   analysis_trades_filter + not_deleted_filter
│   │       ├── trade_metrics.py       # (41)   calculate_r_multiple
│   │       ├── chart_helpers.py       # (123)  رسم نمودار PDF
│   │       ├── uploads.py             # (47)   read_upload_limited
│   │       ├── enums.py               # (21)   enum_value
│   │       └── fonts/                 # فونت فارسی برای PDF
│   │
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/                  # ۸ migration (بخش ۷)
│   └── tests/                         # ۷ فایل تست (۹۰ تست)
│
└── frontend/                          # ← ادامه در پایین
```

### درخت Frontend

```
└── frontend/
    ├── package.json                   # React 19 + Vite 8 + Vitest 5
    ├── vite.config.ts                 # @vitejs/plugin-react
    ├── vitest.config.ts
    ├── tailwind.config.js / postcss.config.js
    ├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
    ├── index.html                     # CSP + فونت Vazirmatn
    ├── public/
    └── src/
        ├── main.tsx                   # (30)  ReactDOM + ToastProvider + ErrorBoundary
        ├── App.tsx                    # (219) Shell: Sidebar/Header/lazy pages/theme/shortcuts
        ├── api/client.ts              # (684) همهٔ توابع API
        ├── utils/jalali.ts            # (62)  تبدیل تاریخ شمسی
        ├── components/
        │   ├── ui/                    # Badge(19) Card(32) ConfirmDialog(71) EmptyState(37)
        │   │                          # LoadingButton(52) ProgressBar(22) StatCard(132) Tooltip(32)
        │   ├── charts/                # ComparisonBar(60) ComparisonRadar(81) EquityCurve(91)
        │   │                          # PnLDistribution(106) PropAnalytics(146) SessionBar(59)
        │   │                          # WeekdayBar(60) WinLossPie(53)
        │   ├── Sidebar.tsx            # (149) ناوبری گروه‌بندی‌شده (۵ گروه)
        │   ├── CommandPalette.tsx     # (127) Ctrl+K
        │   ├── ErrorBoundary.tsx      # (80)
        │   ├── Skeleton.tsx           # (93)  + DashboardSkeleton
        │   ├── Toast.tsx(67) / ToastProvider.tsx(100)
        │   ├── BackupManager.tsx      # (262)
        │   ├── AccountForm(202) / CategoryForm(178) / TransactionForm(261)
        │   ├── PersianDateInput.tsx   # (143)
        │   ├── AnalysisTable(61) / MetricCard(27) / GlassCard(13) / StatCard(23)
        ├── pages/                     # ۱۳ صفحه (فهرست در بخش ۴)
        ├── test/setup.ts
        └── __tests__/
            ├── components.test.tsx    # 5 تست
            └── utils.test.ts          # 4 تست
```

> **جمع‌بندی ساختار:** ۳۴ فایل پایتون در `app/`، ۵۰ فایل TS/TSX در `src/`، ۸ migration، ۷ فایل تست بک‌اند.

---

## ۴. بخش‌های اصلی

### ۴.۰ نقشهٔ صفحات (Frontend Routing)

ناوبری حالت **SPA بدون router** است — `App.tsx` با یک state (`page`) صفحه را عوض می‌کند و هر صفحه با `lazy()` جدا بارگذاری می‌شود.

| گروه Sidebar | صفحه | `page` key | فایل | خط |
|---|---|---|---|---|
| **عملیات** | داشبورد | `dashboard` | `DashboardPage.tsx` | ۱۱۸۴ |
| | تحلیل | `analysis` | `AnalysisPage.tsx` | ۴۷۸ |
| | مقایسه | `comparison` | `ComparisonPage.tsx` | ۶۷۱ |
| **تحقیق و توسعه** | استراتژی | `strategy` | `StrategyPage.tsx` | ۱۰۵۶ |
| | معاملات | `trades` | `TradesPage.tsx` | ۱۱۴۱ |
| | ژورنال | `journal` | `JournalPage.tsx` | ۴۱۳ |
| **مالی** | مالی | `finance` | `FinancePage.tsx` | ۱۳۵۵ |
| **حساب‌ها** | پراپ | `prop` | `PropPage.tsx` | ۱۶۴۸ |
| | برداشت‌ها | `payouts` | `PayoutHistoryPage.tsx` | ۴۰۸ |
| **سیستم** | تقویم | `calendar` | `CalendarPage.tsx` | ۲۰۷ |
| | مدیریت ریسک | `risk` | `RiskManagementPage.tsx` | ۱۸۰ |
| | واردات | `import` | `ImportPage.tsx` | ۶۶۹ |
| | تنظیمات | `settings` | `SettingsPage.tsx` | ۲۱۲ |

---

### ۴.۱ 📊 داشبورد — `DashboardPage.tsx` + `GET /api/analytics/dashboard`

| بخش UI | منبع داده |
|---|---|
| کارت‌های KPI (سود خالص، Win Rate، Max DD، Profit Factor) | `summary.*` |
| کارت «امروز» | `today.*` |
| Sparkline (۳۰ روز) | `sparkline[]` |
| Equity Curve | `equity_curve[]` |
| توزیع PnL | `pnl_distribution[]` |
| برد/باخت | `win_loss` |
| Session bars | `session_analysis` |
| Progress مراحل پراپ فعال | `PropRuleEngine.evaluate_stage` |
| پول قابل خرج (`spendable_money`) | از `Transaction`ها |
| کارت روز گذشته | `GET /api/analytics/yesterday` |

**فازهای مرتبط:** ۱۴.۱، ۱۴.۲، ۱۴.۳، ۱۵.۳ (SQL Aggregation)، ۲۰، ۲۱

---

### ۴.۲ 📈 تحلیل (۶ Tab) — `AnalysisPage.tsx` + `/api/analytics/analyze/*`

تحلیل **۶گانه** با دامنهٔ مستقل (`AnalysisScope`):

| Tab | دامنهٔ scope | Endpoint | فیلتر |
|---|---|---|---|
| ۱. نسخه (Backtest) | `VERSION` | `POST /analyze/version/{id}?test_type=BACKTEST` | `version_id + test_type=BACKTEST` |
| ۲. نسخه (Forward) | `VERSION` | `POST /analyze/version/{id}?test_type=FORWARD` | `version_id + test_type=FORWARD` |
| ۳. مرحلهٔ پراپ | `PROP_STAGE` | `POST /analyze/prop/{stage_id}` | `Trade.prop_stage_id` |
| ۴. حساب بروکر | `BROKER` | `POST /analyze/broker/{account_id}` | `Trade.finance_account_id` |
| ۵. مقایسه | — | `POST /compare` | چند نسخه |
| ۶. تاریخچه | — | `GET /{version_id}/history` | `AnalysisRun` |

**متریک‌های محاسبه‌شده** (`analysis_service._analyze`):

| گروه | متریک‌ها |
|---|---|
| پایه | `total_trades`, `win_rate`, `profit_factor`, `net_pnl`, `net_r`, `max_dd`, `expectancy`, `expectancy_r`, `avg_win`, `avg_loss`, `largest_win`, `largest_loss`, `max_consecutive_losses` |
| Consistency | `pnl_std_dev`, `top_trades_contribution_percent`, `avg_win_avg_loss_ratio` |
| Session | Asia / Europe / America |
| Weekday | دوشنبه…جمعه |
| Hour | ۰…۲۳ |
| Custom Intervals | بازه‌های سفارشی طلا/داوجونز |

**گاردها:** `analysis_trades_filter()` (REAL کنار گذاشته می‌شود) + `not_deleted_filter()` + `_guard_analyzable` (تحلیل کهنه).

**فازهای مرتبط:** ۷، ۱۹، ۲۰، ۲۳، ۲۵

---

### ۴.۳ ⚖️ مقایسه — `ComparisonPage.tsx` + `POST /api/analytics/compare`

- مقایسهٔ چند نسخه با نمودار **Bar** و **Radar**
- پیشنهاد بهترین نسخه + دلایل (`compareVersionsWithDetails`)
- فیلتر «حداقل تعداد معامله» (`min_trades`)
- جدول جزئیات هر نسخه

**کامپوننت‌ها:** `ComparisonBarChart.tsx`, `ComparisonRadarChart.tsx`

---

### ۴.۴ 🎯 استراتژی — `StrategyPage.tsx` + `/api/strategies/*`

- درخت **استراتژی → نسخه‌ها** (`Strategy` → `StrategyVersion`)
- وضعیت نسخه: `RESEARCH / BACKTEST / OPTIMIZATION / FORWARD / APPROVED / LIVE / REVIEW / DEPRECATED / ARCHIVED / REJECTED`
- **Fork نسخه** (فاز ۲۴): `POST /versions/{id}/fork` (`version_name`, `rules_note`, `test_type`, `status`)
- `test_type` روی نسخه (`BACKTEST/FORWARD/REAL`)
- آمار نسخه (`/{id}/stats`): net_pnl, win_rate, PF, DD, expectancy
- تعداد معاملات هر نسخه (`trades_count` — فیلترشده با `is_deleted`)

**فازهای مرتبط:** ۲، ۲۴، ۲۵

---

### ۴.۵ 📋 معاملات — `TradesPage.tsx` + `/api/trades/*`

| قابلیت | جزئیات |
|---|---|
| فیلترها | نسخه، نماد، نوع تست، منبع، بازهٔ تاریخ (شمسی)، جستجو در یادداشت |
| صفحه‌بندی | `page`/`page_size` (پیش‌فرض ۵۰، سقف ۲۰۰) |
| مرتب‌سازی | `sort_by` + `sort_order` |
| ویرایش | یادداشت + اسکرین‌شات + Classification |
| افزودن دستی | `POST /manual` با اعتبارسنجی کامل (`TradeValidator`) |
| اسکرین‌شات | آپلود/لیست/حذف + گالری + Lightbox |
| **حذف نرم** | `DELETE /{id}` → `is_deleted=True` (فاز ۲۵) |
| **حذف سخت** | `DELETE /{id}?hard=true` (فقط API) |
| **حذف گروهی** | `POST /batch-delete` + checkbox + ConfirmDialog |
| Export | CSV + PDF با همان فیلترهای صفحه |

**Trade Contract (XOR):**
```
BACKTEST → version_id الزامی
FORWARD  → version_id الزامی
REAL     → (prop_stage_id XOR finance_account_id) الزامی
```

**فازهای مرتبط:** ۲، ۳، ۴، ۱۰، ۲۵

---

### ۴.۶ 📔 ژورنال — `JournalPage.tsx` + `/api/personal/journal/*`

- ثبت مرور معامله: `setup_quality`, `execution_quality`, `rule_violations`, `notes`, `lessons`, `rating`
- اسکرین‌شات‌های مرور (`entity_type="review"`)
- مدل: `JournalReview` + `Screenshot`

**فازهای مرتبط:** ۸

---

### ۴.۷ 🏢 پراپ — `PropPage.tsx` + `/api/prop/*`

| قابلیت | Endpoint |
|---|---|
| شرکت‌های پراپ + قوانین پیش‌فرض | `GET/POST /firms`, `GET /firms/{id}/default-rules` |
| حساب‌های پراپ | `GET/POST /accounts` |
| مراحل (Stage 1/2/Funded) | `GET /stages/all` |
| بررسی آمادگی پاس | `GET /stages/{id}/check-pass` |
| پاس کردن مرحله | `POST /stages/{id}/pass` |
| فیل کردن مرحله | `POST /stages/{id}/fail` |
| ویرایش قوانین | `PATCH /stages/{id}/rules` |
| معاملات مرحله | `GET /stages/{id}/trades` |
| برداشت | `POST /stages/{id}/withdraw` + `GET /stages/{id}/withdrawals` |
| هشدارها | `GET /alerts`, `POST /alerts/generate`, `PATCH /alerts/{id}/read` |
| هزینه‌ها | `POST /costs`, `GET /accounts/{id}/costs` |
| تحلیل پراپ | `GET /analytics` |
| اتصال به حسابداری | `GET/POST /accounts/{id}/finance-account` |

**PropRuleEngine** (`services/prop_rule_engine.py`) — تنها منبع حقیقت:
- `evaluate_stage()` → `equity`, `current_profit`, `max_daily_loss`, `max_total_dd`, `trading_days`, `ready_to_pass`, `violations`, `withdrawable_profit`
- `validate_withdrawal()`
- **واحدها:** همهٔ مبالغ **دلار**؛ UI فقط درصد را نمایش/دریافت می‌کند.

**فازهای مرتبط:** ۶، ۱۶، ۲۱، ۲۵

---

### ۴.۸ 💰 مالی (۹ گزارش) — `FinancePage.tsx` + `/api/finance/*`

**نهادها:** `Account` (bank/exchange/crypto_wallet/broker/prop) + `Category` + `Transaction`

**۹ تب گزارش:**

| # | تب | Endpoint |
|---|---|---|
| ۱ | خلاصه | `GET /summary` |
| ۲ | تراکنش‌ها | `GET/POST /transactions` |
| ۳ | جریان نقدی | `GET /charts/cashflow` |
| ۴ | توزیع | `GET /charts/distribution` |
| ۵ | ماهانه | `GET /reports/monthly` |
| ۶ | تفکیک دسته | `GET /reports/category-breakdown` |
| ۷ | مقایسهٔ حساب | `GET /reports/account-comparison` |
| ۸ | سود/زیان | `GET /reports/profit-loss` |
| ۹ | دارایی قابل برداشت | `GET /spendable-assets` |

**گزارش‌های فاز ۲۲:**

| Endpoint | توضیح |
|---|---|
| `GET /real-pnl` | سود/زیان Real: مرحلهٔ ۳ پراپ + بروکر (net_pnl) |
| `GET /net-profit` | سود خالص = سود Real − هزینه‌ها |
| `GET /money-flow` | جریان پول بین حساب‌ها |
| `GET /expenses` | تفکیک هزینه‌ها |
| `GET /money-cycle` | چرخهٔ پول (واریز/برداشت/تبدیل/انتقال) |
| `GET /financial-calendar` | تقویم مالی شمسی |
| `GET /asset-trend` | روند تجمعی دارایی |
| `GET /exchange-rates` | نرخ تبدیل IRR→USD |
| `GET /withdrawals/stats` | آمار برداشت‌ها |

**فازهای مرتبط:** ۹، ۱۱، ۱۵.۱۲، ۲۱، ۲۲، ۲۵

---

### ۴.۹ 📅 تقویم — `CalendarPage.tsx` + `GET /api/analytics/calendar`

- تقویم **شمسی** با گروه‌بندی معاملات بر اساس روز
- پارامترها: `year`/`month` (شمسی) یا `from_date`/`to_date` (میلادی)
- خروجی هر روز: `trade_count`, `total_pnl`, `win_rate`, `trades[]`

**فازهای مرتبط:** Sprint 9، ۱۴.۳

---

### ۴.۱۰ 🛡️ مدیریت ریسک — `RiskManagementPage.tsx`

| Endpoint | خروجی |
|---|---|
| `GET /api/analytics/risk-metrics` | Sharpe, Sortino, Calmar, VaR/CVaR, Kelly, Ulcer, ROR, open exposure |
| `GET /api/analytics/risk-advanced?date_from=&date_to=` | نسخهٔ پیشرفته با فیلتر بازه |

**فازهای مرتبط:** ۱۴.۴، ۱۵.۳

---

### ۴.۱۱ 📥 واردات — `ImportPage.tsx` + `POST /api/imports/{soft4x|mt4}`

| ویژگی | توضیح |
|---|---|
| منابع | **Soft4X** (HTML report) + **MT4** (HTML report) |
| Rate Limit | `IMPORT_RATE_LIMIT` (۱۰ درخواست/دقیقه) |
| Duplicate Detection | `trade_hash` = MD5 روی فیلدهای کلیدی |
| Symbol Mapping | تبدیل نماد بروکر → نماد کانونیک (`/api/symbol-mappings`) |
| هدف | نسخه / مرحلهٔ پراپ (با `version_id` صحیح) |
| Auto test_type | برای prop/personal → `REAL` |
| به‌روزرسانی پراپ | `_update_prop_stage_profit` پس از import |

**فازهای مرتبط:** ۵، ۱۵.۲

---

### ۴.۱۲ ⚙️ تنظیمات — `SettingsPage.tsx` + `/api/settings/`

- `theme` (dark/light/system)، `font_size`، `timezone`، `currency`، `calendar` (persian/gregorian)، `default_risk_percent`، `default_profit_share`
- مدل: `UserSettings` (تک‌رکوردی — `get_or_create_settings`)
- شامل `BackupManager` (بخش ۴.۱۴)

**فازهای مرتبط:** ۱۲، ۱۷

---

### ۴.۱۳ 💸 برداشت‌ها (Payout History) — `PayoutHistoryPage.tsx`

| Endpoint | توضیح |
|---|---|
| `GET /api/prop/payouts` | لیست payoutهای پراپ |
| `GET /api/prop/payouts/stats` | آمار (جمع، تعداد، میانگین) |
| `POST /api/prop/payouts` | ثبت برداشت + ساخت `Transaction` خودکار |
| `PATCH/PUT/DELETE /api/prop/payouts/{id}` | ویرایش/حذف |
| `GET /api/broker/payouts` | برداشت‌های بروکر |
| `GET /api/broker/payouts/stats` | آمار بروکر |

**فازهای مرتبط:** ۱۶، ۲۱

---

### ۴.۱۴ 🗄️ Backup — `BackupManager.tsx` + `/api/backup/*`

| Endpoint | توضیح |
|---|---|
| `POST /create` | Backup دستی (SQLite Online Backup API) |
| `GET /list` | لیست Backupها (نام/حجم/تاریخ) |
| `GET /download/{filename}` | دانلود |
| `POST /restore/{filename}` | بازیابی (Backup ایمنی خودکار قبل + `engine.dispose()`) |
| `DELETE /{filename}` | حذف |
| `GET/PUT /settings` | تنظیم Backup خودکار (بازه/تعداد نگهداری) |

**Backup خودکار:** thread پس‌زمینه در `main.py` (`_backup_loop`) — هر ۳۰ دقیقه بررسی + Backup اولیه در startup.

**فازهای مرتبط:** ۱۷، ۱۸

---

## ۵. مدل‌های دیتابیس

**۲۱ مدل در ۵ فایل · ۸ migration**

### ۵.۱ `models/strategy.py` (۲۸۴ خط)

| مدل | جدول | فیلدهای کلیدی |
|---|---|---|
| `Strategy` | `strategies` | `id`, `name`, `description`, `created_at` |
| `StrategyVersion` | `strategy_versions` | `id`, `strategy_id`→, `version_name`, `rules_note`, `status`, `test_type`, `forked_from_version_id`(self-FK), `created_at` |
| **`Trade`** | `trades` | `id`, `version_id`→, `prop_stage_id`→, `finance_account_id`→, `symbol`, `direction`, `open_time`, `close_time`, `open_price`, `close_price`, `size`, `sl`, `tp`, `pnl`, `r_multiple`, `commission`, `swap`, `entry_sequence`, `source`, `test_type`, `note`, `screenshot_path`, `raw_data`(JSON), `trade_hash`(idx), **`is_deleted`**(idx), `created_at` |
| `CustomTimeInterval` | `custom_time_intervals` | `name`, `symbol`, `start_hour/min`, `end_hour/min`, `label`, `priority`, `is_active` |
| `TimePoint` | `time_points` | `symbol`, `hour`, `minute`, `label`, `is_active` |
| `AnalysisResult` | `analysis_results` | `scope`, `scope_key`, `version_id`/`prop_stage_id`/`finance_account_id`، ۱۳ متریک + ۵ JSON (consistency/session/weekday/hour/custom_time) — **`UniqueConstraint(scope, scope_key)`** |
| `AnalysisRun` | `analysis_runs` | مثل `AnalysisResult` + `full_metrics`(JSON) — **بدون unique** (تاریخچه) |
| `SymbolMapping` | `symbol_mappings` | `original_symbol`(unique), `canonical_symbol`, `description` |

> ⚠️ **مقدار `AnalysisScope` به‌صورت NAME ذخیره می‌شود:** `'VERSION'`, `'PROP_STAGE'`, `'BROKER'`

### ۵.۲ `models/prop.py` (۱۳۸ خط)

| مدل | جدول | فیلدهای کلیدی |
|---|---|---|
| `PropFirm` | `prop_firms` | `name`, `default_profit_share`, `website`, `notes` |
| `PropFirmDefaultRules` | `prop_firm_default_rules` | `prop_firm_id`→, `stage_type`, `profit_target`, `max_daily_dd`, `max_total_dd`, `min_trading_days`, `profit_share_percentage` |
| `PropAccount` | `prop_accounts` | `prop_firm_id`→, `account_label`, `account_number`, `currency`, `is_active`, `finance_account_id`→`accounts.id` |
| `PropStage` | `prop_stages` | `prop_account_id`→, `stage_type`, `status`, `start/end_date`, `profit_target`, `max_daily_dd`, `max_total_dd`, `min_trading_days`, `restrictions`(JSON), `initial_balance`, `final_balance`, `profit_share_percentage`, `total_withdrawn`, `current_profit`, `failure_reason`, `failure_details` |
| `PropWithdrawal` | `prop_withdrawals` | `prop_stage_id`→, `amount`, `withdrawal_date`, `note`, `destination_account_id`→`accounts.id` |
| `PropCost` | `prop_costs` | `prop_account_id`→, `cost_type`, `amount`, `currency`, `cost_date`, `is_refunded` |
| `PropAlert` | `prop_alerts` | `prop_stage_id`→, `message`, `is_read` |

**Enumها:** `StageType` (STAGE_1/STAGE_2/FUNDED_REAL) · `StageStatus` (ACTIVE/PASSED/FAILED/CLOSED) · `FailureReason` (۶ مقدار)

### ۵.۳ `models/finance.py` (۱۲۴ خط)

| مدل | جدول | فیلدهای کلیدی |
|---|---|---|
| `Account` | `accounts` | `name`, `type`, `currency`, `balance`, `card_number`, `broker_name`, `prop_firm_name`, `prop_firm_id`→ |
| `Category` | `categories` | `name`, `type`, `color`, `icon` |
| `Transaction` | `transactions` | `account_id`→, `category_id`→, `amount`, `currency`, `date`, `description`, `type`, `from_account_id`→, `to_account_id`→, `related_trade_id`→`trades.id`, `related_prop_account_id`→, **`is_deleted`** |

**Enumها:** `AccountType` (BANK/EXCHANGE/CRYPTO_WALLET/BROKER/PROP) · `Currency` (IRR/USD) · `CategoryType` (INCOME/EXPENSE/TRANSFER/EXCHANGE) · `TransactionType` (DEPOSIT/WITHDRAWAL/EXCHANGE/PROFIT/LOSS/FEE/PURCHASE)

### ۵.۴ `models/personal.py` (۳۷ خط) + `models/settings.py` (۱۷ خط)

| مدل | جدول | فیلدهای کلیدی |
|---|---|---|
| `JournalReview` | `journal_reviews` | `trade_id`→, `setup_quality`, `execution_quality`, `rule_violations`, `notes`, `lessons`, `rating` |
| `Screenshot` | `screenshots` | `entity_type` (`trade`/`review`), `entity_id`, `review_id`→, `file_path`, `file_hash`, `description` |
| `UserSettings` | `user_settings` | `theme`, `font_size`, `timezone`, `currency`, `calendar`, `default_risk_percent`, `default_profit_share` |

### ۵.۵ نمودار روابط (ER — ساده‌شده)

```
Strategy ──1:N──► StrategyVersion ──1:N──► Trade ──1:N──► JournalReview ──1:N──► Screenshot
                     │                        │
                     │                        ├──N:1──► PropStage ──N:1──► PropAccount ──N:1──► PropFirm
                     │                        │              │
                     │                        │              └──1:N──► PropWithdrawal ──N:1──► Account
                     │                        │
                     ├──1:N──► AnalysisResult │
                     └──1:N──► AnalysisRun    └──N:1──► Account ──1:N──► Transaction ──N:1──► Category
                                                                  ▲                    │
                                                                  └──related_trade_id──┘
```

### ۵.۶ Enumها (خلاصه)

| Enum | فایل | مقادیر |
|---|---|---|
| `StrategyStatus` | strategy | research, backtest, optimization, forward, approved, live, review, deprecated, archived, rejected |
| `TradeSource` | strategy | mt4_import, soft4x_import, manual |
| `TestType` | strategy | backtest, forward, real |
| `AnalysisScope` | strategy | version, prop_stage, broker |
| `StageType` | prop | stage_1, stage_2, funded_real |
| `StageStatus` | prop | active, passed, failed, closed |
| `FailureReason` | prop | max_daily_dd_exceeded, max_total_dd_exceeded, profit_target_not_met, min_trading_days_not_met, rule_violation, manual, other |
| `AccountType` | finance | bank, exchange, crypto_wallet, broker, prop |
| `Currency` | finance | IRR, USD |
| `CategoryType` | finance | income, expense, transfer, exchange |
| `TransactionType` | finance | deposit, withdrawal, exchange, profit, loss, fee, purchase |

---

## ۶. API Endpoints

**آمار کل:** ۱۰۸ مسیر یکتا · ۱۳۷ عملیات · ۱۲ router · مستندات تعاملی در `http://localhost:8000/docs`

> همهٔ مسیرها زیر `http://localhost:8000` (پیش‌فرض). Prefixها در `main.py:151-162` ثبت می‌شوند.

### ۶.۱ `/api/strategies` (strategies.py) — ۹ مسیر

| متد | مسیر | توضیح |
|---|---|---|
| GET / POST | `/` | لیست / ساخت استراتژی |
| GET / PATCH / DELETE | `/{strategy_id}` | جزئیات / ویرایش / حذف |
| GET / POST | `/{strategy_id}/versions` | لیست / ساخت نسخه |
| GET | `/versions/all` | همهٔ نسخه‌ها (با `trades_count`) |
| PATCH / DELETE | `/versions/{version_id}` | ویرایش / حذف نسخه |
| POST | `/versions/{version_id}/fork` | **Fork نسخه** (فاز ۲۴) |
| GET | `/versions/{version_id}/trades` | معاملات نسخه |
| GET | `/{strategy_id}/stats` | آمار تجمعی استراتژی |

### ۶.۲ `/api/prop` (prop.py) — ۲۲ مسیر

| متد | مسیر | توضیح |
|---|---|---|
| GET / POST | `/firms` | شرکت‌های پراپ |
| GET | `/firms/{firm_id}/default-rules` | قوانین پیش‌فرض |
| GET / POST | `/accounts` | حساب‌های پراپ |
| GET | `/accounts/{account_id}` | جزئیات |
| GET / POST | `/accounts/{account_id}/finance-account` | **پل به حسابداری** (فاز ۵.۱) |
| GET | `/accounts/{account_id}/costs` | هزینه‌ها |
| POST | `/costs` | ثبت هزینه |
| GET | `/stages/all` | همهٔ مراحل |
| GET | `/stages/{stage_id}/check-pass` | بررسی آمادگی پاس |
| POST | `/stages/{stage_id}/pass` | پاس کردن + ساخت مرحلهٔ بعدی |
| POST | `/stages/{stage_id}/fail` | فیل کردن (+ دلیل) |
| PATCH | `/stages/{stage_id}/rules` | ویرایش قوانین |
| GET | `/stages/{stage_id}/trades` | معاملات مرحله |
| POST | `/stages/{stage_id}/withdraw` | برداشت (فاز ۱۶) |
| GET | `/stages/{stage_id}/withdrawals` | تاریخچهٔ برداشت مرحله |
| GET / POST | `/payouts` | Payoutها (فاز ۱۶) |
| GET | `/payouts/stats` | آمار payoutها |
| POST / PATCH / PUT / DELETE | `/payouts/{payout_id}` | مدیریت payout |
| GET | `/alerts` | هشدارها |
| POST | `/alerts/generate` | تولید هشدار |
| PATCH | `/alerts/{alert_id}/read` | علامت خوانده‌شده |
| GET | `/analytics` | تحلیل پراپ |

### ۶.۳ `/api/trades` (trades.py) — ۶ مسیر

| متد | مسیر | توضیح |
|---|---|---|
| GET | `/` | لیست + فیلتر + صفحه‌بندی |
| GET / PATCH | `/{trade_id}` | جزئیات / ویرایش کنترل‌شده |
| DELETE | `/{trade_id}` | **حذف نرم** (`?hard=true` → حذف کامل) — فاز ۲۵ |
| POST | `/manual` | معاملهٔ دستی |
| POST | `/batch-delete` | **حذف گروهی** — فاز ۲۵ |
| POST / GET | `/{trade_id}/screenshots` | آپلود / لیست اسکرین‌شات |
| DELETE | `/screenshots/{screenshot_id}` | حذف اسکرین‌شات |

### ۶.۴ `/api/analytics` (analytics.py) — ۲۱ مسیر

| متد | مسیر | توضیح |
|---|---|---|
| GET | `/dashboard?date_from=&date_to=` | دادهٔ داشبورد |
| GET | `/yesterday` | عملکرد دیروز (شمسی) |
| GET | `/risk-metrics` | شاخص‌های ریسک |
| GET | `/risk-advanced` | ریسک پیشرفته (فاز ۱۴.۴) |
| GET | `/calendar?year=&month=` | تقویم معاملات |
| POST | `/analyze/{version_id}` | تحلیل legacy |
| POST | `/analyze/version/{version_id}?test_type=` | تحلیل نسخه (فاز ۲۰/۲۳) |
| POST | `/analyze/prop/{prop_stage_id}` | تحلیل مرحلهٔ پراپ |
| POST | `/analyze/broker/{finance_account_id}` | تحلیل حساب بروکر |
| GET | `/analysis/version/{version_id}` | خواندن تحلیل ذخیره‌شده |
| GET | `/analysis/prop/{prop_stage_id}` | خواندن تحلیل پراپ |
| GET | `/analysis/broker/{finance_account_id}` | خواندن تحلیل بروکر |
| GET | `/{version_id}` | تحلیل جاری نسخه |
| GET | `/{version_id}/history` | تاریخچهٔ `AnalysisRun` |
| POST | `/compare` | مقایسهٔ نسخه‌ها |
| GET / POST | `/intervals/` | بازه‌های سفارشی |
| DELETE | `/intervals/{interval_id}` | حذف بازه |
| POST | `/intervals/seed-gold` | seed بازه‌های طلا |
| POST | `/intervals/seed-dji` | seed بازه‌های داوجونز |

### ۶.۵ `/api/finance` (finance.py) — ۳۵ مسیر

| متد | مسیر |
|---|---|
| GET / POST | `/accounts`, `/categories`, `/transactions`, `/withdrawals` |
| GET / PATCH / DELETE | `/accounts/{id}`, `/categories/{id}`, `/transactions/{id}`, `/withdrawals/{id}` |
| GET | `/accounts/{account_id}/stats` |
| GET | `/summary`, `/spendable-assets`, `/real-pnl`, `/net-profit`, `/expenses`, `/money-flow`, `/money-cycle`, `/asset-trend`, `/exchange-rates`, `/financial-calendar` |
| GET | `/charts/cashflow`, `/charts/distribution` |
| GET | `/reports/monthly`, `/reports/category-breakdown`, `/reports/account-comparison`, `/reports/profit-loss` |
| GET | `/withdrawals/stats` |
| POST | `/sync/trades` (**Finance Bridge** — فاز ۲۱), `/seed` |

### ۶.۶ بقیهٔ routerها

| Prefix | فایل | مسیرها | توضیح |
|---|---|---|---|
| `/api/imports` | imports.py | `POST /soft4x`, `POST /mt4` | واردات (Rate-limited) |
| `/api/personal` | personal.py | `POST /journal/review`, `GET /journal/reviews`, `DELETE /journal/reviews/{id}`, `POST/GET/DELETE .../screenshots`, `GET /prop-accounts-list` | ژورنال + اسکرین‌شات |
| `/api/export` | export.py | `GET /trades/csv`, `/trades/pdf`, `/analysis/pdf`, `/dashboard/pdf` | خروجی (Rate-limited) |
| `/api/broker` | broker.py | `GET /payouts`, `GET /payouts/stats` | برداشت‌های بروکر |
| `/api/backup` | backup.py | `POST /create`, `GET /list`, `GET /download/{f}`, `POST /restore/{f}`, `GET/PUT /settings`, `DELETE /{f}` | Backup |
| `/api/symbol-mappings` | symbol_mappings.py | `GET/POST /`, `PATCH/DELETE /{id}`, `POST /seed-defaults` | نگاشت نماد |
| `/api/settings` | settings.py | `GET/PATCH /` | تنظیمات |
| `/` | main.py | `GET /` | Health check |

### ۶.۷ نکات مهم endpointها

| نکته | توضیح |
|---|---|
| **Route Order** | `POST /api/trades/batch-delete` باید قبل از هر `POST /{param}` باشد — هیچ تضادی وجود ندارد |
| **Rate Limit** | `/api/imports/*` و `/api/export/*` محدود شده‌اند (`slowapi`) |
| **Static** | `GET /storage/*` → فایل‌های اسکرین‌شات |
| **Docs** | `/docs` (Swagger) و `/redoc` |
| **Enum در ورودی** | `test_type` به‌صورت string می‌آید و در API به Enum نگاشت می‌شود |

---

## ۷. فازهای انجام‌شده

### ۷.۱ فاز ۱–۸ (پایهٔ پروژه)

| فاز | نام | چه چیزی ساخته شد | فایل‌های کلیدی | مستند |
|---|---|---|---|---|
| **۰** | Architecture Freeze | تثبیت معماری Router/Service/Model + Trade Classification Contract | `main.py` | `MokTradeDesk-1.md` |
| **۱** | Migration Foundation | Alembic + اسکیمای اولیه + `trade_hash` | `c4838cd01bbd_initial_schema_with_trade_hash.py` | — |
| **۲** | Trade Contract | `TradeValidator` (Classification/Numbers/Dates)، N+1 حل با `joinedload`، فیلترهای جدید | `utils/trade_validator.py`, `api/trades.py` | `2302dc8` |
| **۳** | Trades API | صفحه‌بندی + مرتب‌سازی + فیلترهای پیشرفته | `api/trades.py` | — |
| **۴** | Trades Frontend | `TradesPage.tsx` کامل (فیلتر/ویرایش/اسکرین‌شات) | `pages/TradesPage.tsx` | — |
| **۵** | Import Pipeline | `Soft4XImporter` + `MT4Importer`، Duplicate Detection، Symbol Mapping | `services/import_service.py` | `SPRINT4-5_REPORT.md` |
| **۶** | Prop Rule Engine | `PropRuleEngine` کامل + **درصد↔دلار** در UI | `services/prop_rule_engine.py` | `PHASE6_DARKMODE_REPORT.md` |
| **۷** | Analysis Engine | `AnalysisService` + `AnalysisRun` + تحلیل Session/Weekday/Hour/Custom | `services/analysis_service.py` | `PHASE7_DARKMODE_REPORT.md` |
| **۸** | Journal / Screenshots | `JournalReview` + `Screenshot` + `JournalPage` | `models/personal.py`, `api/personal.py` | `PHASE8_DARKMODE_REPORT.md` |

### ۷.۲ فاز ۹–۱۴ (مالی + UX + داشبورد)

| فاز | نام | چه چیزی | مستند |
|---|---|---|---|
| **۹** | ادغام Personal → Finance | حذف `PersonalAccount`/`LedgerTransaction`؛ `Trade.personal_account_id` → `finance_account_id` | `PHASE9_REPORT.md` |
| **۱۰** | UI معاملهٔ دستی | فیلد حساب مالی در فرم معاملهٔ دستی | `PHASE10_REPORT.md` |
| **۱۱** | گزارش‌های مالی پیشرفته | گزارش‌های ماهانه/دسته‌بندی/مقایسه حساب | `PHASE11_REPORT.md` |
| **۱۲** | Testing Suite | راه‌اندازی `pytest` (۹۰ تست) + `vitest` (۹ تست) | `PHASE12_REPORT.md` |
| **۱۳** | بهبودهای UX | `ToastProvider`, `ErrorBoundary`, `CommandPalette`, `EmptyState`, `Tooltip`, `ConfirmDialog`, `LoadingButton` + میانبرها | `PHASE13_REPORT.md` |
| **۱۴.۱** | رفع باگ + نمودار پایه | Equity Curve, Win/Loss Pie, PnL Distribution, Session bars | `PHASE14_1_REPORT.md` |
| **۱۴.۲** | ترتیب + کارت دیروز | `GET /yesterday` (شمسی) + ویجت مالی | `PHASE14_2_REPORT.md` |
| **۱۴.۳** | فیلتر بازه + جدول | `dashboard?date_from/date_to` + جدول معاملات | `PHASE14_3_REPORT.md` |
| **۱۴.۴** | ریسک پیشرفته | `GET /risk-advanced` (Sharpe/Sortino/Calmar/VaR/CVaR/Kelly) | `PHASE14_4_REPORT.md` |
| **۱۴.۵** | Empty State + Refresh + Quick Actions | بهبود تجربهٔ صفحات خالی | `PHASE14_5_REPORT.md` |

### ۷.۳ فاز ۱۵ (پرفرمنس + امنیت)

| زیرفاز | نام | دستاورد | مستند |
|---|---|---|---|
| **۱۵.۱** | رفع باگ‌های P0 | CORS (`*` حذف شد)، کد مردهٔ `export.py`، مسیر تکراری `finance.py`، `return` فراموش‌شده | `PHASE15_1_REPORT.md` |
| **۱۵.۲** | N+1 + Rate Limiting | رفع N+1 در چند endpoint + `slowapi` روی import/export | `PHASE15_2_REPORT.md` |
| **۱۵.۳** | SQL Aggregation | محاسبات داشبورد از Python → SQL — **۲–۴ برابر سریع‌تر** | `PHASE15_3_REPORT.md` |
| **۱۵.۴** | Bundle Splitting | ۱۳ صفحه `lazy()` + `<Suspense>` → **۷۷٪ کاهش bundle اولیه** | `PHASE15_4_REPORT.md` |
| **۱۵.۵/۷/۸/۹/۱۰** | پاکسازی‌ها | حذف توابع تکراری، env variables، ایندکس DB، interceptor | `PHASE15_5_7_10_REPORT.md` |
| **۱۵.۱۱/۱۲** | Withdrawals | endpointهای برداشت + soft delete | `PHASE15_11_12_REPORT.md` |

### ۷.۴ فاز ۱۶–۱۹

| فاز | نام | دستاورد | مستند |
|---|---|---|---|
| **۱۶** | Payout History | مدل/API/صفحهٔ برداشت‌ها + اتصال خودکار به `Transaction` | `PHASE16_REPORT.md` |
| **۱۷** | Backup خودکار | `backup_service.py` + thread پس‌زمینه + `BackupManager.tsx` | `PHASE17_REPORT.md` |
| **۱۸** | Auto-Migrate Protection | اجرای خودکار `alembic upgrade head` در startup (بدون از دست دادن لاگ) | `PHASE18_REPORT.md` |
| **۱۹** | جداسازی REAL از تحلیل | `analysis_trades_filter()` — معاملات REAL از تحلیل نسخه کنار گذاشته می‌شوند | `PHASE19_REPORT.md` |

### ۷.۵ فاز ۲۰–۲۵ (تحلیل چنددامنه + مالی + حذف نرم)

| فاز | نام | دستاورد | مستند |
|---|---|---|---|
| **۲۰** | تحلیل ۶گانه | `AnalysisScope` (VERSION/PROP_STAGE/BROKER) + `scope_key` + ۶ تب + داشبورد پول واقعی | `PHASE20_REPORT.md`, `PHASE20_DESIGN.md` |
| **۲۱** | Finance Bridge | `FinanceSyncService` — هر معاملهٔ بسته‌شدهٔ بروکر/فاندد → `Transaction` + به‌روزرسانی `Account.balance` | `PHASE21_REPORT.md` |
| **۲۲** | گزارش‌های مالی | ۹ گزارش: `real-pnl`, `net-profit`, `money-flow`, `expenses`, `money-cycle`, `financial-calendar`, `asset-trend`, `exchange-rates`, `spendable-assets` | `PHASE22_REPORT.md` |
| **۲۳** | استقلال تحلیل | Backtest/Forward مستقل (کلید `version_id:TEST_TYPE`) + رفع ۵ باگ دامنه | `PHASE23_REPORT.md` |
| **۲۴** | Fork + Launcher | Fork کامل نسخه (۴ فیلد) + `start.vbs`/`stop.vbs`/`splash.hta` | `PHASE24_REPORT.md` |
| **۲۵** | Soft Delete | `Trade.is_deleted` + Migration + حذف نرم/سخت/گروهی + ConfirmDialog + فیلتر در همهٔ کوئری‌ها | `PHASE25_REPORT.md`, `PHASE25_PART2_REPORT.md` |

### ۷.۶ Sprintهای جانبی

| Sprint | نام | مستند |
|---|---|---|
| Sprint 4-5 | Prop percentages + Duplicate Detection + net_pnl | `SPRINT4-5_REPORT.md` |
| Sprint 6 | Export PDF/CSV | `SPRINT6_REPORT.md` |
| Sprint 7 | جایگزینی `datetime.utcnow()` deprecated | `SPRINT7_REPORT.md` |
| Sprint 8 | Cleanup | `CLEANUP_REPORT.md` |
| Sprint 9 | Calendar View (شمسی) | `SPRINT9_REPORT.md` |
| Sprint 10 | UX Quality + env variables | `SPRINT10_REPORT.md` |

### ۷.۷ جدول Migrationها

| # | Revision | down_revision | توضیح |
|---|---|---|---|
| ۱ | `c4838cd01bbd` | `None` | اسکیمای اولیه + `trade_hash` |
| ۲ | `1771fcd3af2f` | `c4838cd01bbd` | جدول `analysis_runs` |
| ۳ | `51ea09b4aa3d` | `1771fcd3af2f` | جداول مالی (`accounts`, `categories`, `transactions`) |
| ۴ | `b7d4e19c2f83` | `51ea09b4aa3d` | `prop_accounts.finance_account_id` + `prop_withdrawals.destination_account_id` |
| ۵ | `9f1a2b3c4d5e` | `b7d4e19c2f83` | ادغام Personal → Finance |
| ۶ | `a3f7c21b9d84` | `9f1a2b3c4d5e` | فاز ۲۰: `AnalysisScope` |
| ۷ | `e5f6a7b8c9d0` | `a3f7c21b9d84` | `strategy_versions.test_type` |
| ۸ | `f1a2b3c4d5e6` | `e5f6a7b8c9d0` | **فاز ۲۵: `trades.is_deleted` + index** → **head** |

**Handoff (قبل از بلوپرینت):** طراحی اولیه و Contractها در `MokTradeDesk-1.md`، `MokTradeDesklast-bluprint-2.md`، `MokTradeDesk-3..md` و `PROP_FINANCE_INTEGRATION.md`.

---

## ۸. تست‌ها

### ۸.۱ Backend — pytest (۹۰ تست، ۷ فایل)

| فایل | تعداد | پوشش |
|---|---|---|
| `test_finance.py` | ۲۳ | `_gregorian_to_jalali`, `spendable-assets`, `real-pnl`, `net-profit`, money-flow, calendar, ... |
| `test_trades.py` | ۱۸ | `TradeValidator` + endpointهای معاملات + **فاز ۲۵ (۸ تست soft/batch/hard delete)** |
| `test_analysis_scope.py` | ۱۴ | دامنه‌های تحلیل (فاز ۲۰) |
| `test_soft_delete_filters.py` | ۱۱ | **فاز ۲۵ بخش ۲** — فیلتر is_deleted در پراپ/مالی/تحلیل/گزارش |
| `test_prop.py` | ۱۰ | `PropRuleEngine` + endpointهای پراپ |
| `test_analysis_phase23.py` | ۹ | استقلال Backtest/Forward (فاز ۲۳) |
| `test_imports.py` | ۵ | Import Pipeline |
| **مجموع** | **۹۰** | — |

**زیرساخت تست** (`conftest.py`):
- `db_session` — SQLite درون‌حافظه‌ای (`sqlite://` + `StaticPool`) برای هر تست → DB واقعی دست‌نخورده می‌ماند.
- `client` — `TestClient` با `dependency_overrides[get_db]`.

**اجرا:**
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q          # 90 passed
.\venv\Scripts\python.exe -m pytest --cov=app   # با coverage
```

### ۸.۲ Frontend — vitest (۹ تست، ۲ فایل)

| فایل | تعداد | پوشش |
|---|---|---|
| `components.test.tsx` | ۵ | `Badge`, `ProgressBar`, `Card` |
| `utils.test.ts` | ۴ | توابع تاریخ شمسی |

**اجرا:**
```powershell
cd frontend
npm run test          # vitest run → 9 passed
npm run test:watch    # حالت watch
```

### ۸.۳ وضعیت کیفیت

| ابزار | دستور | نتیجهٔ فعلی |
|---|---|---|
| TypeScript | `npx tsc -b --force` | ✅ EXIT=0 |
| Frontend Build | `npm run build` | ✅ EXIT=0 |
| Backend Import | `python -c "import app.main"` | ✅ OK |
| ESLint | `npm run lint` | (بدون خطای مسدودکننده) |

> **پوشش تست نسبتاً پایین است** (۹۰ بک‌اند + ۹ فرانت). جزئیات پیشنهادی در بخش ۱۳.

---

## ۹. قابلیت‌های کلیدی

| # | قابلیت | توضیح | محل پیاده‌سازی |
|---|---|---|---|
| ۱ | **Dark Mode** | مبتنی بر **CSS Variables** (`var(--*)`) — بیش از ۱۷۰۰ ارجاع؛ تم از `localStorage` + `prefers-color-scheme` | `App.tsx:56-70` |
| ۲ | **Command Palette** | جستجوی سریع بین صفحات (Ctrl+K) با فیلتر/↑↓/↵/Esc | `components/CommandPalette.tsx` |
| ۳ | **Multi-scope Analysis** | ۶ دامنهٔ تحلیل مستقل (`VERSION`×۲ + `PROP_STAGE` + `BROKER` + compare + history) | `AnalysisScope`, `AnalysisService` |
| ۴ | **Finance Bridge** | تبدیل خودکار معاملات بسته‌شده → `Transaction` + به‌روزرسانی موجودی | `services/finance_sync_service.py` |
| ۵ | **Soft Delete** | حذف نرم + حذف سخت اختیاری + حذف گروهی + فیلتر در همهٔ کوئری‌ها | `Trade.is_deleted`, `trade_scope.py` |
| ۶ | **Launcher (Splash + Progress)** | `start.vbs` + `splash.hta`: migration → backend → frontend → browser، با وضعیت زنده | `start.vbs`, `splash.hta` |
| ۷ | **Payout History** | تاریخچهٔ برداشت‌ها (پراپ + بروکر) با آمار | `prop.py`, `broker.py` |
| ۸ | **Backup خودکار** | thread پس‌زمینه + SQLite Online Backup API + بازیابی ایمن | `services/backup_service.py` |
| ۹ | **Duplicate Detection** | MD5 hash معامله (`trade_hash`) در Import | `import_service.py` |
| ۱۰ | **Prop Rule Engine** | واحد مرکزی قوانین پراپ | `services/prop_rule_engine.py` |
| ۱۱ | **درصد ↔ دلار** | UI درصد، DB دلار | `PropPage.tsx`, `prop.py` |
| ۱۲ | **تاریخ شمسی** | تبدیل دوطرفه + تقویم شمسی | `utils/jalali.ts`, `finance._gregorian_to_jalali` |
| ۱۳ | **تاریخچهٔ تحلیل** | `AnalysisRun` (snapshot کامل JSON) | `analysis_service._analyze` |
| ۱۴ | **Export PDF/CSV** | خروجی با فونت فارسی (RTL) | `api/export.py`, `chart_helpers.py` |
| ۱۵ | **Fork نسخه** | ساخت نسخه از نسخهٔ دیگر + درخت fork | `strategies.py` |
| ۱۶ | **Symbol Mapping** | نگاشت نماد بروکر → کانونیک | `api/symbol_mappings.py` |
| ۱۷ | **Auto-Migrate** | اجرای خودکار migration در startup | `main.py:88-119` |
| ۱۸ | **گالری اسکرین‌شات** | آپلود/گالری/Lightbox | `TradesPage.tsx`, `personal.py` |
| ۱۹ | **Toast سراسری + ErrorBoundary** | بازخورد یکنواخت خطا/موفقیت | `ToastProvider.tsx`, `ErrorBoundary.tsx` |
| ۲۰ | **میانبرهای صفحه‌کلید** | Ctrl+K/D/T/K/N + Esc | `App.tsx` |

---

## ۱۰. امنیت

### ۱۰.۱ وضعیت فعلی

| # | موضوع | وضعیت | محل |
|---|---|---|---|
| ۱ | **CORS محدود** | ✅ فقط `localhost:5173` و `localhost:3000` (wildcard حذف شد) | `main.py:62-68` |
| ۲ | **Rate Limiting** | ✅ `slowapi` روی Import و Export | `core/rate_limit.py` |
| ۳ | **محدودیت حجم آپلود** | ✅ `read_upload_limited(file)` | `utils/uploads.py` |
| ۴ | **Soft Delete** | ✅ حذف بازگشت‌پذیر | `Trade.is_deleted` |
| ۵ | **بدون SQL Injection** | ✅ استفادهٔ کامل از ORM | کل پروژه |
| ۶ | **ماسک شمارهٔ کارت** | ⚠️ `Account.card_number` ذخیره می‌شود — نمایش نیاز به تأیید ماسک دارد | `models/finance.py` |
| ۷ | **Authentication / Authorization** | ❌ **وجود ندارد** (طراحی Local-First) | — |
| ۸ | **کنترل دسترسی Static** | ❌ `GET /storage/*` بدون auth | `main.py:146` |
| ۹ | **Backup قبل از عملیات خطرناک** | ✅ Backup ایمنی خودکار در `restore` | `backup_service.py` |

### ۱۰.۲ ملاحظات مهم

> 🔴 **هشدار:** پروژه **هیچ احراز هویت/مجوزدهی**ای ندارد. این برای طراحی **Local-First** قابل قبول است، اما:
> - اگر پورت ۸۰۰۰ روی شبکه expose شود، **هر کسی** می‌تواند داده‌ها را بخواند/تغییر دهد/حذف کند.
> - **توصیه:** تا زمانی که Authentication اضافه نشده، سرور فقط روی `127.0.0.1` گوش دهد.

### ۱۰.۳ چک‌لیست امنیتی (برای production)

- [ ] پیاده‌سازی JWT یا API-Key (`Depends` روی routerها)
- [ ] محدودکردن `StaticFiles` با auth
- [ ] ماسک `card_number` در پاسخ‌های API
- [ ] `SECRET_KEY` واقعی در `.env` (نه مقدار پیش‌فرض)
- [ ] HTTPS در صورت دسترسی خارجی
- [ ] Backup رمزنگاری‌شده (AES) برای داده‌های حساس

---

## ۱۱. پرفرمنس

### ۱۱.۱ Bundle Splitting (فاز ۱۵.۴)

| قبل | بعد |
|---|---|
| **یک bundle ۱.۰۷MB** (gzip ~۲۷۳kB) — همهٔ ۱۳ صفحه + Recharts | ۱۳ chunk جدا + chunk مشترک |

**خروجی بیلد فعلی:**

| Chunk | حجم | gzip |
|---|---|---|
| `index-*.js` | ۲۴۱ kB | ۷۵ kB |
| `BarChart-*.js` (recharts) | ۳۵۹ kB | ۱۰۴ kB |
| `FinancePage-*.js` | ۷۱ kB | ۱۱ kB |
| `PropPage-*.js` | ۶۸ kB | ۱۱ kB |
| `client-*.js` | ۵۷ kB | ۲۱ kB |
| `ComparisonPage-*.js` | ۵۶ kB | ۱۳ kB |

➡️ **کاهش ~۷۷٪** در حجم اولیهٔ بارگذاری. صفحهٔ پیش‌فرض (Dashboard) با `preloadDashboard()` از قبل بارگذاری می‌شود.

### ۱۱.۲ SQL Aggregation (فاز ۱۵.۳)

| قبل | بعد |
|---|---|
| `db.query(Trade).all()` + محاسبه در Python | `func.sum/count/case/group_by` مستقیم در SQL |

**محل‌های تغییر:** `dashboard`, `risk-advanced`, `risk-metrics`, `calendar`, `strategy_stats` — **۲ تا ۴ برابر سریع‌تر** روی داده‌های واقعی.

### ۱۱.۳ رفع N+1 (فاز ۱۵.۲ + ۱۵.۳)

| # | محل | راه‌حل |
|---|---|---|
| ۱ | `get_trades` (لیست) | `joinedload(Trade.version).joinedload(StrategyVersion.strategy)` |
| ۲ | اسکرین‌شات‌ها | `_get_screenshots_count_map` (یک کوئری برای همه) |
| ۳ | `get_strategies` | `selectinload` + `_trades_count_by_version` (گروهی) |
| ۴ | `JournalPage` | حذف N+1 در reviews/screenshots |
| ۵ | `compare_versions` | واکشی ستونی (`with_entities`) |
| ۶ | `export` | `joinedload` |

### ۱۱.۴ ایندکس‌های دیتابیس

| جدول.ستون | نوع |
|---|---|
| `trades.id` | PK |
| `trades.trade_hash` | index (Duplicate Detection) |
| `trades.is_deleted` | **index (فاز ۲۵)** |
| `analysis_results.scope` / `scope_key` | index + Unique |
| `analysis_runs.scope` / `scope_key` | index |
| `strategy_versions`, `prop_stages`, ... | PK |

### ۱۱.۵ سایر بهینه‌سازی‌ها

| مورد | توضیح |
|---|---|
| محدودیت صفحه | `page_size` سقف ۲۰۰ |
| Rate Limit | جلوگیری از import/export پشت‌سرهم |
| Backup غیرمسدودکننده | thread پس‌زمینه، نه در مسیر request |
| `engine.dispose()` در restore | آزادسازی اتصال‌ها قبل از جایگزینی فایل DB |

---

## ۱۲. راه‌اندازی

### ۱۲.۱ پیش‌نیازها

| ابزار | نسخه | توضیح |
|---|---|---|
| **Windows** | ۱۰/۱۱ | Launcher بر پایهٔ VBScript/HTA |
| **Python** | ۳.۱۲ | `C:\Python312\` (مسیر venv در `backend/venv/`) |
| **Node.js** | ۲۰+ | `C:\Program Files\nodejs\` |
| **pnpm** | ۹+ | `npm i -g pnpm` |
| **Git** | اختیاری | برای نسخه‌بندی |

### ۱۲.۲ راه‌اندازی Backend

```powershell
cd backend

# ۱. ساخت virtualenv
python -m venv venv

# ۲. فعال‌سازی
.\venv\Scripts\Activate.ps1

# ۳. نصب وابستگی‌ها
pip install -r requirements.txt

# ۴. اجرای migration
.\venv\Scripts\alembic upgrade head

# ۵. اجرای سرور
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
➡️ API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

> 💡 در `startup` برنامه، migration **خودکار** اجرا می‌شود؛ مرحلهٔ ۴ اختیاری است.

### ۱۲.۳ راه‌اندازی Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```
➡️ UI: `http://localhost:5173`

### ۱۲.۴ راه‌اندازی یکجا (Launcher)

| فایل | کار |
|---|---|
| **`start.vbs`** | دوبار کلیک → Splash + migration + backend + frontend + باز شدن مرورگر (بی‌پنجره) |
| **`stop.vbs`** | توقف backend + frontend + splash |
| `stop.vbs quiet` | توقف بی‌پیام |

**مراحل داخلی `start.vbs`:**
```
۱. بررسی وجود python.exe در venv
۲. اگر backend و frontend از قبل up باشند → فقط مرورگر باز می‌شود
۳. نمایش splash.hta (خواندن وضعیت از %TEMP%\moktrade_launch_status.txt)
۴. alembic upgrade head           →  8%
۵. uvicorn app.main:app           →  30%  (انتظار تا up)
۶. pnpm dev                       →  68%  (انتظار تا up)
۷. باز کردن http://localhost:5173 →  100%
```

**لاگ‌ها:** `logs/backend.log` · `logs/frontend.log` · `logs/migration.log` · `logs/stop.log` · `logs/app.log`

### ۱۲.۵ متغیرهای محیطی (`.env`)

```env
API_BASE_URL=http://localhost:8000
DATABASE_URL=sqlite:///./trading_desk.db
VITE_API_BASE_URL=http://localhost:8000
SECRET_KEY=change-me-to-a-random-string
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```
> `frontend/src/api/client.ts` از `import.meta.env.VITE_API_BASE_URL` می‌خواند (fallback: `http://localhost:8000`).

### ۱۲.۶ دستورات پرکاربرد

| کار | دستور |
|---|---|
| تست بک‌اند | `cd backend; .\venv\Scripts\python.exe -m pytest -q` |
| تست فرانت | `cd frontend; npm run test` |
| بررسی TypeScript | `cd frontend; npx tsc -b --force` |
| بیلد فرانت | `cd frontend; npm run build` |
| وضعیت migration | `cd backend; .\venv\Scripts\python.exe -m alembic current` |
| ساخت migration | `cd backend; .\venv\Scripts\python.exe -m alembic revision --autogenerate -m "msg"` |
| Backup دستی | `POST /api/backup/create` |

---

## ۱۳. فازهای باقی‌مانده (اختیاری)

| # | قابلیت | اولویت | زمان تخمینی | وابستگی |
|---|---|---|---|---|
| ۱ | **Notifications** (ایمیل / تلگرام / Browser) | P2 | ۶–۸ ساعت | `PropAlert` موجود؛ دکمهٔ 🔔 در `App.tsx` بی‌عمل |
| ۲ | **Excel Export** | P3 | ۳ ساعت | `openpyxl` از قبل در `requirements.txt` |
| ۳ | **Heatmap تقویم** | P3 | ۴ ساعت | `CalendarPage` موجود |
| ۴ | **Multi-Account Prop View** | P2 | ۴ ساعت | `PropRuleEngine` |
| ۵ | **Correlation Matrix** | P3 | ۶ ساعت | `analysis_service` |
| ۶ | **Restore endpoint** | P2 | ۲ ساعت | `Trade.is_deleted` موجود |
| ۷ | **نمایش «حذف‌شده‌ها» در UI** | P2 | ۳ ساعت | `is_deleted` موجود |
| ۸ | **Testing Suite کامل** | P3 | ۲۵+ ساعت | — |
| ۹ | **Authentication (JWT)** | P1 (اگر expose شود) | ۶–۸ ساعت | — |
| ۱۰ | **API Versioning** (`/api/v1/`) | P4 | ۲ ساعت | — |
| ۱۱ | **Mobile Responsive / PWA** | P3 | ۴–۶ ساعت | Tailwind موجود |
| ۱۲ | **Trade Playback** | P4 | ۸ ساعت | `lightweight-charts` |
| ۱۳ | **AI Journal Assistant** | P4 | ۱۰ ساعت | `JournalReview` |
| ۱۴ | **Monte Carlo Simulation** | P3 | ۶ ساعت | `analysis_service` |
| ۱۵ | **Strategy Rule Builder (بصری)** | P4 | ۸ ساعت | `rules_note` موجود |

### ۱۳.۱ وضعیت بلوپرینت اولیه

> **نکته:** فایل `BLUEPRINT_STATUS.md` در ریشهٔ پروژه **وجود ندارد**. نزدیک‌ترین مرجع، `REMAINING_BLUEPRINT_ITEMS.md` است که **قدیمی** است (بر پایهٔ مستندات قبل از Sprint 7) و می‌گوید PHASE 9/10 ناتمام‌اند — در حالی که در کد واقعی:
> - PHASE 9 (Testing) → **کامل** (۹۰ تست بک‌اند)
> - PHASE 10 (Personal Finance) → **کامل** (ماژول `finance` با ۳۵ endpoint)

---

## ۱۴. پیشنهادات برای آینده

### ۱۴.۱ قابلیت‌های جدید

| # | قابلیت | ارزش | توضیح |
|---|---|---|---|
| ۱ | **Notifications چندکاناله** | 🔴 بالا | تلگرام/ایمیل/Browser — هشدارهای پراپ (نزدیک DD، deadline، Payout) |
| ۲ | **Excel Export** | 🟡 متوسط | `openpyxl` موجود؛ مفید برای گزارش‌های رسمی |
| ۳ | **Heatmap تقویم** | 🟡 متوسط | دید سریع روزهای خوب/بد |
| ۴ | **AI Journal Assistant** | 🟡 متوسط | تحلیل `rule_violations` و تشخیص revenge trading |
| ۵ | **Trade Playback** | 🟢 کم | مرور بصری معاملات |
| ۶ | **Monte Carlo** | 🟢 کم | ارزیابی ریسک ورشکستگی استراتژی |

### ۱۴.۲ بهبودها

| # | بهبود | اولویت | توضیح |
|---|---|---|---|
| ۱ | **Restore endpoint** | 🔴 بالا | `POST /api/trades/{id}/restore` — تکمیل چرخهٔ soft delete |
| ۲ | **نمایش «حذف‌شده‌ها»** | 🔴 بالا | فیلتر `include_deleted` + دکمهٔ بازگردانی در `TradesPage` |
| ۳ | **Coverage تست** | 🟠 بالا | رساندن به >۷۰٪؛ شروع از `analytics` (کم‌پوشش‌ترین) + یک E2E |
| ۴ | **یکنواخت‌سازی Loading** | 🟡 متوسط | استفاده از `Skeleton` در همهٔ صفحات (الان فقط Dashboard) |
| ۵ | **رفع باقی‌ماندهٔ Dark Mode** | 🟡 متوسط | `DashboardPage.tsx:378,413-425`, `ComparisonPage.tsx:568,572` |
| ۶ | **`BLUEPRINT_STATUS.md`** | 🟡 متوسط | ساخت/به‌روزرسانی سند وضعیت بلوپرینت |
| ۷ | **به‌روزرسانی `NOTES.md`** | 🟢 کم | هنوز وضعیت فاز ۱-۱۰ قدیمی را نشان می‌دهد |
| ۸ | **آرشیو مستندات قدیمی** | 🟢 کم | `ANALYSIS.md`, `SUGGESTIONS.md`, `REMAINING_BLUEPRINT_ITEMS.md` (منسوخ) |
| ۹ | **PWA / Mobile** | 🟡 متوسط | منیفست + service worker برای نصب روی موبایل |
| ۱۰ | **Dockerize** | 🟢 کم | `Dockerfile` + `docker-compose` |
| ۱۱ | **CI/CD** | 🟢 کم | GitHub Actions: `pytest` + `tsc` + `vitest` + `build` |

### ۱۴.۳ امنیت

| # | اقدام | اولویت |
|---|---|---|
| ۱ | **Authentication (JWT یا API-Key)** | 🔴 بالا (اگر سرور روی شبکه) |
| ۲ | **Multi-User** | 🟡 متوسط — نیاز به `user_id` روی همهٔ جداول |
| ۳ | **ماسک `card_number`** در API | 🟠 بالا |
| ۴ | **auth روی `/storage/*`** | 🟠 بالا |
| ۵ | **HTTPS + SECRET_KEY واقعی** | 🟠 بالا (در صورت دسترسی خارجی) |

### ۱۴.۴ پرفرمنس

| # | اقدام | اولویت | توضیح |
|---|---|---|---|
| ۱ | **Caching (Redis/lru_cache)** | 🟡 متوسط | کش `AnalysisResult` |
| ۲ | **Background Tasks** | 🟡 متوسط | Import بزرگ + تحلیل سنگین به‌صورت async |
| ۳ | **WAL Mode برای SQLite** | 🟡 متوسط | `PRAGMA journal_mode=WAL` |
| ۴ | **Index تکمیلی** | 🟢 کم | `trades(version_id)`, `trades(prop_stage_id)`, `trades(close_time)` |
| ۵ | **Virtual Scrolling** | 🟢 کم | جدول معاملات با >۱۰۰۰ ردیف |

### ۱۴.۵ معماری

| # | اقدام | توضیح |
|---|---|---|
| ۱ | **`response_model` برای همهٔ endpointها** | مستندات OpenAPI کامل + جلوگیری از نشت فیلد (`raw_data`) |
| ۲ | **API Versioning** (`/api/v1/`) | آمادگی برای breaking changes |
| ۳ | **Pydantic strict** | `model_config = ConfigDict(strict=True)` در schemaهای حساس |
| ۴ | **از `on_event` به `lifespan`** | رفع `DeprecationWarning`های FastAPI |
| ۵ | **از `declarative_base()` به `DeclarativeBase`** | رفع `MovedIn20Warning` در SQLAlchemy 2 |
| ۶ | **یکپارچه‌سازی `not_deleted_filter()`** | جایگزینی `Trade.is_deleted == False` مستقیم با helper |

---

## ۱۵. پیوست‌ها

### ۱۵.۱ فهرست کامل گزارش‌های فاز

| فایل | عنوان |
|---|---|
| `PHASE6_DARKMODE_REPORT.md` | Dark Mode در Personal/Prop |
| `PHASE6_1_DARKMODE_CHILDREN_REPORT.md` | Dark Mode کامپوننت‌های فرزند |
| `PHASE7_DARKMODE_REPORT.md` | Dark Mode کامل + حذف App.css |
| `PHASE8_DARKMODE_REPORT.md` | Dark Mode ۸ صفحهٔ باقی‌مانده |
| `PHASE9_REPORT.md` | ادغام دو دفتر کل (Personal → Finance) |
| `PHASE10_REPORT.md` | تکمیل UI معاملهٔ دستی (فیلد حساب مالی) |
| `PHASE11_REPORT.md` | گزارش‌های پیشرفتهٔ مالی |
| `PHASE12_REPORT.md` | Testing Suite |
| `PHASE13_REPORT.md` | بهبودهای UX |
| `PHASE14_1_REPORT.md` | رفع باگ‌ها + نمودارهای پایه |
| `PHASE14_2_REPORT.md` | ترتیب جدید + کارت روز گذشته + ویجت مالی |
| `PHASE14_3_REPORT.md` | فیلتر بازهٔ زمانی + جدول معاملات |
| `PHASE14_4_REPORT.md` | آمار ریسک پیشرفته |
| `PHASE14_5_REPORT.md` | Empty State، Refresh، Quick Actions |
| `PHASE15_1_REPORT.md` | رفع باگ‌های P0 |
| `PHASE15_2_REPORT.md` | رفع N+1 + Rate Limiting |
| `PHASE15_3_REPORT.md` | پرفرمنس Dashboard با SQL Aggregation |
| `PHASE15_4_REPORT.md` | Bundle Splitting (Frontend) |
| `PHASE15_5_7_10_REPORT.md` | پاکسازی‌ها (۵+۷+۸+۹+۱۰) |
| `PHASE15_11_12_REPORT.md` | Withdrawals (۱۵.۱۱ + ۱۵.۱۲) |
| `PHASE16_REPORT.md` | Payout History |
| `PHASE17_REPORT.md` | Backup خودکار و دستی |
| `PHASE18_REPORT.md` | محافظت خودکار دیتابیس (Auto-Migrate) |
| `PHASE19_REPORT.md` | جداسازی معاملات REAL از تحلیل استراتژی |
| `PHASE20_DESIGN.md` | طراحی تحلیل ۶گانه |
| `PHASE20_REPORT.md` | تحلیل ۶گانه + Tab bar + داشبورد پول واقعی |
| `PHASE21_REPORT.md` | Finance Bridge |
| `PHASE22_REPORT.md` | گزارش‌های مالی |
| `PHASE23_REPORT.md` | استقلال تحلیل |
| `PHASE24_REPORT.md` | بهبود کامل Fork |
| `PHASE25_REPORT.md` | Soft Delete + حذف گروهی |
| `PHASE25_PART2_REPORT.md` | رفع فیلترهای `is_deleted` در پراپ/مالی/تحلیل/گزارش |

### ۱۵.۲ سایر اسناد

| فایل | موضوع |
|---|---|
| `COMPREHENSIVE_REVIEW.md` | بررسی جامع (۷۸ مسیر در زمان نگارش، ۲۷ یافته) |
| `SUGGESTIONS.md` | پیشنهادات تکمیلی (۵۵۹ خط) |
| `ANALYSIS.md` | تحلیل جامع اولیه |
| `REMAINING_BLUEPRINT_ITEMS.md` | موارد باقی‌ماندهٔ بلوپرینت (منسوخ) |
| `CLEANUP_REPORT.md` | گزارش پاک‌سازی |
| `FINANCE_PHASE1_REPORT.md` | ماژول مالی — فاز ۱ |
| `PROP_FINANCE_INTEGRATION*.md` | طراحی/گزارش یکپارچگی پراپ↔مالی |
| `STRATEGY_PROP_ANALYSIS.md` / `STRATEGY_PROP_IMPROVEMENTS.md` | تحلیل/بهبود استراتژی و پراپ |
| `SPRINT4-5 / 6 / 7 / 9 / 10_REPORT.md` | گزارش Sprintها |
| `MokTradeDesk-1.md` / `MokTradeDesklast-bluprint-2.md` / `MokTradeDesk-3..md` | اسناد Handoff اولیه |
| `NOTES.md` | یادداشت وضعیت (قدیمی) |
| `FINAL_BLUEPRINT.md` | **این سند** |

### ۱۵.۳ آمار نهایی

| شاخص | مقدار |
|---|---|
| فازها | ۲۵ (+۶ Sprint) |
| endpointها | ۱۰۸ مسیر / ۱۳۷ عملیات |
| صفحات Frontend | ۱۳ |
| کامپوننت‌ها | ۳۱ |
| مدل‌ها | ۲۱ |
| Migrationها | ۸ |
| تست بک‌اند | ۹۰ |
| تست فرانت | ۹ |
| گزارش‌ها | ۳۲ فایل `PHASE*` + ۲۰ سند |

### ۱۵.۴ لینک‌ها

| منبع | آدرس |
|---|---|
| API Docs (لوکال) | `http://localhost:8000/docs` |
| ReDoc (لوکال) | `http://localhost:8000/redoc` |
| UI (لوکال) | `http://localhost:5173` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |
| Backupها | `backend/backups/` |
| لاگ‌ها | `logs/` |
| اسکرین‌شات‌ها | `backend/storage/screenshots/` |

> **نکته:** این پروژه یک مخزن محلی است و لینک GitHub عمومی برای آن ثبت نشده؛ برای انتقال به مخزن، از `git remote add origin <url>` استفاده کنید.

---

## 🏁 جمع‌بندی

**MokTradeDesk** در وضعیت **کامل و سالم** قرار دارد: ۲۵ فاز پیاده‌سازی شده، ۱۰۸ مسیر API، ۱۳ صفحهٔ هوشمند، ۹۰ تست بک‌اند و ۹ تست فرانت همه پاس، build بدون خطا.

| ✅ قوت‌ها | ⚠️ بدهی‌های فنی |
|---|---|
| معماری تمیز Router/Service/Model | نبود Authentication (Local-First) |
| Trade Classification Contract محکم (XOR) | پوشش تست ~۷۰٪ (پیشنهاد: افزایش) |
| Soft Delete یکپارچه در همهٔ کوئری‌ها | مستندات قدیمی متناقض (`NOTES.md`, `REMAINING_BLUEPRINT_ITEMS.md`) |
| Multi-scope Analysis (۶ دامنه) | Restore endpoint ندارد |
| Dark Mode اصولی (CSS Variables) | باقی‌ماندهٔ رنگ‌های هاردکد Dark Mode |
| Backup خودکار + Auto-Migrate | ماسک `card_number` تأییدنشده |
| SQL Aggregation + Bundle Splitting | — |

> **مسیر پیشنهادی بعدی:** (۱) Restore + UI حذف‌شده‌ها → (۲) گسترش تست‌ها → (۳) Notifications → (۴) Authentication در صورت نیاز شبکه‌ای.

---

*این بلوپرینت بر اساس بازخوانی مستقیم کدِ واقعی، `git log`، ۳۲ گزارش فاز و ۲۰ سند پروژه تهیه شده است — نه بر اساس مستندات منسوخ.*
*نسخه ۱.۰ — ۱۴۰۵/۰۷/۰۵ (2026-09-27)*














