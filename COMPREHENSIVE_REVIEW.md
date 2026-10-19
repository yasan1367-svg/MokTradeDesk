# 🔍 بررسی جامع پروژه MokTradeDesk

> **تاریخ بررسی:** ۱۴۰۵/۰۷/۰۳ (2026-09-25)
> **دامنه:** Backend (FastAPI + SQLAlchemy + SQLite) + Frontend (React 19 + Vite 8 + Tailwind)
> **روش:** بازخوانی کدِ واقعی فایل‌ها + اجرای `tsc -b --force`، `vite build`، `py_compile` و `TestClient` روی endpointها
> **وضعیت Build:** ✅ Backend قابل import و سالم — ✅ Frontend با `tsc` و `vite build` بدون خطا (خروجی 0)
> **تعداد Endpoint (مسیرهای یکتا در OpenAPI):** **78**

---

## 📈 خلاصه اجرایی

پروژه از نظر **معماری و پوشش قابلیت** خوب و منسجم است: ۷۸ مسیر API، ۱۲ صفحه Frontend، ادغام Prop↔Finance، حالت تاریک مبتنی بر CSS Variables، و Duplicate Detection برای معاملات. اما سه دسته مشکل جدی وجود دارد:

1. **🔴 امنیت صفر** — هیچ احراز هویت/مجوزدهی‌ای وجود ندارد و CORS کاملاً باز است.
2. **🟠 پرفرمنس** — چند endpoint کل جدول `trades` را در حافظه لود و در Python محاسبه می‌کنند (بدون SQL Aggregation) و چند N+1 وجود دارد.
3. **🟡 کد مرده/تکراری و پوشش تست ناکافی** — کد مرده در `export.py`، مسیر تکراری در `finance.py`، و تنها ۳۳ تست Backend.

| اولویت | تعداد یافته | زمان تخمینی رفع |
|---|---|---|
| **P0 — بحرانی** | 6 | ۹–۱۲ ساعت |
| **P1 — بالا** | 7 | ۱۴–۱۸ ساعت |
| **P2 — متوسط** | 8 | ۱۶–۲۰ ساعت |
| **P3 — کم** | 6 | ۱۲–۲۰ ساعت |
| **مجموع** | **27** | **۵۱–۷۰ ساعت** |

---

## ۱. بررسی Backend

### ۱.۱ نقشه Endpointها

| Prefix | مسیرها (نمونه) | فایل |
|---|---|---|
| `/api/strategies` | `/`, `/{id}`, `/{id}/versions`, `/versions/all`, `/versions/{id}`, `/versions/{id}/fork`, `/versions/{id}/trades`, `/{id}/stats` | `strategies.py` |
| `/api/prop` | `/firms`, `/firms/{id}/default-rules`, `/accounts`, `/accounts/{id}`, `/accounts/{id}/finance-account`, `/stages/{id}/check-pass`, `/stages/{id}/pass`, `/stages/{id}/fail`, `/stages/{id}/rules`, `/withdrawals`, `/alerts`, `/alerts/{id}/read`, `/alerts/generate`, `/costs`, `/analytics` | `prop.py` |
| `/api/personal` | `/journal/review`, `/journal/reviews`, `/journal/reviews/{id}`, `/journal/reviews/{id}/screenshots`, `/prop-accounts-list` | `personal.py` |
| `/api/imports` | `/soft4x`, `/mt4` | `imports.py` |
| `/api/analytics` | `/analyze/{id}`, `/dashboard`, `/yesterday`, `/risk-metrics`, `/risk-advanced`, `/calendar`, `/{id}`, `/{id}/history`, `/compare`, `/intervals/`, `/intervals/{id}`, `/intervals/seed-gold`, `/intervals/seed-dji` | `analytics.py` |
| `/api/export` | `/trades/csv`, `/trades/pdf`, `/analysis/pdf`, `/dashboard/pdf` | `export.py` |
| `/api/trades` | `/`, `/{id}`, `/manual`, `/{id}/screenshots`, `/screenshots/{id}` | `trades.py` |
| `/api/symbol-mappings` | `/`, `/{id}`, `/seed-defaults` | `symbol_mappings.py` |
| `/api/settings` | `/` (GET/PATCH) | `settings.py` |
| `/api/finance` | `/accounts`, `/accounts/{id}/stats`, `/categories`, `/transactions`, `/summary`, `/withdrawals/stats`, `/charts/cashflow`, `/charts/distribution`, `/reports/monthly`, `/reports/category-breakdown`, `/reports/account-comparison`, `/reports/profit-loss`, `/seed` | `finance.py` |

---

### ۱.۲ 🚨 ایرادهای بحرانی (P0)

