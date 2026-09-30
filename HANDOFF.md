# Handoff — MokTradeDesk

> سند انتقال به توسعه‌دهندهٔ بعدی. آخرین به‌روزرسانی: **پایان فاز ۴۰**.

## وضعیت فعلی

- **آخرین commit:** `09070dc`
- **تست‌ها:** ۲۴۶ بک‌اند (pytest) + ۹ فرانت‌اند (vitest) — همه سبز (۰ xfailed)
- **Alembic head:** `f39a1b2c3d4e`
- **دیتابیس:** `backend/trading_desk.db` (SQLite، WAL)

## قابلیت‌های آماده

- ✅ Strategy + StrategyVersion (+ Fork)
- ✅ Prop (Firm, Account, Stage, Rule Engine)
- ✅ Analysis (Version / Prop / Personal — Multi-scope)
- ✅ Trade (CRUD, Import MT4/Soft4X, Soft Delete + گروهی، Screenshot)
- ✅ Finance (WalletService، برداشت پراپ/بروکر، تراکنش/انتقال/اصلاح)
- ✅ Journal + Screenshot
- ✅ Calendar + Risk + Comparison
- ✅ Backup (خودکار + دستی + بازیابی)
- ✅ Export (PDF/CSV)

## قابلیت‌های Skip شده

- ❌ Authentication
- ❌ Strategy Version Review (UI)
- ❌ E2E Tests
- ❌ Master Plan (فازهای ۴۵–۶۴)

## بدهی‌های باز (شناخته‌شده)

| # | مورد | شدت | یادداشت |
|:--|:---|:---:|:---|
| ۱ | ✅ **رفع شد (فاز ۴۰.۵)** — `PATCH /api/trades/{id}` تغییرات را persist نمی‌کرد | — | `app/api/trades.py:361`: `db.commit()` گم شده بود و `db.refresh()` تغییرات را دور می‌ریخت. fix: افزودن `db.commit()` پیش از `refresh` (خط ۴۸۶). تست: `test_full_cycle_manual_trade_reclassification` (اکنون pass). |
| ۲ | سبدهای per-type در `spendable-assets` ارز-ناشناس‌اند (`bank` همهٔ ارزها را جمع می‌زند) | 🟡 | pre-existing؛ رفع کامل = تفکیک `bank_irr`/`bank_usd`. |
| ۳ | `WalletService.reconcile()`/`ledger()` بدون endpoint عمومی | 🟢 | ابزار تشخیص drift آمادهٔ استفاده است. |

## چطور ادامه بدهیم

1. `git pull`
2. `cd backend && alembic upgrade head`
3. `venv\Scripts\python.exe -m pytest -q -p no:warnings`  → انتظار: ۲۴۵ passed
4. `cd frontend && npx tsc -b --force && npx vitest run && npm run build`
5. `cd backend && venv\Scripts\python.exe -m uvicorn app.main:app --reload`
6. `cd frontend && npm run dev`

## نکات مهم

- `WalletService` تنها نویسندهٔ `FinancialAccount.balance` است (فاز ۳۹). هر تغییر موجودی باید از آن عبور کند.
- تست‌ها روی DB جداگانه اجرا می‌شوند (فاز ۳۹.۵)؛ هوک `startup` (migration + backup) در تست‌ها no-op می‌شود.
- enumها بسته به مدل، گاهی `value` (lowercase) و گاهی `NAME` ذخیره می‌شوند — به کامنت‌های مدل‌ها دقت کنید.
