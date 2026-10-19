# PHASE9_REPORT — ادغام دو دفتر کل (Personal → Finance)

**وضعیت:** ✅ کامل شد
**Revision جدید:** `9f1a2b3c4d5e` (down_revision: `b7d4e19c2f83`)
**Backup:** `backend/trading_desk.backup_phase9_20260925_020348.db`

---

## ۱. خلاصه تغییرات

| مرحله | تغییر |
|------|-------|
| Backup | از `trading_desk.db` نسخه پشتیبان گرفته شد. |
| Migration | افزودن `trades.finance_account_id` (FK → `accounts.id`)، انتقال داده‌ها، حذف `trades.personal_account_id`، حذف جداول `personal_accounts` و `ledger_transactions`. |
| Models | `PersonalAccount`/`LedgerTransaction`/`PersonalAccountCreate`/`PersonalAccountResponse` حذف شدند. `Trade.personal_account_id` → `Trade.finance_account_id` + `relationship("Account")`. `JournalReview`/`Screenshot` دست‌نخورده. |
| APIs | از `api/personal.py` تمام endpointهای حساب شخصی/دفتر کل/جریان نقدی حذف شد (فقط Journal و `prop-accounts-list` ماند). `imports.py`/`trades.py`/`analytics.py`/`trade_validator.py`/`import_service.py` به `finance_account_id` منتقل شدند. `schemas/personal.py` (بی‌استفاده) حذف شد. |
| Frontend | `PersonalPage.tsx` حذف شد؛ لینک `personal` از `Sidebar.tsx` و مسیر/تایتل آن از `App.tsx` حذف شد. APIهای پرسونال از `client.ts` پاک شد (Journal باقی ماند). `TradesPage.tsx` و `ImportPage.tsx` از حساب شخصی پاک‌سازی شدند. |

---

## ۲. جدول Migration داده‌ها

### `personal_accounts` → `accounts`

| مبدأ | مقصد |
|------|------|
| `name` | `name` |
| — | `type = 'BROKER'` |
| `currency` | `currency` (IRR/USD، سایر → USD) |
| `initial_balance + SUM(ledger.amount)` | `balance` |
| `broker_name` | `broker_name` |
| `id` (نگاشت داخلی) | `id` جدید در `accounts` (برای نگاشت FKs) |

### `ledger_transactions` → `transactions`

| `transaction_type` | شرط | `type` مقصد |
|--------------------|------|-------------|
| `TRADE_PNL` | amount ≥ 0 | `PROFIT` |
| `TRADE_PNL` | amount < 0 | `LOSS` |
| `PROP_PAYOUT` | — | `PROFIT` |
| `DEPOSIT` | — | `DEPOSIT` |
| `WITHDRAWAL` | — | `WITHDRAWAL` |
| `CHALLENGE_FEE` | — | `PURCHASE` |
| `EXPENSE` | — | `FEE` |
| `MANUAL_ADJUSTMENT` | amount ≥ 0 | `DEPOSIT` |
| `MANUAL_ADJUSTMENT` | amount < 0 | `WITHDRAWAL` |

نگاشت سایر فیلدها: `amount = abs(amount)`، `date = transaction_date`، `description` مستقیم، `related_prop_account_id = prop_account_id`، `related_trade_id` در صورت `source_type` شامل `trade`، `is_deleted = 0`.
حساب مقصد: نگاشت `personal_account_id` → `accounts.id`، در غیر این‌صورت `prop_accounts.finance_account_id`، و در نهایت اولین حساب موجود (پیش‌فرض `accounts.id=1`).

### نتیجه واقعی روی داده‌ها