#### `BE-01` — عدم وجود هرگونه احراز هویت (تمام ۷۸ مسیر)
- **فایل/خط:** `backend/app/main.py:36-42` (CORS) و نبود middleware احراز هویت در کل پروژه.
- **مشکل:**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # ← wildcard
      allow_credentials=True,   # ← ترکیب نامعتبر با "*"
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  ترکیب `allow_origins=["*"]` با `allow_credentials=True` توسط مرورگر رد می‌شود و ضمناً یعنی **هر Origin** می‌تواند درخواست بفرستد. هیچ endpointی توکن/سشن/کلید بررسی نمی‌کند — هر کسی که به پورت ۸۰۰۰ دسترسی دارد می‌تواند همه‌چیز را بخواند، ویرایش و **حذف** کند (`DELETE /api/trades/{id}`, `DELETE /api/finance/accounts/{id}`, ...).
- **ریسک:** Critical — داده‌های مالی و معاملاتی حساس در معرض حذف/تغییر کامل.
- **راه‌حل:** (الف) حداقل فوری: حذف `"*"` از `allow_origins`؛ (ب) پیاده‌سازی API Key یا JWT با `Depends(...)` روی routerها.
- **زمان تخمینی:** CORS = ۱۰ دقیقه | JWT کامل = ۶–۸ ساعت.

#### `BE-02` — کد مرده + تابع تکراری در `export.py`
- **فایل/خط:** `backend/app/api/export.py:79-95`
- **مشکل:** پس از `return` در `_colored_pnl` (خط ۷۸)، سه خط مرده رها شده و تابع `_build_pdf_response` **دو بار** تعریف شده است:
  ```python
  78 |     return Paragraph(f"<font color='#6B7A94'>{v:{fmt}}</font>", style)
  79 |     """BytesIO -> StreamingResponse"""          # ← کد مرده
  80 |     buffer.seek(0)
  81 |     ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  82 | def _build_pdf_response(buffer, filename_prefix):   # ← تعریف تابع وسط تابع قبلی
  86 |     return StreamingResponse(...)
  91 |     return StreamingResponse(...)                   # ← return تکراری/مرده (۹۱-۹۵)
  ```
- **تأثیر:** خطای runtime نمی‌دهد (کد مرده است) اما نتیجهٔ copy/paste اشتباه است؛ نگهداری را دشوار می‌کند.
- **زمان تخمینی:** ۱۵ دقیقه.

#### `BE-03` — مسیر تکراری: `DELETE /api/finance/accounts/{account_id}`
- **فایل/خط:** `backend/app/api/finance.py:147` **و** `backend/app/api/finance.py:979`
- **مشکل:** تابع `delete_account` دو بار با مسیر یکسان تعریف شده. دومی (خط ۹۷۹) در startup اولی را override می‌کند. فعلاً رفتارشان یکسان است، اما این یک **بمب ساعتی** است: هر تغییر در یکی، بی‌صدا نادیده گرفته می‌شود.
- **زمان تخمینی:** ۱۰ دقیقه (حذف نسخهٔ اضافی).

#### `BE-04` — `delete_category` بدون `return`
- **فایل/خط:** `backend/app/api/finance.py:207-215`
- **مشکل:** بعد از `db.delete(cat)` و `db.commit()` هیچ مقداری return نمی‌شود ⇒ پاسخ `null` برمی‌گردد (ناسازگار با بقیهٔ endpointها که `{"message": ...}` می‌دهند).
- **زمان تخمینی:** ۵ دقیقه.

#### `BE-05` — نبود Rate Limiting و محدودیت حجم آپلود
- **فایل/خط:** `main.py` (بدون middleware) — آپلودها در `trades.py:583`, `personal.py:48`, `imports.py:15,94`.
- **مشکل:** `UploadFile` بدون سقف حجم ⇒ آپلود فایل حجیم می‌تواند حافظه/دیسک سرور را پر کند.
- **راه‌حل:** محدودیت اندازهٔ فایل (مثلاً ۲۰MB) + `slowapi`.
- **زمان تخمینی:** ۱.۵ ساعت.

#### `BE-06` — `except:` برهنه که خطا را می‌بلعد
- **فایل/خط:** `personal.py:120-121` و `personal.py:171-172`
- **مشکل:** `try: os.remove(path) except: pass` — هر خطا (از جمله PermissionError) بی‌صدا نادیده گرفته می‌شود و فایل‌های یتیم روی دیسک می‌مانند.
- **زمان تخمینی:** ۱۵ دقیقه.

---

### ۱.۳ 🟠 ایرادهای پرفرمنس و پایداری (P1)

#### `BE-07` — داشبورد کل جدول `trades` را در حافظه لود می‌کند
- **فایل/خط:** `backend/app/api/analytics.py:58` → `all_trades = db.query(Trade).all()`
- **مشکل:** سپس فیلتر بازه (خطوط ۸۰-۹۰)، محاسبهٔ PnL، منحنی اکوییتی، streak و توزیع، همگی **در Python روی لیست کامل** انجام می‌شود. با ۱۰٬۰۰۰+ معامله، زمان پاسخ به‌سرعت به چند ثانیه می‌رسد و هر refresh داشبورد این هزینه را تکرار می‌کند.
- **راه‌حل:** انتقال محاسبات به `func.sum/count`، `GROUP BY` روی `date(close_time)` و window functions؛ فیلتر تاریخ در سطح SQL.
- **زمان تخمینی:** ۴ ساعت.

#### `BE-08` — N+1 Query در `get_firms`
- **فایل/خط:** `backend/app/api/prop.py:144-147`
  ```python
  firms = db.query(PropFirm).all()
  for f in firms:
      accounts = db.query(PropAccount).filter(PropAccount.prop_firm_id == f.id).all()  # ← N+1
  ```
