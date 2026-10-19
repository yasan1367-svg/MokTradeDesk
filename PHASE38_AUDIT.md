# 📋 PHASE38_AUDIT.md — Personal Finance Foundation Audit

> **نوع سند:** Audit — پیش از شروع پیاده‌سازی فاز ۳۸
> **تاریخ:** ۱۴۰۵/۰۷/۰۹ (2026-09-29)
> **پایه:** پس از Phase 37 (`FinancialAccount` / `FinancialTransaction`)
> **Revision فعلی:** `c9d0e1f2a3b4`

---

## خلاصهٔ اجرایی

دامنهٔ FINANCE پس از فاز ۳۷ ساختار تمیزی دارد (`FinancialAccount`/`FinancialTransaction` با
نام‌های یکسان‌شده) اما چند ناهمگونی باقی است:

| محور | وضعیت | شدت |
|:---|:---|:---:|
| `AccountType` | فقط `BANK/EXCHANGE/CRYPTO_WALLET` — `CARD/CASH/TRUST_WALLET` گم شده | 🟠 |
| `PropAccount.currency` · `PropCost.currency` · `PropCost.cost_type` | **String** (نه Enum) | 🟠 |
| `PropAlert.is_read` | **Integer** (نه Boolean) | 🟡 |
| `DateTime` naive | ~۳۵ ستون | 🟡 |
| مبالغ | **Float** — `Decimal/Numeric` صفر | 🟠 |
| DB واقعی | `accounts=0` · `transactions=0` · `prop_costs=0` · `prop_alerts=0` ⇒ ریسک مهاجرت **صفر** | 🟢 |

**نتیجهٔ کلیدی:** هر ۵ تغییر پیشنهادی فاز ۳۸ روی **ستون‌های سازگار با SQLite** (`VARCHAR`/`INTEGER`)
صورت می‌گیرد ⇒ **هیچ migration اجباری لازم نیست** (به‌جز در صورت تمایل به CHECK constraint).

---

## ۱. FinancialAccount — وضعیت فعلی

| ستون | نوع | Nullable | Index | FK |
|:---|---:|:---:|:---:|:---:|
| `id` | Integer | NO | PK | — |
| `name` | String | NO | — | — |
| `type` | `Enum(AccountType)` | NO | — | — |
| `currency` | `Enum(Currency)` | NO | — | — |
| `balance` | **Float** | YES (0.0) | — | — |
| `card_number` | String | YES | — | — |
| `created_at` | **DateTime (naive)** | YES | — | — |

- **relationships:** `transactions_out` · `transactions_in` · `entries` (هر سه با `FinancialTransaction`)
- **indexes:** فقط `id` (PK auto) — هیچ ایندکسی روی `type`/`currency`
- **`currency`:** ✅ `Enum(Currency)` (نه String)

> ⚠️ `balance` = `Float` ⇒ دقت اعشاری ندارد (موضوع فاز Precision).
> ⚠️ `created_at` naive ⇒ ناسازگار با ستون‌های `DateTime(timezone=True)` بقیهٔ دامنه.

---

## ۲. FinancialTransaction — وضعیت فعلی

| ستون | نوع | Nullable | Index | FK |
|:---|---:|:---:|:---:|:---:|
| `id` | Integer | NO | PK | — |
| `account_id` | Integer | NO | ✅ | → `accounts.id` |
| `category_id` | Integer | YES | — | → `categories.id` |
| `amount` | **Float** | NO | — | — |
| `currency` | `Enum(Currency)` | NO | — | — |
| `date` | **DateTime (naive)** | NO | ✅ | — |
| `description` | Text | YES | — | — |
| `type` | `Enum(TransactionType)` | NO | ✅ | — |
| `from_account_id` | Integer | YES | — | → `accounts.id` |
| `to_account_id` | Integer | YES | — | → `accounts.id` |
| `related_trade_id` | Integer | YES | — | → `trades.id` |
| `related_prop_account_id` | Integer | YES | — | → `prop_accounts.id` |
| `is_deleted` | Boolean | YES | — | — |
| `created_at` | DateTime (naive) | YES | — | — |

