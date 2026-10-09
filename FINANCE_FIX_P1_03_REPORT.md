# گزارش رفع P1-03 — جداسازی سود شخصی از پراپ

## نتیجه

**وضعیت: FIXED**

## بررسی پیش از تغییر

- `get_net_profit` در `backend/app/api/finance.py` پیش از اصلاح، PnL شخصی و funded را در یک عدد جمع و هزینه‌ها را از مجموع کم می‌کرد.
- `_compute_real_pnl` سود حساب‌های معاملاتی شخصی و مراحل پراپ FUNDED_REAL را جداگانه محاسبه می‌کرد، اما فیلتر قرارداد معاملهٔ REAL را به‌صراحت اعمال نمی‌کرد.
- `_expenses_total` پیش از اصلاح فقط FEE و PURCHASE را جمع می‌کرد.
- مدل `PropStage` دارای فیلد `profit_share_percentage` است.

## تغییرات

- خروجی `/net-profit` اکنون بخش‌های `personal`، `prop`، `total` و `by_currency` را ارائه می‌کند و فیلدهای سازگاری `real_pnl`، `expenses` و `net_profit` حفظ شده‌اند.
- سود شخصی فقط از معاملات بستهٔ `REAL_PERSONAL` محاسبه می‌شود؛ PnL پراپ فقط از معاملات بستهٔ `REAL_PROP` در مراحل `FUNDED_REAL` است.
- سهم پراپ بر مبنای درصد مرحله محاسبه می‌شود؛ در نبود درصد، مقدار ۱۰۰٪ با warning ثبت می‌شود.
- هزینه‌های شخصی شامل FEE، PURCHASE و EXTERNAL_EXPENSE است. هزینهٔ پراپ در حال حاضر صفر است، چون مسیر حساب مالی پراپ مجزا موجود نیست.
- محاسبات USDT و IRR جدا هستند.

## فایل‌های تغییرکرده

- `backend/app/api/finance.py`
- `backend/tests/test_finance.py`
- `FINANCE_FIX_P1_03_REPORT.md`

## اعتبارسنجی

دستور موردنیاز: `venv\Scripts\python.exe -m pytest tests/test_finance.py -v` از پوشهٔ `backend`.