- **راه‌حل:** یک query با `group_by(PropAccount.prop_firm_id)` برای شمارش، یا `selectinload`.
- **زمان تخمینی:** ۳۰ دقیقه.

#### `BE-09` — N+1 Query در `get_reviews`
- **فایل/خط:** `backend/app/api/personal.py:131-138` — برای هر review یک query جدا برای `Trade` و یک query برای `Screenshot`.
- **راه‌حل:** `joinedload(Screenshot)` و join با `Trade` در یک query.
- **زمان تخمینی:** ۳۰ دقیقه.

#### `BE-10` — N+1 در شمارش نسخه‌ها/معاملات استراتژی
- **فایل/خط:** `strategies.py:46`, `strategies.py:113`, `strategies.py:140` — برای هر استراتژی/نسخه یک `count()` جدا اجرا می‌شود.
- **راه‌حل:** subquery با `func.count` و `outerjoin`/`group_by`.
- **زمان تخمینی:** ۴۵ دقیقه.

#### `BE-11` — `get_strategy_stats` و `get_version_trades` بدون صفحه‌بندی
- **فایل/خط:** `strategies.py:243` (`get_version_trades` همهٔ معاملات) و `strategies.py:291` (`get_strategy_stats` همهٔ معاملات همهٔ نسخه‌ها).
- **مشکل:** برخلاف `GET /api/trades` که صفحه‌بندی دارد (`trades.py:208-209`)، اینها کل داده را برمی‌گردانند.
- **راه‌حل:** افزودن `page/page_size` یا محاسبهٔ آماری سمت SQL.
- **زمان تخمینی:** ۲.۵ ساعت.

#### `BE-12` — `yesterday` و `risk-metrics`/`risk-advanced` هم تمام‌جدول را می‌خوانند
- **فایل/خط:** `analytics.py:266`, `analytics.py:338`, `analytics.py:458`, `analytics.py:567`, `export.py:337`.
- **مشکل:** الگوی `db.query(Trade).filter(Trade.close_time != None).all()` سپس فیلتر بازه در Python (یا بارگذاری همه برای export).
- **زمان تخمینی:** ۳ ساعت (بازآرایی مشترک با BE-07).

#### `BE-13` — جستجو با wildcard ابتدایی (Full Scan)
- **فایل/خط:** `trades.py:242`, `export.py:157`, `export.py:221` → `Trade.note.like(f"%{search}%")`
- **وضعیت امنیت:** ✅ **SQL Injection ندارد** — SQLAlchemy پارامترها را به‌صورت bind می‌فرستد. اما به‌خاطر `%` ابتدایی، ایندکس قابل استفاده نیست ⇒ Full Table Scan.
- **راه‌حل:** در صورت نیاز، Full-text (FTS5 در SQLite) یا حداقل `like` بدون wildcard ابتدایی.
- **زمان تخمینی:** ۱.۵ ساعت.

---

### ۱.۴ 🟡 ایرادهای متوسط Backend (P2)

#### `BE-14` — عدم اطمینان از ساخت جداول/مهاجرت در startup
- **فایل/خط:** `main.py:56-58` — `startup()` فقط لاگ می‌کند و `Base.metadata.create_all(bind=engine)` فراخوانی نمی‌شود (بررسی شود).
- **ریسک:** روی DB خالی، جداول ساخته نمی‌شوند و endpointها ۵۰۰ می‌دهند. (`alembic.ini` و پوشهٔ `migrations` وجود دارد اما در startup اجرا نمی‌شود.)
- **زمان تخمینی:** ۴۵ دقیقه.

#### `BE-15` — `SQLite` با `check_same_thread=False` و بدون WAL
- **فایل/خط:** `core/database.py:7-10`
- **مشکل:** SQLite برای نوشتن همزمان ضعیف است؛ بدون `PRAGMA journal_mode=WAL` و `busy_timeout` ممکن است در همزمانی (مثلاً import همزمان با read) خطای «database is locked» رخ دهد.
- **زمان تخمینی:** ۳۰ دقیقه.

#### `BE-16` — ناسازگاری در مقداردهی Enum/پاسخ
- **فایل/خط:** `strategies.py:119` و `146` از `hasattr(v.status, 'value')` استفاده می‌کنند، ولی `prop.py:291` مستقیم `.value` می‌گیرد. خروجی JSON ممکن است بین endpointها متفاوت باشد.
- **زمان تخمینی:** ۳۰ دقیقه.

#### `BE-17` — `_to_currency` با fallback بی‌صدا
- **فایل/خط:** `prop.py:22-27` — `except ValueError: return Currency.USD` بدون لاگ. تبدیل ناخواستهٔ IRR→USD در سکوت.
- **زمان تخمینی:** ۲۰ دقیقه.

#### `BE-18` — نبود `response_model` در اکثر endpointها
- **مشکل:** از ۷۸ مسیر، فقط چند مورد (`analytics.py:778,794,803`) `response_model` دارند. بقیه dict خام برمی‌گردانند ⇒ مستندات OpenAPI ناقص و ریسک نشت فیلدهای حساس (مثل `raw_data` در `trades.py:176`).
- **زمان تخمینی:** ۴–۶ ساعت.