- **indexes:** `account_id`, `date`, `type` (فاز ۳۶) ✅
- **`currency`:** ✅ `Enum(Currency)`

`TransactionType` (۹ مقدار — مطابق Master Plan):
```
DEPOSIT · WITHDRAWAL · EXCHANGE · PROFIT · LOSS · FEE · PURCHASE · TRANSFER(ف۳۷) · ADJUSTMENT(ف۳۷)
```
> نگاشت با Master Plan: `PROFIT`=Income · `LOSS/FEE/PURCHASE`=Expense · `TRANSFER`=Transfer ·
> `EXCHANGE`=Conversion · `ADJUSTMENT`=Adjustment ✅

---

## ۳. Category — وضعیت فعلی

| ستون | نوع | Nullable |
|:---|---:|:---:|
| `id` | Integer | NO |
| `name` | String | NO |
| `type` | `Enum(CategoryType)` | NO |
| `color` | String | YES |
| `icon` | String | YES |
| `created_at` | DateTime (naive) | YES |

- **relationship:** `transactions` → `FinancialTransaction`
- `CategoryType`: `INCOME · EXPENSE · TRANSFER · EXCHANGE · CONVERSION(ف۳۷)` ✅ کامل

---

## ۴. Enumها (کد کامل)

```python
class AccountType(str, enum.Enum):      # فاز ۲۷
    BANK = "bank"
    EXCHANGE = "exchange"
    CRYPTO_WALLET = "crypto_wallet"

class Currency(str, enum.Enum):
    IRR = "IRR"
    USD = "USD"

class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    EXCHANGE = "exchange"
    CONVERSION = "conversion"          # فاز ۳۷

class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    EXCHANGE = "exchange"
    PROFIT = "profit"
    LOSS = "loss"
    FEE = "fee"
    PURCHASE = "purchase"
    TRANSFER = "transfer"              # فاز ۳۷
    ADJUSTMENT = "adjustment"          # فاز ۳۷
```

| Enum | محل‌های استفاده | نتیجه |
|:---|:---|:---|
| `AccountType` | `FinancialAccount.type` | ❌ **ناقص** (CARD/CASH/TRUST_WALLET گم) |
| `Currency` | `FinancialAccount`, `FinancialTransaction`, `PropWithdrawal`, `PersonalTradingAccount`, `Broker` | ✅ Enum (اما `PropAccount`/`PropCost` String) |
| `CategoryType` | `Category.type` | ✅ کامل |
| `TransactionType` | `FinancialTransaction.type` | ✅ کامل |

---

## ۵. Prop Models — وضعیت فعلی

| مدل | ستون | نوع فعلی | مسئله |
|:---|:---|:---|:---|
| `PropAccount` | `currency` | **String** (default "USD") | 🟠 نه Enum |
| `PropCost` | `currency` | **String** (default "USD") | 🟠 نه Enum |
| `PropCost` | `cost_type` | **String** (NOT NULL) | 🟠 نه Enum — مقدار آزاد |
| `PropAlert` | `is_read` | **Integer** (default 0) | 🟡 نه Boolean |
| `PropWithdrawal` | `currency` | `Enum(Currency)` | ✅ (فاز ۳۳) |

### نکتهٔ حیاتی `cost_type`
در `api/prop.py:1106`:
```python
is_purchase = cost.create_transaction and (cost.cost_type or "").lower() == "purchase"
```
⇒ مقادیر فعلی **lowercase** هستند (`"purchase"`). اگر Enum با ذخیرهٔ **NAME** (`"PURCHASE"`) ساخته شود،
**داده‌های قدیمی می‌شکنند**. راه‌حل: `values_callable` برای ذخیرهٔ **value** (lowercase).

---

## ۶. داده واقعی در DB (خروجی خام)

