# گزارش اصلاح P1-01 — تازگی موجودی بروکر

## وضعیت نهایی: FIXED

### تغییرات انجام‌شده
- `FinanceSyncService` اکنون موجودی هر حساب را از `initial_balance`، خالص P&L معاملات بستهٔ `REAL_PERSONAL` و مجموع واریز/برداشت بروکر بازسازی می‌کند. `net_pnl` با جمع `pnl + commission + swap` در query محاسبه می‌شود.
- همگام‌سازی دستی، حساب‌های دارای معامله یا گردش وجه را پوشش می‌دهد؛ همچنین متدهای بازسازی یک/چند حساب اضافه شدند.
- بعد از ثبت و ویرایش معامله، حساب(های) متأثر refresh می‌شوند. حذف تکی و گروهی نیز شناسهٔ حساب را پیش از حذف ذخیره و پس از commit بازسازی می‌کند.
- مسیرهای ایجاد/ویرایش/حذف گردش وجه پس از تغییر ledger موجودی را بازسازی می‌کنند. کنترل‌های قبلی برای جلوگیری از موجودی منفی حفظ شده‌اند.
- endpoint دستی `POST /api/trading/accounts/{account_id}/sync-balance` اضافه شد.
- تست in-memory چرخهٔ سود، زیان، حذف معامله، واریز و برداشت اضافه شد.

### اعتبارسنجی
- اجرا: `venv\Scripts\python.exe -m pytest tests/test_finance_sync.py tests/test_finance.py tests/test_trading_domain.py -v`
- نتیجه: **82 passed**, 9 warning (deprecationهای وابستگی/اپلیکیشن).
- `compileall` و `git diff --check` نیز اجرا شدند؛ خطای کد/ whitespace گزارش نشد.

### نکتهٔ طراحی
`BrokerCashService` کنترل projected balance را پیش از mutation حفظ می‌کند، اما دیگر `current_balance` را با delta تغییر نمی‌دهد؛ پس از افزودن/ویرایش/حذف Movement مقدار canonical از ledger محاسبه می‌شود تا گردش دوبار شمرده نشود.

هیچ commit یا push انجام نشد.