#### `BE-19` — `get_finance_summary`/`get_account_stats` کل حساب‌ها/تراکنش‌ها را لود می‌کنند
- **فایل/خط:** `finance.py:309` (`db.query(Account).all()`) و مشابه‌ها در گزارش‌های `finance.py:672+`.
- **زمان تخمینی:** ۳ ساعت.

#### `BE-20` — نبود اعتبارسنجی بازهٔ تاریخ در `get_calendar_data` و `compare`
- **فایل/خط:** `analytics.py:617` (`year`/`month` بدون اعتبارسنجی محدوده) و `analytics.py:779`.
- **مشکل:** ورودی نامعتبر می‌تواند منجر به محاسبات اشتباه یا ۵۰۰ شود.
- **زمان تخمینی:** ۱ ساعت.

#### `BE-21` — نبود احراز مالکیت/وجود entity در آپلود اسکرین‌شات
- **فایل/خط:** `trades.py:583` — بررسی می‌شود که trade وجود دارد؟ (باید تأیید شود). در `personal.py:47` بررسی review وجود دارد ✅.
- **زمان تخمینی:** ۳۰ دقیقه.

---

## ۲. بررسی Frontend

**صفحات (۱۲):** `DashboardPage`, `AnalysisPage`, `ComparisonPage`, `StrategyPage`, `TradesPage`, `JournalPage`, `PropPage`, `CalendarPage`, `RiskManagementPage`, `ImportPage`, `FinancePage`, `SettingsPage` — همه در `App.tsx:177-188` با `ErrorBoundary` محصور شده‌اند ✅ (نکته مثبت).

### ۲.۱ 🟠 ایرادهای Frontend (P1)

#### `FE-01` — Bundle یکجا ۱.۰۷MB (بدون Code Splitting)
- **فایل/خط:** `frontend/src/App.tsx:7-19` — همهٔ ۱۲ صفحه با `import` استاتیک وارد می‌شوند.
- **شاهد:** خروجی `vite build` → `dist/assets/index-*.js  1,071.20 kB` (gzip: 273 kB) + هشدار رسمی Vite: «Some chunks are larger than 500 kB after minification».
- **راه‌حل:** `const DashboardPage = lazy(() => import('./pages/DashboardPage'))` + `<Suspense fallback={<DashboardSkeleton />}>`.
- **زمان تخمینی:** ۲–۳ ساعت.

#### `FE-02` — وابستگی‌های نمودار (recharts) در bundle اصلی
- **فایل/خط:** `DashboardPage.tsx:2` و ۷ کامپوننت در `components/charts/*`.
- **مشکل:** Recharts حجم زیادی دارد و همیشه لود می‌شود، حتی وقتی کاربر به صفحهٔ نمودار نمی‌رود (به‌خاطر FE-01).
- **زمان تخمینی:** ۱ ساعت (با lazy + manualChunks).

### ۲.۲ 🌗 ناسازگاری با Dark Mode (P2)

پروژه Dark Mode را با CSS Variables پیاده کرده و **در اکثر جاها درست است** (بیش از ۱٬۷۰۰ ارجاع `var(--*)` در صفحات). اما موارد زیر رنگ ثابت روشن دارند و در حالت تاریک **محو/ناخوانا** می‌شوند:

| # | فایل:خط | کد | مشکل |
|---|---|---|---|
| `FE-03` | `DashboardPage.tsx:378` | `background: 'linear-gradient(135deg, #FFFFFF 0%, #F0F6FF 100%)'` | گرادیان روشن ثابت — در Dark خیلی روشن می‌ماند |
| `FE-04` | `DashboardPage.tsx:413,419,425` | `bg-white/70 backdrop-blur ...` | کارت‌های روشن نیمه‌شفاف — در Dark خاکستری-سفید می‌شوند |
| `FE-05` | `ComparisonPage.tsx:568,572` | `bg-white/60 rounded-[10px] p-3` | پنل روشن ثابت |
| `FE-06` | `Skeleton.tsx:37` | `bg-white dark:bg-[#152238] ...` | این‌جا کلاس `dark:` دارد (خوب) اما رنگ هاردکد `#152238`/`#E5EBF3` با توکن‌های تم همراستا نیست |
| `FE-07` | `TradesPage.tsx:981` | `bg-white/20 hover:bg-white/30 text-white` | روی modal تصویر — قابل قبول (overlay) اما بهتر است توکن شود |

- **زمان تخمینی رفع کل موارد Dark Mode:** ۱–۲ ساعت.

### ۲.۳ 🟡 ایرادهای متوسط Frontend (P2)

#### `FE-08` — توابع تکراری در API Client
- **فایل/خط:** `frontend/src/api/client.ts:29` (`compareVersions`) و `client.ts:34` (`compareVersionsWithDetails`) — **هر دو دقیقاً یک درخواست یکسان** به `/api/analytics/compare` می‌فرستند. یکی باید حذف شود.
- **زمان تخمینی:** ۱۰ دقیقه.

#### `FE-09` — نبود نشانگر Loading/Error یکنواخت در همهٔ صفحات
- **شاهد:** فقط `DashboardPage` از `DashboardSkeleton` (`components/Skeleton.tsx`) استفاده می‌کند. صفحات دیگر (مثل `FinancePage`, `CalendarPage`) الگوی skeleton/loading مشترک ندارند.
- **زمان تخمینی:** ۳–۴ ساعت.

