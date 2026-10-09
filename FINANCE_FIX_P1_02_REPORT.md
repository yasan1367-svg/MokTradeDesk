# گزارش اصلاح P1-02 — هم‌معنایی Cash Flow و درآمد/هزینه

## وضعیت: FIXED

## تعریف اعمال‌شده

Cash Flow درآمد را فقط برای ورود به بانک و هزینه را فقط برای خروج از بانک ثبت می‌کند. انتقال به حساب غیر‌بانکی از بانک `expense`، انتقال از حساب غیر‌بانکی به بانک `income`، و انتقال Bank→Bank `none` است. `EXTERNAL_INCOME` فقط در مقصد بانکی `income` محسوب می‌شود؛ واریز (`DEPOSIT`) به‌تنهایی `none` باقی می‌ماند.

## تغییرات

- `backend/app/services/wallet_service.py`: `detect_cash_flow` برای TRANSFER جهت مبدأ/مقصد را اعمال می‌کند؛ EXTERNAL_INCOME و PROFIT فقط به بانک income هستند و WITHDRAWAL/LOSS/FEE/PURCHASE/EXTERNAL_EXPENSE فقط از بانک expense می‌شوند. DEPOSIT همچنان `none` است.
- `backend/app/services/financial_reporting.py`: `bank_income_filter` و `is_bank_income` اکنون از `cash_flow == income` استفاده می‌کنند تا تعریف income با summary یکی باشد.
- `backend/app/api/finance.py`: نمودار `/charts/cashflow` به‌جای فیلتر نوع تراکنش/`bank_income_filter`، فقط `cash_flow == income/expense` را جمع می‌زند. گزارش ماهانه و تفکیک دسته‌بندی نیز برای درآمد و هزینه از همان ستون cash_flow استفاده می‌کنند.
- `backend/tests/test_finance.py`: هفت حالت الزامی با تست‌های پارامتری API پوشش داده شده‌اند. تست category-breakdown نیز به‌روزرسانی شد: DEPOSIT طبق قرارداد جدید درآمد نیست، بنابراین نمونهٔ درآمد آن تست EXTERNAL_INCOME است.

## بررسی و اعتبارسنجی

فایل‌های بررسی‌شده پیش از تغییر: `financial_reporting.py`، `wallet_service.py`، `api/finance.py`، مدل‌های مالی و `test_finance.py`. summary از قبل از `cash_flow` ذخیره‌شده استفاده می‌کرد؛ chart و برخی گزارش‌ها از قواعد مستقل استفاده می‌کردند که باعث اختلاف می‌شد.

فرمان نهایی اجراشده از پوشهٔ `backend`:

```text
venv\Scripts\python.exe -m pytest tests/test_finance.py -v
```

نتیجه: **52 passed, 9 warnings**. هشدارها deprecationهای وابستگی‌ها هستند و تستی را ناموفق نکردند. `git diff --check` نیز بدون خطا بود.

در اجرای نخست، یک تست قدیمی category-breakdown انتظار داشت DEPOSIT درآمد باشد؛ این انتظار با قرارداد مصوب P1-02 تعارض داشت. تست به EXTERNAL_INCOME تغییر کرد و بعد از اصلاح، کل مجموعهٔ تست با موفقیت اجرا شد.

## فایل‌های تغییرکرده

- `backend/app/services/wallet_service.py`
- `backend/app/services/financial_reporting.py`
- `backend/app/api/finance.py`
- `backend/tests/test_finance.py`
- `FINANCE_FIX_P1_02_REPORT.md` (این گزارش)

هیچ commit یا push انجام نشد؛ تغییرات به P1-02 محدود ماندند.