```
=== accounts ===          count: 0  (id,name,type VARCHAR(13),currency VARCHAR(3),balance FLOAT,card_number,created_at)
=== transactions ===      count: 0
=== prop_accounts ===     count: 1   currencies: [('USD',)]
=== prop_costs ===        count: 0   currencies: []   cost_types: []
=== prop_alerts ===       count: 0   is_read values: []
```

✅ **نتیجه:** صفر داده در FINANCE و صفر در `prop_costs`/`prop_alerts` ⇒ مهاجرت نوع ستون‌ها
**بدون ریسک data loss**. تنها `prop_accounts` یک ردیف `'USD'` دارد که با `Enum(Currency)`
(NAME = `'USD'`) **سازگار** است.

---

## ۷. DateTimeها — نوع‌ها

### Naive — `DateTime` (بدون timezone) — ~۲۶ ستون
| فایل | موارد |
|:---|:---|
| `finance.py` | `FinancialAccount.created_at` · `Category.created_at` · `FinancialTransaction.date/created_at` |
| `prop.py` | `PropFirm/PropFirmDefaultRules/PropAccount.created_at` · `PropStage.start_date/end_date/created_at` · `PropCost.cost_date` · `PropAlert.created_at` |
| `strategy.py` | `Strategy/StrategyVersion/Trade/CustomTimeInterval/TimePoint/AnalysisResult.created_at` |
| `personal.py` | `JournalReview.created_at` · `Screenshot.uploaded_at` |
| `settings.py` | `UserSettings.updated_at` |

### Timezone-aware — `DateTime(timezone=True)` — ~۱۴ ستون
| فایل | موارد |
|:---|:---|
| `imports.py` | `ImportProfile.created_at` · `ImportBatch.started_at/completed_at` · `ImportIdentity.open_time/close_time` |
| `strategy.py` | `Trade.open_time/close_time` · `AnalysisRun.created_at` · `AnalysisScopeRecord.from_date/to_date/created_at` |
| `prop.py` | `PropWithdrawal.withdrawal_date/created_at` · `RuleViolation.occurred_at` |
| `trading.py` | `Broker.created_at` · `PersonalTradingAccount.created_at` |

> ⚠️ `prop.py` و `strategy.py` **هر دو نوع** را در خود دارند ⇒ ناسازگاری درون‌فایلی.

---

## ۸. Migrationهای مرتبط

| فایل | ارتباط |
|:---|:---|
| `51ea09b4aa3d_add_finance_tables.py` | ساخت `accounts`+`transactions` با `sa.Enum('IRR','USD', name='currency')` |
| `9f1a2b3c4d5e_merge_personal_into_finance.py` | ادغام `personal_accounts`→`accounts` و `ledger_transactions`→`transactions` |
| `b7d4e19c2f83_link_prop_to_finance.py` | پل `PropAccount.finance_account_id` (بعداً حذف شد) |
| `c3d4e5f6a7b8_phase28_finance_cleanup.py` | حذف فیلدهای مالی قدیمی از `accounts` |
| `c4838cd01bbd_initial_schema_with_trade_hash.py` | ساخت اولیهٔ `prop_costs` (`cost_type String`) و `prop_alerts` (`is_read Integer`) |
| `a7b8c9d0e1f2_phase33_prop_withdrawal.py` | `PropWithdrawal.currency → Enum(Currency)` |
| `c9d0e1f2a3b4_phase36_indexes.py` | ایندکس‌های `account_id`/`date`/`type` |

> ✅ هیچ migration فعلی روی `prop_accounts.currency` / `prop_costs.cost_type` / `prop_alerts.is_read` کار نکرده.

---

## ۹. تست‌های مرتبط