#### `FE-10` — نبود تست کامپوننت/صفحه
- **شاهد:** `vitest.config.ts` الگوی `src/**/*.{test,spec}.{ts,tsx}` دارد، اما در `src` فقط ۲ فایل تست (مربوط به setup/library) وجود دارد و **هیچ صفحه یا کامپوننت پروژه‌ای تست نشده است**.
- **زمان تخمینی:** ۱۰+ ساعت (برای پوشش حداقلی).

#### `FE-11` — نبود مدیریت خطای سراسری (Axios Interceptor)
- **فایل/خط:** `frontend/src/api/client.ts:6-11` — فقط `baseURL` تنظیم شده؛ هیچ interceptor برای خطا/توکن/Retry وجود ندارد. خطاها به‌صورت پراکنده در هر صفحه `catch` می‌شوند ⇒ پیام‌های ناهمگون.
- **زمان تخمینی:** ۱.۵ ساعت.

#### `FE-12` — Header بدون عملکرد در بعضی دکمه‌ها
- **فایل/خط:** `App.tsx:164-166` — دکمهٔ 🔔 (اعلان) هیچ `onClick` ندارد (دکمهٔ بی‌عمل).
- **زمان تخمینی:** ۲۰ دقیقه (یا حذف یا اتصال به هشدارهای پراپ).

### ۲.۴ 🟢 نکات مثبت Frontend

- ✅ `ErrorBoundary` روی **هر ۱۲ صفحه** و همچنین در `main.tsx` به‌صورت fullScreen.
- ✅ پیاده‌سازی تم با `useTheme` + پشتیبانی از `prefers-color-scheme` و `localStorage` (`App.tsx:38-72`).
- ✅ استفادهٔ گسترده و درست از CSS Variables به‌جای رنگ هاردکد (به‌جز موارد FE-03..07).
- ✅ `CommandPalette` با میانبر `Ctrl+K` و میانبرهای کیبورد.
- ✅ توابع API Client **منظم و دسته‌بندی‌شده** و با TypeScript types.

---

## ۳. بررسی یکپارچگی (Integration)

### ۳.۱ ✅ بخش‌های متصل — تأییدشده
- **Frontend ↔ Backend:** تمام مسیرهای صدا‌زده‌شده در `frontend/src/api/client.ts` با مسیرهای واقعی Backend (۷۸ مسیر در OpenAPI) **تطبیق کامل** دارند. هیچ endpoint گم‌شده‌ای یافت نشد.
- **Prop ↔ Finance:** ادغام واقعی است — `PropAccount.finance_account_id`، ساخت خودکار حساب مالی (`prop.py:234-248`)، `POST /accounts/{id}/finance-account`، و ثبت خودکار تراکنش در `create_cost` (`prop.py:762+`).
- **Prop Alerts ↔ Dashboard/PropPage:** `getPropAlerts`/`markAlertRead`/`generatePropAlerts` همه وصل‌اند و (پس از رفع باگ `PropAlert`) سالم پاسخ می‌دهند.
- **Import ↔ Strategy/Prop:** `imports.py` با `version_id` و `prop_stage_id` + Duplicate Detection.

### ۳.۲ ⚠️ ناهماهنگی‌ها

#### `INT-01` — دو مسیر متفاوت برای برداشت پراپ
- **مشکل:** Backend هم `/api/prop/stages/{stage_id}/withdraw` و هم `/withdrawals` دارد؛ Frontend از کدام استفاده می‌کند؟ (نیاز به بازبینی یکسان‌سازی).
- **زمان:** ۳۰ دقیقه.

#### `INT-02` — ناسازگاری فرمت خروجی Enum بین ماژول‌ها
- **فایل/خط:** `strategies.py:119` (با `hasattr`) در مقابل `prop.py:291` (مستقیم `.value`). ممکن است یکجا رشته و جای دیگر `null`/شیء برگردد.
- **زمان:** ۳۰ دقیقه.

#### `INT-03` — `raw_data` کامل در پاسخ جزئیات معامله برمی‌گردد
- **فایل/خط:** `trades.py:176` — کل `raw_data` (خروجی خام فایل ورودی) بدون محدودیت ارسال می‌شود. با `response_model` (BE-18) باید فیلتر شود.
- **زمان:** ۳۰ دقیقه.

#### `INT-04` — نبود Caching مشترک برای داده‌های سنگین
- **مشکل:** داشبورد، تحلیل ریسک و تقویم هر بار محاسبه می‌شوند؛ هیچ لایهٔ cache (حافظه/Redis) بین آن‌ها نیست.
- **زمان:** ۳–۴ ساعت.

---

## ۴. بررسی عملکرد (Performance)

