# گزارش اصلاح P1-04 و P1-05 — صحت موجودی پراپ

## یافته‌های پیش از اصلاح

- مدل `PropStage` فیلدهای `total_pnl` و `user_share_pnl` ندارد؛ فیلد موجود برای سود محاسبه‌شده `current_profit` است. همچنین `profit_share_percentage` و `total_withdrawn` وجود دارند.
- `sync_prop_stage_profit` در `backend/app/services/import_engine.py` از importها و مسیرهای مدیریت معامله فراخوانی می‌شود. محل‌های فراخوانی production عبارت‌اند از `backend/app/api/trades.py` (چهار مسیر) و `ImportEngine`؛ تست import نیز آن را مستقیم فراخوانی می‌کند.
- `finance_metrics.prop_stage_3` در کد برنامه فقط از `backend/app/api/finance.py` فراخوانی می‌شد؛ تست `test_phase44_money.py` نیز مستقیم آن را می‌آزماید.

## تغییرات

### P1-04

- `finance_metrics._stage_net_pnl` اکنون فقط `REAL_PROP`های بسته (`close_time IS NOT NULL`) را جمع می‌کند.
- `finance_metrics.prop_stage_3` فیلتر ارز اختیاری گرفته و مراحل `FUNDED_REAL` را از طریق ارز `PropAccount` تفکیک می‌کند.
- `/finance/spendable-assets` مقدار `prop_stage_3_by_currency` را برای USDT و IRR برمی‌گرداند. قرارداد legacy داخل `prop_stage_3` (`amount` و `currency`) بدون تغییر باقی مانده است؛ مقدار `amount` همچنان USDT است.

### P1-05

- `sync_prop_stage_profit` فقط معاملات بسته را جمع می‌کند و net PnL را از `pnl + commission + swap` محاسبه می‌کند.
- در مرحلهٔ `FUNDED_REAL`، سهم به `current_profit` نوشته می‌شود (فیلدهای جداگانهٔ total/user share در مدل وجود ندارند). درصد صفر معتبر است؛ پیش‌فرض ۸۰٪ فقط در صورت `None` اعمال می‌شود.
- رفتار حفظ تاریخچهٔ مراحل غیرفعال بدون تغییر باقی مانده است.
- تست رگرسیون سهم ۸۰٪، نادیده‌گرفتن معاملهٔ باز، به‌روزرسانی پس از بسته‌شدن، سهم صفر و پیش‌فرض `None` اضافه شد.

## بررسی‌ها

- تست‌های هدفمند:
  `venv\\Scripts\\python.exe -m pytest tests/test_import_engine.py tests/test_finance.py tests/test_phase44_money.py tests/test_phase39_wallet.py::test_spendable_assets_preserves_legacy_keys -q`
  **86 passed**.
- مجموعهٔ کامل (طبق درخواست):
  `venv\\Scripts\\python.exe -m pytest tests/ -v`
  **672 passed, 21 failed, 1 xfailed**. شکست‌ها در تست‌های موجود cash movements، ثبت income/payout، migration/index و trade API دیده شدند؛ failure گزارش‌شده دربارهٔ قرارداد دقیق کلیدهای spendable نیز با بازگرداندن ساختار legacy و افزودن کلید جداگانه حل شد.
- `git diff --check`: موفق.

## نتیجه

**FIXED** — اصلاحات P1-04 و P1-05 پیاده‌سازی و تست‌های هدفمند موفق شدند. مجموعهٔ کامل تست‌ها همچنان ۲۱ شکست موجود/نامرتبط دارد که در این محدوده اصلاح نشدند.

هیچ commit یا push انجام نشد.