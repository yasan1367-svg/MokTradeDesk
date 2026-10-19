# 💰 PHASE 37 — Financial Rename & Enum Extension · IMPLEMENTATION REPORT

> **وضعیت:** ✅ کامل (Rename + Alias + Enums + Tests)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **Revision:** `c9d0e1f2a3b4` — **بدون تغییر** (هیچ migration لازم نبود)
> **خروجی تست:** `176 passed` (۱۶۷ قبلی + ۹ جدید) · `tsc EXIT=0`

---

## ۱. خلاصهٔ اجرایی

| خواستهٔ فاز ۳۷ | پیاده‌سازی |
|:---|:---|
| `Account` → `FinancialAccount` | ✅ نام کلاس؛ `__tablename__` **بدون تغییر** (`accounts`) |
| `Transaction` → `FinancialTransaction` | ✅ نام کلاس؛ `__tablename__` **بدون تغییر** (`transactions`) |
| `CategoryType` + `CONVERSION` | ✅ (`EXCHANGE` برای سازگاری نگه داشته شد) |
| `TransactionType` + `TRANSFER` + `ADJUSTMENT` | ✅ |
| بدون جدول جدید | ✅ |
| بدون دو منبع حقیقت | ✅ (alias همان کلاس را برمی‌گرداند: `Account is FinancialAccount`) |
| alias سازگاری | ✅ در انتهای `models/finance.py` |
| همهٔ ۱۶۷ تست پاس | ✅ (`176 passed` = ۱۶۷ + ۹ جدید) |

---

## ۲. تغییرات فایل‌به‌فایل

### ۲.۱ `backend/app/models/finance.py`
**همین فایل مرجع (source of truth) است.**

- `class Account(Base)` → `class FinancialAccount(Base)` + آپدیت ۶ relationship string:
  `"Transaction"` ×۳ و `"Transaction.from_account_id/to_account_id/account_id"` → `FinancialTransaction`.
- `class Transaction(Base)` → `class FinancialTransaction(Base)` + آپدیت ۳ relationship string:
  `"Account"` ×۳ → `"FinancialAccount"`.
- `Category.transactions` relationship: `"Transaction"` → `"FinancialTransaction"`.
- Enumها:

```python
class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    EXCHANGE = "exchange"        # نگه‌داشته شد (سازگاری)
    CONVERSION = "conversion"    # ← فاز ۳۷

class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    EXCHANGE = "exchange"
    PROFIT = "profit"
    LOSS = "loss"
    FEE = "fee"
    PURCHASE = "purchase"
    TRANSFER = "transfer"        # ← فاز ۳۷
    ADJUSTMENT = "adjustment"    # ← فاز ۳۷
```

- Aliasهای سازگاری در انتهای فایل:

```python
# فاز ۳۷ — aliasهای سازگاری (Backward Compatibility)
Account = FinancialAccount
Transaction = FinancialTransaction
```

### ۲.۲ `backend/app/models/prop.py`
- `PropWithdrawal.destination_account` → `relationship("FinancialAccount", ...)`
- `PropWithdrawal.financial_transaction` → `relationship("FinancialTransaction", ...)`

> ⚠️ این ۲ رشته حیاتی بودند: SQLAlchemy registry بر اساس **نام واقعی کلاس** کار می‌کند
> (نه alias)؛ اگر آپدیت نمی‌شدند، `InvalidRequestError` در زمان اولین کوئری رخ می‌داد.

### ۲.۳ مصرف‌کننده‌ها — rename کامل (۲۳۷ جایگزینی)

اجرای یک rename با **word-boundary** (`\bAccount\b` / `\bTransaction\b`) با **backup ایمنی**
(به‌دلیل کامیت‌نبودن Phase 36):

| فایل | Account | Transaction |
|:---|---:|---:|
| `app/api/finance.py` | ۲۳ | ۱۴۲ |
| `app/api/prop.py` | ۴ | ۲ |
| `app/api/broker.py` | ۷ | ۱۸ |
| `app/api/analytics.py` | ۴ | ۱ |
| `app/services/payout_service.py` | ۱۵ | ۱۵ |
| `migrations/env.py` | ۱ | ۱ |
| `benchmarks/bench_phase36.py` | ۲ | ۲ |
| **جمع** | **۵۶** | **۱۸۱** |

> ✅ متغیرهای lowercase (`account`, `account_id`, `db_account`) **دست‌نخورده** ماندند
> (regex در Python case-sensitive است). بررسی نهایی: **صفر** مورد case-sensitive باقی‌مانده.

### ۲.۴ فایل جدید: `backend/tests/test_phase37_finance_rename.py` (۹ تست)