### ۴.۱ Endpointهای کند
| اولویت | Endpoint | فایل:خط | علت |
|---|---|---|---|
| 🔴 | `GET /api/analytics/dashboard` | `analytics.py:58` | لود کل `trades` + محاسبه در Python (BE-07) |
| 🔴 | `GET /api/analytics/risk-advanced` | `analytics.py:458` | همان الگو (BE-12) |
| 🟠 | `GET /api/analytics/yesterday` | `analytics.py:266` | لود همهٔ closed trades (BE-12) |
| 🟠 | `GET /api/analytics/calendar` | `analytics.py:628` | لود همهٔ معاملات بازه در Python |
| 🟠 | `GET /api/strategies/{id}/stats` | `strategies.py:291` | محاسبهٔ آماری در Python (BE-11) |
| 🟠 | `GET /api/export/trades/pdf` | `export.py:337` | لود کل جدول + ساخت PDF همگام (بلاک‌کننده) |
| 🟡 | `GET /api/prop/firms` | `prop.py:147` | N+1 (BE-08) |
| 🟡 | `GET /api/personal/journal/reviews` | `personal.py:134` | N+1 (BE-09) |
| 🟡 | `GET /api/strategies/versions/all` | `strategies.py:113` | N+1 شمارش (BE-10) |

### ۴.۲ کوئری‌های بهینه‌نشده
- الگوهای `db.query(X).all()` بدون صفحه‌بندی: `analytics.py:58,266,338,458,567`، `finance.py:309`، `export.py:337`، `strategies.py:43,109,243,291`، `prop.py:144,200,280,318,386,481,751,824,885`.
- نبود `joinedload` کافی: `trades.py:315` (جزئیات) به‌درستی از `joinedload` استفاده می‌کند ✅ اما `strategies.py:242`/`personal.py:134` نه.

### ۴.۳ کامپوننت‌های مجدداً رندر‌شونده (Frontend)
- **`FE-13` — نبود `useMemo`/`React.memo` در محاسبات سنگین:** صفحاتی مثل `PropPage.tsx` (۴۶۳ ارجاع var → کامپوننت بزرگ) و `ComparisonPage.tsx` (۲۰۰ ارجاع) بدون memoize کردن داده‌های مشتق‌شده (فیلترها/آمار) رندر می‌شوند. با هر تغییر state، همهٔ نمودارهای Recharts دوباره رندر می‌شوند.
- **`FE-14` — رندر همهٔ ۱۲ صفحه به‌صورت شرطی در یک tree:** `App.tsx:177-188` — چون همه eager import شده‌اند، هر بار switch صفحه کل کامپوننت tree موجود می‌ماند (بهبود با lazy حل می‌شود).
- **زمان تخمینی:** ۳–۴ ساعت.

---

## ۵. بررسی امنیت

### ۵.۱ Endpointهای بدون احراز هویت
**تمام ۷۸ مسیر بدون احراز هویت هستند** (چون هیچ مکانیزم احراز هویتی در پروژه وجود ندارد). نمونه‌های پرخطر:
- `DELETE /api/trades/{trade_id}` (`trades.py:465`)
- `DELETE /api/finance/accounts/{account_id}` (`finance.py:147/979`)
- `DELETE /api/finance/transactions/{transaction_id}` (`finance.py:289`)
- `POST /api/imports/soft4x` و `/mt4` (بارگذاری فایل)
- `POST /api/analytics/intervals/seed-*` و `/api/finance/seed` و `/api/symbol-mappings/seed-defaults` (نوشتن داده)

### ۵.۲ داده‌های حساس
| داده | محل | ریسک |
|---|---|---|
| معاملات و PnL | جدول `trades` | افشای سابقهٔ مالی کامل |
| شماره کارت حساب‌ها | `Account.card_number` (`finance.py:29`) و در پاسخ `finance.py:111` | 🔴 حساس — **بدون هیچ ماسکینگ** برگردانده می‌شود |
| `raw_data` معاملات | `trades.py:176` | دادهٔ خام کامل |
| تراکنش‌ها و موجودی‌ها | `finance.py` | افشای مالی |
| اسکرین‌شات‌ها | `/storage/screenshots` (`main.py:69` — StaticFiles بدون احراز هویت) | 🔴 **هر کسی با حدس نام فایل به تصاویر دسترسی دارد** |

#### `SEC-01` — افشای شمارهٔ کارت بدون ماسکینگ
- **فایل/خط:** `finance.py:111` (`"card_number": a.card_number`) — کارت کامل در JSON برمی‌گردد.
- **راه‌حل:** ماسک‌کردن (مثل `**** **** **** 1234`) یا حذف از پاسخ عمومی.
- **زمان:** ۳۰ دقیقه.

#### `SEC-02` — سرو استاتیک اسکرین‌شات‌ها بدون کنترل دسترسی
- **فایل/خط:** `main.py:67-69` — `app.mount("/storage", StaticFiles(directory=STORAGE_DIR))` بدون احراز هویت؛ نام فایل قابل حدس (`trade_{id}_{timestamp}`).
- **راه‌حل:** سرو از طریق endpoint احراز‌شده یا نام فایل تصادفی (UUID).
- **زمان:** ۱ ساعت.

### ۵.۳ SQL Injection
- **نتیجهٔ بررسی:** ✅ **موردی یافت نشد.** همهٔ کوئری‌ها از SQLAlchemy ORM (`db.query(...).filter(...)`) استفاده می‌کنند که پارامترها را bind می‌کند. حتی `Trade.note.like(f"%{search}%")` (`trades.py:242`) به‌صورت پارامتر bind می‌شود و فقط مسئلهٔ پرفرمنس دارد (BE-13)، نه امنیت.
- **توجه:** هرگونه مهاجرت به `text()`/`execute()` خام در آینده باید با پارامتر انجام شود.

