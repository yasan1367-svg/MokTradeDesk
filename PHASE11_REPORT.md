# فاز ۱۱ — گزارش‌های پیشرفته مالی

**تاریخ:** 1405/07/03 | **وضعیت:** ✅ کامل

---

## ۱. بررسی وضعیت قبل (گزارش‌های موجود در `backend/app/api/finance.py`)
- `GET /api/finance/summary` — خلاصه مالی (دارایی به تفکیک ارز، درآمد/هزینه/انتقال/تعداد)
- `GET /api/finance/accounts/{id}/stats` — آمار یک حساب
- `GET /api/finance/withdrawals/stats` — آمار و تاریخچه برداشت‌ها
- `GET /api/finance/charts/cashflow` — درآمد vs هزینه ماهانه (میلادی)
- `GET /api/finance/charts/distribution` — توزیع تراکنش‌ها بر اساس نوع

**کمبودها:** گزارش ماهانه شمسی، تفکیک دسته‌بندی با درصد، مقایسه حساب‌ها، سود و زیان با روند.

## ۲. Backend — ۴ endpoint جدید
همه در `backend/app/api/finance.py` (+ توابع کمکی `_jalali_to_gregorian`، `_gregorian_to_jalali`، `_jalali_range`، `_current_jalali_year`، `JALALI_MONTHS`):
- `GET /api/finance/reports/monthly` — درآمد/هزینه/خالص ۱۲ ماه شمسی. پارامترها: `year` (شمسی)، `account_id`
- `GET /api/finance/reports/category-breakdown` — مجموع و درصد هر دسته. پارامترها: `year`، `month`، `type` (income/expense)، `account_id`
- `GET /api/finance/reports/account-comparison` — موجودی/درآمد/هزینه/خالص هر حساب. پارامترها: `year`، `month`، `currency`
- `GET /api/finance/reports/profit-loss` — سود خالص، حاشیه سود، تفکیک سالانه، ماهانه و روند تجمعی. پارامترها: `year`، `account_id`

## ۳. Frontend
- `frontend/src/api/client.ts`: چهار تابع `getFinanceMonthlyReport`, `getFinanceCategoryBreakdown`, `getFinanceAccountComparison`, `getFinanceProfitLoss`.
- `frontend/src/pages/FinancePage.tsx`: تب جدید **📈 گزارش‌های پیشرفته** شامل:
  - فیلترها: سال شمسی، ماه شمسی، حساب
  - کارت‌ها: سود خالص، کل درآمد، کل هزینه، حاشیه سود
  - نمودار میله‌ای: درآمد vs هزینه ماهانه
  - نمودار خطی: روند سود و زیان (ماهانه + تجمعی)
  - نمودار دایره‌ای: تفکیک دسته‌بندی (با درصد)
  - جدول: مقایسه حساب‌ها
  - جدول: سود و زیان به تفکیک سال

## ۴. تست
- `npx tsc -b --force` ✅ بدون خطا
- `npm run build` ✅ (`built in 5.66s`)
- تست مستقیم endpointها با DB واقعی ✅ (monthly=۱۲ ماه، breakdown با درصد، accounts، P&L + round-trip تاریخ شمسی)

## ۵. فایل‌های تغییریافته
- `backend/app/api/finance.py` (+ حدود ۳۶۰ خط)
- `frontend/src/api/client.ts`
- `frontend/src/pages/FinancePage.tsx`
- `PHASE11_REPORT.md` (این فایل)