| تست | پوشش |
|:---|:---|
| `test_aliases_are_identical` | `Account is FinancialAccount` · `Transaction is FinancialTransaction` |
| `test_tablenames_unchanged_no_migration` | `accounts` / `transactions` / `categories` ثابت |
| `test_fk_targets_still_point_to_accounts` | FKها هنوز به `accounts.id`/`categories.id` |
| `test_category_type_has_conversion_and_keeps_exchange` | `CONVERSION` + نگهداشت `EXCHANGE` |
| `test_transaction_type_has_transfer_and_adjustment` | `TRANSFER`/`ADJUSTMENT` + ۷ مقدار قبلی |
| `test_relationships_with_renamed_classes` | relationshipهای دوطرفه با نام جدید (۵ assert) |
| `test_new_enum_values_are_persistable` | ذخیرهٔ واقعی `ADJUSTMENT` + `CONVERSION` |
| `test_finance_endpoints_still_work_after_rename` | endpointها + `total_income` + نوع جدید `adjustment` |
| `test_category_crud_with_conversion` | CRUD دسته‌بندی با `conversion` |

---

## ۳. پاسخ به سؤالات ریسک (نتیجهٔ عملی)

| # | سؤال | نتیجهٔ عملی |
|:--|:---|:---|
| ۱ | تداخل با `sqlalchemy.Transaction`؟ | ❌ رخ نداد؛ `mapper`ها بدون خطا configure شدند |
| ۲ | تداخل Pydantic؟ | ❌ رخ نداد؛ `AccountCreate`/`TransactionCreate` مستقل کار می‌کنند |
| ۳ | `__tablename__` عوض شود؟ | ❌ عوض **نشد** ⇒ صفر DDL |
| ۴ | شکستن FK؟ | ❌ هیچ FK نشکست (۳ FK داخلی + ۲ FK از `prop_withdrawals` سالم) |
| ۵ | Enumها | ✅ `CONVERSION` + `TRANSFER` + `ADJUSTMENT` اضافه شد |
| ۶ | Frontend | ✅ **صفر تغییر** — `tsc EXIT=0` بدون ویرایش فرانت |
| ۷ | دادهٔ DB | ✅ صفر ردیف ⇒ ریسک صفر |

---

## ۴. اعتبارسنجی

```text
pytest (کل مجموعه) ....................................... 176 passed (EXIT=0)
pytest tests/test_phase37_finance_rename.py .............. 9 passed
python -c "configure_mappers()" .......................... mappers OK
alembic heads ............................................ c9d0e1f2a3b4 (بدون تغییر)
frontend: npx tsc -b --force ............................. TSC_EXIT=0
grep case-sensitive '\bAccount\b|\bTransaction\b' (۷ فایل) صفر باقی‌مانده
```

---

## ۵. یادداشت‌های طراحی

1. **alias دائمی نیست:** `Account = FinancialAccount` تا فاز ۳۸ حفظ می‌شود؛ پس از آن با
   اطمینان از پوشش کامل، حذف می‌گردد.
2. **دو نام هم‌ارز:** از این پس هم `FinancialAccount` و هم `Account` قابل import هستند و
   **به یک کلاس** اشاره می‌کنند ⇒ «دو منبع حقیقت» ایجاد نشده است.
3. **بدون migration:** چون `__tablename__` ثابت ماند، `alembic head` دست‌نخورده است.
   در صورت مهاجرت آینده به Postgres، افزودن مقادیر Enum نیازمند `ALTER TYPE ... ADD VALUE` خواهد بود.
4. **تست‌ها با نام قدیمی هم کار می‌کنند** (alias) — به همین دلیل ۱۶۷ تست قبلی بدون تغییر پاس شدند.
5. **باقی‌مانده (عمدی):** تست‌ها همچنان از alias قدیمی استفاده می‌کنند؛ به‌روزرسانی آن‌ها
   اختیاری و در فاز بعد انجام می‌شود.

---

## ۶. یادآوری دربارهٔ وضعیت Git

⚠️ working tree همچنان شامل **کار کامیت‌نشدهٔ Phase 36** بود (و اکنون Phase 37 هم اضافه شده).
پیشنهاد: پیش از فاز ۳۸ یک commit با پیام مثلاً:
`Phase 36-37: Performance indexes + Financial rename & enum extension`

---

## ۷. گام بعدی پیشنهادی
- **Phase 38 (Financial Precision):** مهاجرت `Float → Numeric(18,2)` برای مبالغ مالی.
  (DB لوکال خالی است ⇒ ریسک پایین؛ اما برای DB کاربر باید backup + backfill انجام شود.)
- افزودن `CategoryType.CONVERSION` به seed پیش‌فرض دسته‌بندی‌ها.
- به‌روزرسانی تدریجی importهای تست‌ها به نام جدید.