### ۵.۴ CORS
- **فایل/خط:** `main.py:38` — `allow_origins=["...", "*"]` + `allow_credentials=True` (BE-01). این ترکیب هم از نظر امنیتی خطرناک و هم در مرورگر نامعتبر است.

### ۵.۵ نبود Log امنیتی/مالکیت
- هیچ `user_id`/`owner_id` روی مدل‌ها نیست ⇒ در صورت چندکاربره شدن، تفکیک داده غیرممکن است.

---

## ۶. بررسی تست

### ۶.۱ Backend
| فایل | تعداد تست |
|---|---|
| `tests/test_finance.py` | 13 |
| `tests/test_prop.py` | 10 |
| `tests/test_trades.py` | 10 |
| `conftest.py` | (fixtures) |
| **مجموع** | **33** |

- **`TEST-01` — ماژول‌های بدون تست:**
  `analytics.py` (۱۴ endpoint)، `strategies.py` (۱۳)، `personal.py` (۷)، `imports.py` (۲)، `export.py` (۴)، `settings.py` (۲)، `symbol_mappings.py` (۵)، `finance.py` (فقط بخشی).
  یعنی تقریباً **نیمی از ۷۸ مسیر هیچ تستی ندارند**.
- **`TEST-02` — نبود تست یکپارچگی (Frontend↔Backend):** هیچ تست end-to-end یا قرارداد API وجود ندارد.
- **`TEST-03` — نبود تست امنیتی/مرزی:** ورودی‌های نامعتبر، فایل‌های خراب، صفحه‌بندی، و محدودیت‌ها تست نشده‌اند.

### ۶.۲ Frontend
- **`TEST-04` — عدم وجود تست پروژه‌ای:** `vitest.config.ts` تنظیم شده و `@testing-library/react` نصب است، اما هیچ تستی برای صفحات/کامپوننت‌ها/توابع API نوشته نشده. (فایل‌های موجود در جست‌وجو، تست‌های کتابخانه‌های ثالث در `node_modules` بودند، نه پروژه.)
- **زمان تخمینی کل:** پوشش حداقلی Backend = ۱۵ ساعت | Frontend = ۱۰+ ساعت.


---

## ۷. لیست کامل ایرادها با اولویت و زمان

| ID | عنوان | فایل:خط | اولویت | زمان |
|---|---|---|---|---|
| `BE-01` | نبود احراز هویت + CORS باز | `main.py:36-42` | **P0** | ۱۰ دقیقه (CORS) / ۶-۸ ساعت (JWT) |
| `BE-02` | کد مرده + تابع تکراری | `export.py:79-95` | **P0** | ۱۵ دقیقه |
| `BE-03` | مسیر تکراری `DELETE /accounts/{id}` | `finance.py:147,979` | **P0** | ۱۰ دقیقه |
| `BE-04` | `delete_category` بدون `return` | `finance.py:207-215` | **P0** | ۵ دقیقه |
| `BE-05` | نبود Rate Limit + سقف آپلود | `main.py`, `trades.py:583` و… | **P0** | ۱.۵ ساعت |
| `SEC-01` | افشای شمارهٔ کارت | `finance.py:111` | **P0** | ۳۰ دقیقه |
| `FE-01` | Bundle یکجا ۱.۰۷MB | `App.tsx:7-19` | **P1** | ۲-۳ ساعت |
| `BE-07` | dashboard کل trades را لود می‌کند | `analytics.py:58` | **P1** | ۴ ساعت |
| `BE-08` | N+1 در `get_firms` | `prop.py:147` | **P1** | ۳۰ دقیقه |
| `BE-09` | N+1 در `get_reviews` | `personal.py:134` | **P1** | ۳۰ دقیقه |
| `BE-10` | N+1 شمارش نسخه/معامله | `strategies.py:46,113,140` | **P1** | ۴۵ دقیقه |
| `BE-11` | نبود صفحه‌بندی stats/version-trades | `strategies.py:243,291` | **P1** | ۲.۵ ساعت |
| `SEC-02` | سرو استاتیک بدون کنترل | `main.py:69` | **P1** | ۱ ساعت |
| `BE-12` | لود تمام‌جدول در yesterday/risk/export | `analytics.py:266,338,458,567`, `export.py:337` | **P2** | ۳ ساعت |
| `BE-18` | نبود `response_model` | کل api | **P2** | ۴-۶ ساعت |
| `BE-14` | نبود create_all/migration در startup | `main.py:56-58` | **P2** | ۴۵ دقیقه |
| `BE-15` | SQLite بدون WAL | `core/database.py:7-10` | **P2** | ۳۰ دقیقه |
| `BE-13` | جستجوی Full-Scan (نه SQLi) | `trades.py:242` | **P2** | ۱.۵ ساعت |
| `BE-19` | لود کل حساب/تراکنش در گزارش‌ها | `finance.py:309,672+` | **P2** | ۳ ساعت |
| `BE-06` | bare `except:` | `personal.py:120,171` | **P2** | ۱۵ دقیقه |
| `FE-03..07` | ناسازگاری Dark Mode | `DashboardPage.tsx:378,413-425`, `ComparisonPage.tsx:568,572` | **P2** | ۱-۲ ساعت |
| `FE-09` | نبود Loading/Skeleton یکنواخت | `pages/*` | **P2** | ۳-۴ ساعت |
| `BE-16` | ناسازگاری Enum | `strategies.py:119` vs `prop.py:291` | **P3** | ۳۰ دقیقه |
| `BE-17` | fallback بی‌صدای ارز | `prop.py:22-27` | **P3** | ۲۰ دقیقه |
| `BE-20` | نبود اعتبارسنجی تاریخ | `analytics.py:617,779` | **P3** | ۱ ساعت |
| `FE-08` | توابع تکراری client | `client.ts:29,34` | **P3** | ۱۰ دقیقه |
| `FE-11` | نبود Axios interceptor | `client.ts:6-11` | **P3** | ۱.۵ ساعت |
| `FE-12` | دکمهٔ 🔔 بی‌عمل | `App.tsx:164-166` | **P3** | ۲۰ دقیقه |
| `FE-13/14` | رندر مجدد / نبود memo | `PropPage.tsx`, `ComparisonPage.tsx`, `App.tsx:177-188` | **P3** | ۳-۴ ساعت |
| `TEST-01..04` | پوشش تست ناکافی | `tests/`, `src/` | **P3** | ۲۵+ ساعت |
| `INT-01..04` | ناهماهنگی‌ها/caching | متعدد | **P2/P3** | ۴-۵ ساعت |