| فایل | ارجاعات | موضوع |
|:---|---:|:---|
| `test_finance.py` | ۸۴ | هستهٔ مالی |
| `test_phase37_finance_rename.py` | ۴۳ | rename + Enum جدید |
| `test_phase33_withdrawal.py` | ۳۷ | برداشت پراپ + درآمد |
| `test_phase36_performance.py` | ۲۶ | ایندکس + bulk |
| `test_soft_delete_filters.py` | ۲۱ | soft delete |
| `test_trading_domain.py` | ۲۱ | PersonalTradingAccount |
| `test_analysis_phase23.py` | ۲۱ | analysis |
| `test_import_engine.py` | ۲۱ | import |
| `test_prop.py` | ۹ | prop core |
| سایر | ~۱۶ | — |

**جمع تست‌های فعلی پروژه: ۱۷۶**

---

## ۱۰. Gap Analysis vs Master Plan

| مورد Master Plan | وضعیت | فاصله |
|:---|:---:|:---|
| `FinancialAccount` برای Bank/Card/Cash/Trust Wallet/Exchange Wallet | ⚠️ جزئی | `AccountType` فاقد `CARD`/`CASH`/`TRUST_WALLET` |
| `FinancialTransaction` با Income/Expense/Transfer/Conversion/Adjustment | ✅ | کامل (۹ نوع) |
| `Currency` به‌صورت Enum نه String | ⚠️ جزئی | `PropAccount.currency` · `PropCost.currency` هنوز String |
| `Category` طبقه‌بندی | ✅ | کامل (۵ نوع) |
| `cost_type` نوعدار | ❌ | String آزاد |
| `is_read` Boolean | ❌ | Integer |
| مبالغ `Numeric` | ❌ | همه `Float` |
| `DateTime` یکسان | ❌ | naive/aware مخلوط |

---

## ۱۱. پیشنهاد ۵ تغییر برای Phase 38 (تأییدشده)

| # | تغییر | فایل | ریسک |
|:--|:---|:---|:---:|
| ۱ | `AccountType` + `CARD`, `CASH`, `TRUST_WALLET` | `models/finance.py` | 🟢 صفر |
| ۲ | `PropAccount.currency` → `Enum(Currency)` | `models/prop.py` | 🟢 صفر (NAME='USD' سازگار) |
| ۳ | `PropCost.currency` → `Enum(Currency)` | `models/prop.py` | 🟢 صفر |
| ۴ | `PropCost.cost_type` → `Enum(CostType)` با `values_callable` (lowercase) | `models/prop.py` | 🟡 نیازمند mapping مقادیر قدیمی |
| ۵ | `PropAlert.is_read` → `Boolean` | `models/prop.py` | 🟢 صفر (0/1 سازگار) |

**خارج از دامنه (فازهای بعدی):** `Float → Numeric(18,2)` و یکسان‌سازی `DateTime(timezone=True)`.

---

## ۱۲. ریسک‌ها و سؤالات باز

| ریسک | احتمال | تأثیر | کاهش |
|:---|:---:|:---:|:---|
| دادهٔ `cost_type` قدیمی با مقدار ناشناخته در DB کاربر | کم | متوسط | `values_callable` + fallback به `other` |
| `PropAlert.is_read` = مقادیر غیر ۰/۱ | کم | کم | SQLite Boolean هر عددی را ۰/۱ تفسیر می‌کند |
| فرانت‌اند به `is_read: 0/1` عادت کرده | کم | کم | JSON boolean در JS truthy بررسی می‌شود ⇒ سازگار |
| `AccountType` جدید در dropdown فرانت نباشد | متوسط | کم | افزودن گزینه در فاز فرانت‌اند |
| migration لازم شود (CHECK constraint) | کم | کم | SQLAlchemy `create_constraint` پیش‌فرض `False` |

### سؤالات باز
1. آیا `CASH` حساب نقدی مستقل باشد یا زیرمجموعهٔ بانک؟ (پیشنهاد: مستقل)
2. آیا `TRUST_WALLET` از `CRYPTO_WALLET` جدا شود؟ (پیشنهاد: بله)
3. `cost_type` ناشناخته ⇒ `other` یا خطا؟ (پیشنهاد: `other` + لاگ)

---

## ⛔ پایان Audit — آماده برای Phase 38 Implementation


