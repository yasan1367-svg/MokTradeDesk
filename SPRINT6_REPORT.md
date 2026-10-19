# 🚀 Sprint 6 — Export PDF/CSV

**تاریخ**: ۱۴۰۴/۰۷/۰۲ (۲۰۲۶-۰۹-۲۳)
**وضعیت**: ✅ کامل و تست‌شده

---

## 📌 خلاصه

در این اسپرینت، قابلیت **خروجی CSV و PDF** برای گزارش‌های معاملات، تحلیل و Dashboard اضافه شد.

## ✅ موارد پیاده‌سازی‌شده

| بخش | فایل | شرح |
|------|------|------|
| Backend API | `backend/app/api/export.py` | ۴ endpoint جدید برای Export |
| Router ثبت | `backend/app/main.py` | ثبت `export.router` با prefix `/api/export` |
| کتابخانه | `reportlab==5.0.1` | نصب برای تولید PDF |
| Frontend API | `frontend/src/api/client.ts` | ۴ تابع `exportTradesCsv`, `exportTradesPdf`, `exportAnalysisPdf`, `exportDashboardPdf` |
| UI — Trades | `frontend/src/pages/TradesPage.tsx` | دکمه‌های «📥 CSV» و «📄 PDF» |
| UI — Analysis | `frontend/src/pages/AnalysisPage.tsx` | دکمه «📄 دانلود PDF» |
| UI — Dashboard | `frontend/src/pages/DashboardPage.tsx` | دکمه «📄 دانلود گزارش PDF» |

## 🔧 Backend API

### ۱. `GET /api/export/trades/csv`
- خروجی CSV از لیست معاملات با فیلترهای اختیاری:
  - `version_id`, `strategy_id`, `symbol`, `test_type`, `source`, `direction`, `date_from`, `date_to`, `search`
- ستون‌ها: ID, Symbol, Direction, Size, Open/Close Price, Open/Close Time, PnL, Commission, Swap, R Multiple, Source, Test Type, Strategy, Version, Note

### ۲. `GET /api/export/trades/pdf`
- خروجی PDF (A4 Landscape) از لیست معاملات
- شامل: عنوان، تعداد کل، تاریخ، جدول معاملات، **خلاصه آماری** (سود خالص، نرخ برد، فاکتور سود)
- صفحات: Landscape + شماره صفحه + تاریخ در فوتر

### ۳. `GET /api/export/analysis/pdf?version_id=X`
- خروجی PDF (A4 Portrait) از تحلیل یک نسخه
- شامل: اطلاعات نسخه/استراتژی، **۱۴ متریک اصلی**، لیست تا ۵۰ معامله

### ۴. `GET /api/export/dashboard/pdf`
- خروجی PDF (A4 Portrait) از خلاصه Dashboard
- شامل: **Summary** (سود، نرخ برد، فاکتور سود، DD)، **Today**، **Period Performance** (ماه/فصل/سال)، **Prop Progress**

### ساختار مشترک PDF
- هدر: نام پروژه + تاریخ UTC
- فوتر: شماره صفحه
- جداول: هدر آبی `#3F7CFF`، ردیف‌های متناوب `#F9FAFB`/سفید، فونت Helvetica

## 🎨 Frontend UI

### TradesPage
- دو دکمه Export کنار دکمه جستجو
- فیلترهای فعلی صفحه (version, symbol, test_type, source, search) به query ارسال می‌شوند
- دانلود از Blob + anchor.click()

### AnalysisPage
- دکمه «📄 دانلود PDF» فقط وقتی تحلیل وجود دارد نمایش داده می‌شود
- `version_id` انتخاب‌شده ارسال می‌شود

### DashboardPage
- دکمه «📄 دانلود گزارش PDF» در هدر صفحه

## 🧪 تست‌های انجام‌شده

| Endpoint | Status | حجم |
|----------|--------|-----|
| `/api/export/trades/csv` | 200 OK | 2,475 bytes |
| `/api/export/trades/pdf` | 200 OK | 5,541 bytes |
| `/api/export/analysis/pdf?version_id=1` | 200 OK | 4,281 bytes |
| `/api/export/dashboard/pdf` | 200 OK | 2,538 bytes |
| `tsc --noEmit` (Frontend) | ✅ EXIT 0 | — |

## ⚠️ مشکلات برخوردشده و راه‌حل

| مشکل | راه‌حل |
|------|--------|
| محدودیت طول `editor` tool برای فایل بزرگ | فایل به چند بخش تقسیم و append شد |
| خطای `no such table` هنگام تست | سرور باید از پوشه `backend` اجرا شود تا `trading_desk.db` درست پیدا شود |
| خطای Enter در جدول CSV | در انتهای CSV writer بدون BOM |

## 📝 نکات تکمیلی

1. **فیلترها**: دکمه‌های Export فیلترهای **فعلی صفحه** را به‌صورت query param ارسال می‌کنند
2. **نام فایل**: خروجی‌ها به‌صورت `trades_YYYYMMDD_HHMMSS.csv/pdf` نام‌گذاری می‌شوند
3. **زبان PDF**: چون فونت فارسی نصب نیست، عنوان‌های PDF به انگلیسی نوشته شده‌اند (قابل بهبود با نصب font فارسی)
4. **محدودیت**: در گزارش تحلیل، حداکثر ۵۰ معامله نمایش داده می‌شود

## 🔮 پیشنهادات آینده

- [ ] نصب فونت Vazirmatn برای PDF فارسی
- [ ] اضافه کردن نمودارها به PDF (reportlab chart module)
- [ ] Excel (XLSX) به‌عنوان فرمت سوم
- [ ] Export فیلترشده معاملات به PDF از صفحه Risk Management

---
*این گزارش در تاریخ ۱۴۰۴/۰۷/۰۲ تکمیل شده است.*