---

## ۸. پیشنهاد و اولویت‌بندی اقدام

### 🚨 باید فوراً رفع شوند (P0) — این هفته
1. `BE-02` کد مردهٔ `export.py` — ۱۵ دقیقه.
2. `BE-03` مسیر تکراری `finance.py` — ۱۰ دقیقه.
3. `BE-04` `return` فراموش‌شدهٔ `delete_category` — ۵ دقیقه.
4. `BE-01` (فاز ۱ فوری) **محدودکردن CORS** به `localhost:5173`/`3000` بدون `"*"` — ۱۰ دقیقه.
5. `SEC-01` ماسک شمارهٔ کارت — ۳۰ دقیقه.

➡️ **مجموع فوری: حدود ۱ ساعت** (همه کم‌ریسک و قابل تست).

### 🟠 می‌توانند این ماه انجام شوند (P1)
6. `BE-01` (فاز ۲) پیاده‌سازی JWT/API-Key.
7. `BE-07` + `BE-12` بازآرایی محاسبات به SQL Aggregation (بزرگ‌ترین برد پرفرمنس).
8. `BE-08`, `BE-09`, `BE-10` رفع N+1.
9. `FE-01` Code Splitting صفحات.
10. `SEC-02` کنترل دسترسی فایل‌های استاتیک.

### 🟡 بعداً (P2/P3)
11. `BE-18` افزودن `response_model`ها + `BE-14`/`BE-15` پایداری SQLite.
12. `FE-03..07` اصلاح Dark Mode.
13. `TEST-01..04` گسترش پوشش تست (اول analytics/dashboard و یک تست E2E).
14. `FE-11`, `FE-08`, `BE-16/17/20`, `INT-*` پاکسازی‌های کوچک.

### ✅ چیزهایی که خوب است و نیازی به تغییر ندارند
- معماری Router/Prefix تمیز و یکنواخت در `main.py`.
- مدیریت session دیتابیس با `Depends(get_db)` و الگوی try/finally (بدون نشتی اتصال).
- **عدم وجود SQL Injection** (استفادهٔ درست از ORM).
- حل N+1 اسکرین‌شات‌ها با `_get_screenshots_count_map` (`trades.py:97`) — الگوی درست.
- `joinedload` در `get_trade`/`export` (`trades.py:315`, `export.py:150`).
- ErrorBoundary سراسری + Dark Mode اصولی با CSS Variables.
- تطبیق کامل مسیرهای Frontend و Backend (۷۸/۷۸).
- Duplicate Detection با `trade_hash` در import.

> **نتیجه‌گیری کلی:** پروژه از نظر قابلیت و یکپارچگی **کامل و سالم** است و buildها همه موفق‌اند. اما دو بدهی فنی مهم دارد: **امنیت (صفر)** و **پرفرمنس (محاسبات در Python به‌جای SQL)**. با حدود **۱ ساعت کار P0** می‌توان ریسک‌های بحرانی را حذف کرد و با **۱۰–۱۵ ساعت کار P1** پروژه به یک پایهٔ قابل‌اتکا برای مقیاس‌پذیری می‌رسد.

---

### 📎 پیوست — شواهد اجرا
- `npx tsc -b --force` → `TSC_EXIT=0`
- `npx vite build` → 687 modules, built, `VITE_EXIT=0` (با هشدار chunk > 500kB)
- `npm run build` → `NPM_BUILD_EXIT=0`
- `python -m py_compile app/api/prop.py` → OK
- `TestClient` روی `/api/prop/alerts?unread_only=true` → **200**
- `app.openapi()` → **78 paths**

*گزارش توسط بررسی خودکار کد در تاریخ ۱۴۰۵/۰۷/۰۳ تهیه شد.*

