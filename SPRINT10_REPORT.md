# Sprint 10 — UX Quality (بهبود تجربه کاربری)

## خلاصه
در این اسپرینت، تجربه کاربری پروژه از جنبه‌های مختلف بهبود داده شد: Skeleton Loader، ریسپانسیو موبایل، میانبرهای کیبورد، متغیرهای محیطی، لاگینگ، و ErrorBoundary پیشرفته.

---

## تغییرات انجام‌شده

### ۱. Skeleton Loaders
**فایل جدید:** `frontend/src/components/Skeleton.tsx`

- کامپوننت `Skeleton` با واریانت‌های `text`, `card`, `circle`, `rect`
- سه پراست `DashboardSkeleton`, `RiskSkeleton`, `CalendarSkeleton` برای صفحات مختلف
- جایگزینی متن ساده ⏳ با اسکلتون‌های واقعی در:
  - `DashboardPage.tsx` → `DashboardSkeleton`
  - `RiskManagementPage.tsx` → `RiskSkeleton`
  - `CalendarPage.tsx` → `CalendarSkeleton`
- انیمیشن `animate-pulse` با رنگ‌های متناسب با تم

### ۲. Mobile Responsive
**فایل:** `frontend/src/components/Sidebar.tsx`

- سایدبرگ دسکتاپ (≥lg) بدون تغییر
- دکمه **همبرگر ☰** در موبایل (fixed در بالا-راست)
- پنل کشویی از راست با اوورلی نیمه‌شفاف
- بستن منو با کلیک بیرون یا انتخاب آیتم
- نمایش **✕** در حالت باز
- دکمه بستن در هدر پنل موبایل

### ۳. Keyboard Shortcuts
**فایل:** `frontend/src/App.tsx`

- **Ctrl+D / Cmd+D** → رفتن به Dashboard
- **Ctrl+T / Cmd+T** → رفتن به صفحه معاملات
- **Ctrl+K / Cmd+K یا Ctrl+/** → فوکوس روی جستجو
- **Ctrl+N / Cmd+N** → ایجاد معامله جدید (dispatch custom event)
- **Esc** → بستن مودال‌ها (dispatch custom event)

### ۴. Environment Variables
**فایل جدید:** `.env.example`
**فایل:** `frontend/src/api/client.ts`

- `.env.example` شامل کلیدهای:
  - `API_BASE_URL`, `DATABASE_URL`, `VITE_API_BASE_URL`
  - `SECRET_KEY`, `LOG_LEVEL`, `LOG_FILE`
- `client.ts` از `import.meta.env.VITE_API_BASE_URL` می‌خواند (با fallback به `localhost:8000`)

### ۵. Logging & Monitoring
**فایل:** `backend/app/main.py`

- راه‌اندازی `logging.basicConfig` با دو handler:
  - **فایل** `backend/logs/app.log` (با encoding utf-8)
  - **خروجی کنسول** (StreamHandler)
- **Middleware لاگ درخواست‌ها**: ثبت `METHOD /path → status (مدت زمان)` برای همه درخواست‌ها
- **رویداد startup/shutdown**: لاگ شروع و توقف سرور

### ۶. بهبود ErrorBoundary
**فایل:** `frontend/src/App.tsx`

- نمایش **پیام خطا با فونت monospace** در یک باکس اسکرول‌شونده
- دکمه **📋 کپی خطا**: کپی اطلاعات خطا (نام، پیام، stack) در کلیپ‌بورد
- لاگ خطا در کنسول با `componentDidCatch`
- پیام خوش‌آمدتر: «خطا در بارگذاری صفحه ...»

---

## فایل‌های تغییر داده شده

| فایل | نوع تغییر |
|------|-----------|
| `frontend/src/components/Skeleton.tsx` | 🆕 فایل جدید |
| `frontend/src/components/Sidebar.tsx` | ✏️ ریسپانسیو موبایل (همبرگر) |
| `frontend/src/App.tsx` | ✏️ کیبورد شورتکات + ErrorBoundary پیشرفته |
| `frontend/src/api/client.ts` | ✏️ `VITE_API_BASE_URL` از env |
| `frontend/src/pages/DashboardPage.tsx` | ✏️ Skeleton لودر |
| `frontend/src/pages/RiskManagementPage.tsx` | ✏️ Skeleton لودر |
| `frontend/src/pages/CalendarPage.tsx` | ✏️ Skeleton لودر |
| `backend/app/main.py` | ✏️ لاگینگ + middleware |
| `.env.example` | 🆕 فایل جدید |

---

## نکات فنی

- **Skeleton**: واریانت‌های مختلف برای کاربردهای گوناگون (text, card, circle, rect)
- **کیبورد شورتکات**: تشخیص خودکار `Ctrl` (ویندوز/لینوکس) و `Cmd` (مک)
- **لاگینگ**: فایل لاگ در `backend/logs/app.log` ذخیره می‌شود و به صورت خودکار ساخته می‌شود
- **ErrorBoundary**: فقط خطاهای زمان رندر را می‌گیرد، نه خطاهای Event Handlerها

---

## بهبودهای آتی پیشنهادی

- [ ] تبدیل جدول‌ها به کارت‌های عمودی در موبایل (موجود: فقط سایدبرگ ریسپانسیو شده)
- [ ] فونت‌های responsive با Tailwind (text-sm, text-base در breakpointهای مختلف)
- [ ] لاگ سطح‌بندی شده (DEBUG, INFO, WARNING, ERROR) با قابلیت تنظیم از env