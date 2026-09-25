# فاز ۱۴.۳ — فیلتر بازه زمانی + جدول معاملات

**تاریخ:** 1405/07/03 | **وضعیت:** ✅ کامل

---

## ۱. Backend

**الف) `GET /api/analytics/dashboard?date_from=&date_to=`** (`analytics.py`)
- پارامترهای اختیاری بازه؛ فیلتر بر اساس `close_time` (UTC). `date_to` خالصِ تاریخ → تا پایان روز.
- بدون پارامتر = مثل قبل (همه).

**ب) `GET /api/trades/?status=closed|open`** (`trades.py`)
- پارامتر جدید `status`: `open` → `close_time IS NULL`، `closed` → `close_time IS NOT NULL`.
- `limit` / `sort_by` / `sort_order` از قبل موجود بودند.

## ۲. Frontend — فیلتر بازه
- **دکمه‌ها**: امروز، دیروز، این هفته (شنبه تا امروز)، این ماه (شمسی)، این فصل (شمسی)، امسال (شمسی)، همه، سفارشی.
- **سفارشی**: انتخاب بازه با تقویم شمسی (`PersianDateInput`).
- **ذخیره در `localStorage`**: `mok_dashboard_range` / `mok_dashboard_custom_from` / `mok_dashboard_custom_to`.
- همگام با endpoint (`getDashboardData({date_from, date_to})`).
- تابع کمکی جدید `jalaliToGregorian` به `utils/jalali.ts` اضافه شد.

## ۳. Frontend — جدول معاملات
- **آخرین معاملات** (`status=closed&limit=10`): ستون‌ها نماد، نوع (خرید/فروش)، استراتژی، سود/زیان، تاریخ + دکمهٔ **«مشاهده همه»** (ناوبری به صفحهٔ معاملات با prop جدید `onNavigate`).
- **معاملات باز** (`status=open`): ستون‌ها نماد، نوع، استراتژی، سود/زیان لحظه‌ای + **EmptyState** وقتی معاملهٔ بازی نیست.

## ۴. UX
- **Dark Mode / RTL**: CSS variables + `text-right` + layout RTL.
- **Skeleton**: `DashboardSkeleton` موجود.
- **Toast**: خطای بارگذاری داشبورد.
- **EmptyState**: هر دو جدول در حالت خالی.

## ۵. تست
| بررسی | نتیجه |
|---|---|
| Backend smoke (فیلتر بازه) | ✅ Sept=18، بازهٔ خالی=0، امروز=0 (فیلتر واقعاً عمل می‌کند) |
| Backend smoke (`status`) | ✅ closed total=18/returned=10، open total=0 |
| `pytest` | ✅ 33 passed |
| `tsc -b --force` | ✅ بدون خطا |
| `vitest` | ✅ 9 passed |
| `npm run build` | ✅ موفق (3.69s) |

## ۶. فایل‌های تغییریافته
- `backend/app/api/analytics.py` (فیلتر بازه در `/dashboard`)
- `backend/app/api/trades.py` (پارامتر `status`)
- `frontend/src/utils/jalali.ts` (`jalaliToGregorian`)
- `frontend/src/api/client.ts` (`getDashboardData(params)`، `status` در `getTrades`)
- `frontend/src/App.tsx` (پاس‌دادن `onNavigate`)
- `frontend/src/pages/DashboardPage.tsx` (فیلتر بازه + دو جدول)
- `PHASE14_3_REPORT.md`