| جدول | قبل | بعد |
|------|-----|-----|
| `personal_accounts` | ۰ | جدول حذف شد |
| `ledger_transactions` | ۱ | جدول حذف شد |
| `accounts` | ۱ | ۱ (بدون تغییر؛ چون `personal_accounts` خالی بود) |
| `transactions` | ۰ | **۱** (همان رکورد `PROP_PAYOUT` → `type=PROFIT, amount=1000, account_id=1, related_prop_account_id=1`) |
| `trades` | `personal_account_id` (۱۹ ستون) | `finance_account_id` (FK → accounts) |

---

## ۳. نتایج تست

| تست | نتیجه |
|-----|-------|
| `alembic upgrade head` | ✅ موفق (`b7d4e19c2f83 → 9f1a2b3c4d5e`) |
| بررسی ساختار DB | ✅ جداول قدیمی حذف، `trades.finance_account_id` با FK به `accounts` |
| `python -c "import app.main"` | ✅ IMPORT OK |
| OpenAPI | ✅ ۷۲ مسیر؛ `/api/personal/accounts`, `/ledger`, `/cashflow` **حذف شده**؛ Journal و `prop-accounts-list` موجود |
| Smoke تست توابع (DB واقعی) | ✅ `journal/reviews`=1، `trades`=18، `finance/accounts`=1، `finance/transactions`=1، `finance/summary` ✅، `analytics/risk-metrics` ✅ |
| `npx tsc -b --force` | ✅ Exit 0 |
| `npm run build` | ✅ Exit 0 (`dist/assets/index-*.js` 1,023 kB) |

---

## ۴. نکات و هشدارها

1. **تفاوت قرارداد علامت:** `ledger_transactions.amount` علامت‌دار بود ولی `transactions.amount` همیشه مثبت است و جهت با `type` مشخص می‌شود؛ در Migration تبدیل انجام شد.
2. **تفاوت مدل Enum:** SQLAlchemy نامِ Enum را ذخیره می‌کند (مثلاً `BROKER`، `PROFIT`)، بنابراین Migration از مقادیر نام (uppercase) استفاده می‌کند.
3. **`Trade.finance_account_id`:** جانشین `personal_account_id` شد. UI معامله‌ی دستی در `TradesPage` برای `REAL` اکنون فقط «مرحله‌ی پراپ» را انتخاب می‌کند؛ فیلد `finance_account_id` در API موجود است اما فعلاً از UI مقدار نمی‌گیرد (قابل استفاده در فازهای بعدی).
4. **`ImportPage`:** هدف «حساب شخصی» حذف شد؛ اهداف باقی‌مانده: استراتژی، پراپ.
5. **حذف فیزیکی:** `Backup` تنها راه بازگشت داده‌هاست (به‌جز `downgrade` که فقط ساختار جداول قدیمی را بازسازی می‌کند و داده‌ها را برنمی‌گرداند).
6. **نکته‌ی از قبل موجود (خارج از دامنه):** `prop_accounts.id=2` مقدار `finance_account_id=2` دارد اما `accounts.id=2` وجود ندارد (ناسازگاری داده‌ی قدیمی). همچنین در `finance.py` هشدار Duplicate Operation ID برای `delete_account` وجود دارد (قبلاً هم بود).
7. **فایل‌های backup فرانت‌اند** (`PersonalPage.tsx.bak/pre61` و مشابه) دست‌نخورده باقی مانده‌اند و ارجاعی به آن‌ها وجود ندارد.

---

## ۵. فایل‌های تغییر‌یافته

**Backend:** `models/personal.py`, `models/strategy.py`, `api/personal.py`, `api/trades.py`, `api/imports.py`, `api/analytics.py`, `utils/trade_validator.py`, `services/import_service.py`, `migrations/env.py`, `migrations/versions/9f1a2b3c4d5e_merge_personal_into_finance.py` (جدید)
**حذف‌شده:** `app/schemas/personal.py`
**Frontend:** `App.tsx`, `components/Sidebar.tsx`, `api/client.ts`, `pages/TradesPage.tsx`, `pages/ImportPage.tsx`
**حذف‌شده:** `pages/PersonalPage.tsx`