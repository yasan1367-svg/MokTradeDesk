# 💰 PHASE 38 — Personal Finance Foundation · IMPLEMENTATION REPORT

> **وضعیت:** ✅ کامل (Enums + Type-safe Columns + Tests)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **Revision:** `c9d0e1f2a3b4` — **بدون تغییر** (هیچ migration لازم نبود)
> **خروجی تست:** `188 passed` (۱۷۶ قبلی + ۱۲ جدید) · `tsc EXIT=0`

---

## ۱. خلاصهٔ اجرایی

| # | خواستهٔ فاز ۳۸ | پیاده‌سازی |
|:--|:---|:---|
| ۱ | `AccountType` + `CARD`/`CASH`/`TRUST_WALLET` | ✅ |
| ۲ | `PropAccount.currency` String → `Enum(Currency)` | ✅ |
| ۳ | `PropCost.currency` String → `Enum(Currency)` | ✅ |
| ۴ | `PropCost.cost_type` String → `Enum(CostType)` | ✅ (با ذخیرهٔ **lowercase**) |
| ۵ | `PropAlert.is_read` Integer → `Boolean` | ✅ |
| — | بدون جدول جدید / بدون دو منبع حقیقت | ✅ |
| — | Migration | ✅ **لازم نبود** |

---

## ۲. تغییرات فایل‌به‌فایل

### ۲.۱ `backend/app/models/finance.py` — `AccountType`
```python
class AccountType(str, enum.Enum):
    BANK = "bank"
    EXCHANGE = "exchange"
    CRYPTO_WALLET = "crypto_wallet"
    CARD = "card"                  # ← فاز ۳۸
    CASH = "cash"                  # ← فاز ۳۸
    TRUST_WALLET = "trust_wallet"  # ← فاز ۳۸
```
> پشتیبانی کامل Master Plan: Bank / Card / Cash / Trust Wallet / Exchange Wallet / Crypto Wallet.

### ۲.۲ `backend/app/models/prop.py`

**الف) enum جدید `CostType` + helper:**
```python
class CostType(str, enum.Enum):
    """توجه: مقدار در DB به‌صورت value (lowercase) ذخیره می‌شود، نه NAME."""
    PURCHASE = "purchase"
    RESET = "reset"
    ADDON = "addon"
    DATA_FEE = "data_fee"
    REFUND = "refund"
    OTHER = "other"


def _enum_values(enum_cls):
    """SQLAlchemy `values_callable`: ذخیرهٔ value (lowercase) به‌جای NAME."""
    return [e.value for e in enum_cls]
```

**ب) `PropAccount.currency`:**
```python
# قبل: currency = Column(String, default="USD")
currency = Column(Enum(Currency), default=Currency.USD)
```

**ج) `PropCost`:**
```python
cost_type = Column(
    Enum(CostType, values_callable=_enum_values),
    nullable=False, default=CostType.OTHER,
)
currency = Column(Enum(Currency), default=Currency.USD)
```

**د) `PropAlert`:**
```python
# قبل: is_read = Column(Integer, default=0)
is_read = Column(Boolean, default=False)
```

**ه) import:** افزودن `Boolean` به importهای SQLAlchemy.

### ۲.۳ `backend/app/api/prop.py`
- import `CostType`.
- `create_cost` — `cost_type` نوعدار با پیام خطای فارسی:
```python
try:
    cost_type = CostType((cost.cost_type or "").strip().lower())
except ValueError:
    raise HTTPException(400, detail="نوع هزینه نامعتبر است (مجاز: ...)")

is_purchase = cost.create_transaction and cost_type == CostType.PURCHASE
...
db_cost = PropCost(
    prop_account_id=cost.prop_account_id,
    cost_type=cost_type,
    amount=cost.amount,
    currency=_to_currency(cost.currency),   # ← String → Enum
    description=cost.description,
)
```
- `create_account` (پراپ) — `currency=_to_currency(account.currency)`.
- `PropAlert.is_read == 0` → `== False` (**۶ مورد**) و `alert.is_read = 1` → `= True` (**۱ مورد**).

---

## ۳. تصمیم کلیدی — ذخیرهٔ lowercase برای `cost_type`

| رویکرد | مقدار ذخیره‌شده | سازگاری با دادهٔ قدیمی (`"purchase"`) |
|:---|:---|:---:|
| `Enum(CostType)` پیش‌فرض (NAME) | `"PURCHASE"` | ❌ می‌شکند |
| **`Enum(CostType, values_callable=...)`** | **`"purchase"`** | ✅ **سازگار** |

دلیل: قرارداد فعلی API/کد `(cost_type or "").lower() == "purchase"` است ⇒ مقدار lowercase
ذخیره می‌شد. با `values_callable` این قرارداد و دادهٔ قدیمی حفظ می‌شود.

---

## ۴. بدون Migration

| ستون | نوع DB فعلی | نوع جدید | سازگار؟ |
|:---|:---|:---|:---:|
| `accounts.type` | `VARCHAR(13)` | `Enum(AccountType)` (مقادیر بیشتر) | ✅ |
| `prop_accounts.currency` | `VARCHAR` | `Enum(Currency)` (NAME='USD'/'IRR') | ✅ |
| `prop_costs.currency` | `VARCHAR` | `Enum(Currency)` | ✅ |
| `prop_costs.cost_type` | `VARCHAR NOT NULL` | `Enum(CostType)` (lowercase) | ✅ |
| `prop_alerts.is_read` | `INTEGER` | `Boolean` (0/1) | ✅ |

> SQLAlchemy `Enum.create_constraint` پیش‌فرض **False** است ⇒ هیچ CHECK constraint روی SQLite
> ساخته نمی‌شود ⇒ افزودن مقادیر جدید بدون DDL کار می‌کند.
> ✅ `alembic head` همچنان `c9d0e1f2a3b4` است.

---

## ۵. تست‌ها — `backend/tests/test_phase38_personal_finance.py` (۱۲ تست)

| تست | پوشش |
|:---|:---|
| `test_account_type_new_values_added` | `card`/`cash`/`trust_wallet` + حفظ ۳ مقدار قبلی |
| `test_account_type_works_via_api` | ساخت حساب مالی با هر ۳ نوع جدید |
| `test_cost_type_values` | دقیقاً ۶ مقدار `CostType` |
| `test_cost_type_column_is_enum` | ستون `Enum` با `purchase` در enums |
| `test_cost_type_stored_lowercase_in_db` | ورودی `"RESET"` ⇒ ذخیرهٔ `"reset"` در DB (raw SQL) |
| `test_cost_type_invalid_rejected` | مقدار نامعتبر ⇒ `400` |
| `test_prop_account_currency_is_enum` | ستون `Enum(Currency)` |
| `test_prop_cost_currency_is_enum` | ستون `Enum(Currency)` |
| `test_prop_account_currency_persists` | ساخت پراپ با `IRR` ⇒ `Currency.IRR` در DB |
| `test_purchase_cost_creates_typed_transaction` | `purchase` ⇒ `CostType.PURCHASE` + تراکنش مالی |
| `test_prop_alert_is_read_is_boolean` | نوع ستون `Boolean` |
| `test_prop_alert_mark_read_flow` | `False` → PATCH → `True` (DB + API) |

---

## ۶. اعتبارسنجی

```text
pytest (کل مجموعه) ....................................... 188 passed (EXIT=0)
pytest tests/test_phase38_personal_finance.py ............ 12 passed
python -c "configure_mappers()" .......................... mappers OK
alembic heads ............................................ c9d0e1f2a3b4 (بدون تغییر)
frontend: npx tsc -b --force ............................. TSC_EXIT=0
```

---

## ۷. سازگاری (Backward Compatibility)

| مصرف‌کننده | تأثیر |
|:---|:---|
| `GET/POST /api/finance/accounts` | ✅ بدون تغییر (JSON `type` = `"card"`/`"cash"`/...) |
| `POST /api/prop/costs` | ✅ ورودی‌های `"purchase"` (lowercase) دست‌نخورده کار می‌کنند + Uppercase هم پذیرفته می‌شود |
| `GET /api/prop/alerts` | ⚠️ `is_read` اکنون `true/false` به‌جای `0/1` — در JS هر دو truthy یکسان‌اند |
| فرانت‌اند | ✅ `tsc EXIT=0`؛ اما dropdown `AccountType` در `FinancePage` باید ۳ گزینهٔ جدید را اضافه کند (فاز فرانت) |

---

## ۸. یادداشت‌ها

1. **`values_callable` استثنای آگاهانه:** تنها `cost_type` است که value (lowercase) ذخیره می‌کند؛
   بقیهٔ Enumها طبق قرارداد پروژه NAME ذخیره می‌کنند. علت: سازگاری با داده/قرارداد قبلی.
2. **`Currency` NAME == value** ⇒ تغییر String → Enum برای `PropAccount`/`PropCost` بدون هیچ
   مهاجرت داده‌ای کار می‌کند.
3. **خارج از دامنه (فاز بعدی):**
   - `Float → Numeric(18,2)` برای دقت پول.
   - یکسان‌سازی `DateTime(timezone=True)` (~۲۶ ستون naive).
   - افزودن ۳ گزینهٔ `AccountType` به dropdown فرانت‌اند.
4. **Git:** فاز ۳۶/۳۷ توسط کاربر کامیت شد (`619ffd2`). working tree فعلی فقط شامل
   تغییرات فاز ۳۸ است (۳ فایل modified + ۳ فایل جدید).

---

## ۹. گام بعدی پیشنهادی

- **Phase 38.2 (اختیاری):** فرانت‌اند — افزودن `card`/`cash`/`trust_wallet` به dropdown نوع حساب.
- **Phase 39 (Financial Precision):** `Float → Numeric(18,2)` + یکسان‌سازی DateTime.

