# 📋 PLAN_PHASE37.md — Phase 37: Financial Rename & Enum Extension

> **نوع سند:** Plan + نتیجهٔ تحلیل (این سند پیش از شروع اجرا نوشته شد)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **پیش‌نیاز:** `BASELINE_REPORT.md` (Phase 0 Audit)
> **گزینهٔ منتخب کاربر:** 🟢 **گزینه B (متعادل)** — rename + alias + enum، بدون جدول جدید

---

## ۱. خلاصهٔ اجرایی

| اقدام | جزئیات |
|:---|:---|
| `Account` → `FinancialAccount` | نام **کلاس Python**؛ `__tablename__` = `"accounts"` **بدون تغییر** |
| `Transaction` → `FinancialTransaction` | نام **کلاس Python**؛ `__tablename__` = `"transactions"` **بدون تغییر** |
| `CategoryType` | + `CONVERSION` (نگهداشت `EXCHANGE` برای دادهٔ قدیمی) |
| `TransactionType` | + `TRANSFER` + `ADJUSTMENT` |
| Alias سازگاری | `Account = FinancialAccount` · `Transaction = FinancialTransaction` |
| Migration | **لازم نیست** (بدون تغییر schema؛ SQLite `VARCHAR` بدون CHECK سختگیر) |
| API / Frontend | **صفر تغییر** (pathها و کلیدهای JSON ثابت) |

---

## ۲. پاسخ به ۷ سؤال ریسک (خلاصهٔ تحلیل)

| # | سؤال | پاسخ |
|:--|:---|:---|
| ۱ | تداخل با `sqlalchemy.Transaction`؟ | ❌ خیر — namespace متفاوت (`sqlalchemy.engine.base`). تغییر نام یک بهبود است نه رفع باگ. |
| ۲ | تداخل با Pydantic Schemas؟ | ❌ خیر — `AccountCreate`/`TransactionCreate` در `api/finance.py` کلاس‌های مستقل `BaseModel`اند. |
| ۳ | تغییر `__tablename__`؟ | ❌ **خیر** — با تغییر نام جدول، در SQLite نیاز به rebuild + شکستن FKها می‌شد. |
| ۴ | FKها؟ | ۵ FK داخلی (`Transaction.account_id/from_account_id/to_account_id`) + `prop_withdrawals.destination_account_id` + `prop_withdrawals.transaction_id`. با ثابت‌ماندن `__tablename__` **هیچ‌کدام نمی‌شکنند**. |
| ۵ | Enumها | `TransactionType` بدون `TRANSFER`/`ADJUSTMENT` · `CategoryType` بدون `CONVERSION` · `EXCHANGE` در **هر دو** موجود است. |
| ۶ | Frontend | ✅ صفر — فرانت فقط API path و JSON key مصرف می‌کند. |
| ۷ | دادهٔ DB | `accounts = 0` · `transactions = 0` ⇒ ریسک data loss **صفر**. |

---

## ۳. فایل‌های درگیر (با تعداد ارجاع)

### ۳.۱ ارجاعات `Account` (بدون PropAccount/TradingAccount · بدون venv)
| فایل | تعداد |
|:---|---:|
| `app/api/finance.py` | ۴۱ |
| `app/api/prop.py` | ۲۷ |
| `app/services/payout_service.py` | ۱۰ |
| `app/api/broker.py` | ۶ |
| `app/api/analytics.py` | ۶ (alias: `FinAccount`/`FinanceAccount`) |
| `app/models/finance.py` | ۵ |
| `app/models/prop.py` | ۳ (relationship strings) |
| `tests/*` (۵ فایل) | ~۱۵ |
| `benchmarks/bench_phase36.py` | ۱ |

### ۳.۲ ارجاعات `Transaction`
`api/finance.py` (~۴۵) · `services/payout_service.py` (~۲۰) · `api/prop.py` (~۱۵) ·
`api/analytics.py` (~۱۰) · `api/broker.py` · `tests/*` (~۲۴)

### ۳.۳ Importهای مستقیم `models.finance` (۱۱ فایل)
```
app/api/finance.py            app/api/prop.py          app/api/broker.py
app/api/analytics.py          app/api/trading.py       app/services/payout_service.py
migrations/env.py             benchmarks/bench_phase36.py
tests/test_finance.py         tests/test_phase33_withdrawal.py   tests/test_phase36_performance.py
tests/test_import_engine.py   tests/test_analysis_phase23.py
tests/test_analysis_scope.py  tests/test_soft_delete_filters.py  tests/test_trading_domain.py
```

### ۳.۴ Relationship strings که **باید** عوض شوند (نکتهٔ حیاتی)
| فایل | رشتهٔ فعلی | رشتهٔ جدید |
|:---|:---|:---|
| `models/finance.py` (Account) | `"Transaction"` ×۳ | `"FinancialTransaction"` |
| `models/finance.py` (Category) | `"Transaction"` ×۱ | `"FinancialTransaction"` |
| `models/finance.py` (Transaction) | `"Account"` ×۳ | `"FinancialAccount"` |
| `models/prop.py` (PropWithdrawal) | `"Account"` ×۱ | `"FinancialAccount"` |
| `models/prop.py` (PropWithdrawal) | `"Transaction"` ×۱ | `"FinancialTransaction"` |

> ⚠️ **SQLAlchemy registry بر اساس نام واقعی کلاس کار می‌کند، نه alias.** اگر رشته‌ها آپدیت نشوند،
> `InvalidRequestError` در زمان اولین کوئری رخ می‌دهد.

---

## ۴. سه گزینه (تحلیل)

| معیار | 🟢 A (alias only) | 🟡 **B (متعادل) — منتخب** | 🔴 C (clean break) |
|:---|:---|:---|:---|
| تمیزی کد | کم | خوب | کامل |
| `__tablename__` | ثابت | **ثابت** | عوض می‌شود |
| Migration | ❌ ندارد | سبک/ندارد | سنگین (rebuild) |
| ریسک data loss | صفر | **صفر** (DB خالی + بدون rename جدول) | بالا |
| تأثیر تست‌ها | صفر | **صفر** (alias) | نیاز به بازنویسی |
| زمان | ~۳۰ دقیقه | **~۲ ساعت** | ۱-۲ روز |
| سازگاری با Phase 38 (Precision) | ضعیف | **خوب** | خوب |

---

## ۵. توصیه

**گزینه B.** دلایل:
1. **صفر ریسک data loss** — `__tablename__` ثابت می‌ماند و DB لوکال خالی است.
2. **صفر تغییر API/Frontend** — مصرف‌کننده‌ها دست‌نخورده می‌مانند.
3. **۱۶۷ تست بدون تغییر پاس می‌مانند** — به‌لطف alias.
4. **سازگار با Phase 38** — نام‌گذاری `FinancialAccount`/`FinancialTransaction` بستر
   صحیح برای افزودن `Numeric` (دقت پول) بدون ابهام دامنه است.
5. **قابل بازگشت** — اگر مشکلی رخ داد، فقط نام کلاس‌ها برمی‌گردد؛ DB اصلاً دست نخورده است.

---

## ۶. نقشهٔ گام‌به‌گام (گزینه B)

### گام ۱ — `models/finance.py`: rename کلاس‌ها + آپدیت relationship strings

**قبل:**
```python
class Account(Base):
    """حساب مالی (بانکی، صرافی، بروکر، پراپ، کیف‌پول)"""
    __tablename__ = "accounts"
    ...
    transactions_out = relationship("Transaction", foreign_keys="Transaction.from_account_id", ...)
    transactions_in  = relationship("Transaction", foreign_keys="Transaction.to_account_id", ...)
    entries          = relationship("Transaction", foreign_keys="Transaction.account_id", ...)

class Category(Base):
    transactions = relationship("Transaction", back_populates="category")

class Transaction(Base):
    __tablename__ = "transactions"
    ...
    account      = relationship("Account", foreign_keys=[account_id], back_populates="entries")
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transactions_out")
    to_account   = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_in")
```

**بعد:**
```python
class FinancialAccount(Base):
    """حساب مالی (بانکی، صرافی، کیف‌پول) — فاز ۳۷: rename؛ جدول همان `accounts`."""
    __tablename__ = "accounts"
    ...
    transactions_out = relationship("FinancialTransaction", foreign_keys="FinancialTransaction.from_account_id", ...)
    transactions_in  = relationship("FinancialTransaction", foreign_keys="FinancialTransaction.to_account_id", ...)
    entries          = relationship("FinancialTransaction", foreign_keys="FinancialTransaction.account_id", ...)

class Category(Base):
    transactions = relationship("FinancialTransaction", back_populates="category")

class FinancialTransaction(Base):
    __tablename__ = "transactions"
    ...
    account      = relationship("FinancialAccount", foreign_keys=[account_id], back_populates="entries")
    from_account = relationship("FinancialAccount", foreign_keys=[from_account_id], back_populates="transactions_out")
    to_account   = relationship("FinancialAccount", foreign_keys=[to_account_id], back_populates="transactions_in")

# ── فاز ۳۷: aliasهای سازگاری ──
Account = FinancialAccount
Transaction = FinancialTransaction
```

### گام ۲ — `models/prop.py`: آپدیت relationship stringها
```python
    destination_account   = relationship("FinancialAccount", foreign_keys=[destination_account_id])
    financial_transaction = relationship("FinancialTransaction", foreign_keys=[transaction_id])
```

### گام ۳ — Enumها (`models/finance.py`)
```python
class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    EXCHANGE = "exchange"       # نگه‌داشته می‌شود (داده/کد قدیمی)
    CONVERSION = "conversion"   # ← جدید فاز ۳۷

class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    EXCHANGE = "exchange"
    PROFIT = "profit"
    LOSS = "loss"
    FEE = "fee"
    PURCHASE = "purchase"
    TRANSFER = "transfer"       # ← جدید: انتقال بین حساب‌ها (درآمد/هزینه نیست)
    ADJUSTMENT = "adjustment"   # ← جدید: اصلاح دستی موجودی
```

### گام ۴ — Migration
**لازم نیست.** دلایل:
- `__tablename__` عوض نمی‌شود ⇒ هیچ rebuild/FK تغییری لازم نیست.
- ستون‌های `type`/`category.type` در SQLite به‌صورت `VARCHAR` ذخیره می‌شوند و
  SQLAlchemy برای Enumهای پروژه `CHECK constraint` سختگیر نمی‌سازد ⇒ مقادیر جدید بدون DDL کار می‌کنند.
- `alembic head` فعلی (`c9d0e1f2a3b4`) **دست‌نخورده** می‌ماند.

> اگر در آینده مهاجرت به Postgres مطرح شد، افزودن مقادیر Enum آنجا نیازمند `ALTER TYPE ... ADD VALUE` خواهد بود.

### گام ۵ — به‌روزرسانی importها (تمیزکاری)
alias تمام importهای قدیمی را زنده نگه می‌دارد. برای «تمیزی واقعی»، importهای فایل‌های اصلی
به نام جدید به‌روز می‌شوند؛ بقیه در فاز بعد.

### گام ۶ — تست و تأیید
```shell
# ۱) سلامت import
venv\Scripts\python.exe -c "import app.main; from app.models.finance import FinancialAccount, FinancialTransaction, Account, Transaction; print('OK')"
# ۲) تست کامل (باید 167 passed بماند)
venv\Scripts\python.exe -m pytest -q -p no:warnings
# ۳) تأیید نبودن migration جدید
venv\Scripts\python.exe -m alembic heads     # باید همان c9d0e1f2a3b4 باشد
```

---

## ۷. جدول ریسک و کاهش

| ریسک | احتمال | تأثیر | راه کاهش |
|:---|:---:|:---:|:---|
| تداخل `Transaction` با SQLAlchemy engine | کم | متوسط | rename به `FinancialTransaction` (همین کار) |
| شکستن relationship strings | متوسط | **زیاد** | گام ۱ و ۲: ۷ رشته در ۲ فایل آپدیت می‌شود |
| شکستن FKها | کم | زیاد | `__tablename__` تغییر نمی‌کند |
| شکستن تست‌ها | کم | متوسط | alias `Account`/`Transaction` |
| فراموشی import | متوسط | کم | alias پوشش می‌دهد + grep تأییدی در پایان |
| آلودگی git (کار فاز ۳۶ commit نشده) | زیاد | کم | خارج از دامنهٔ این فاز؛ فقط یادآوری می‌شود |

---

## ۸. سؤالات باز

1. aliasها تا کدام فاز بمانند؟ (پیشنهاد: تا فاز ۳۸، سپس حذف تدریجی)
2. `ADJUSTMENT` مجاز به مبلغ منفی/مثبت؟ (پیشنهاد: هر دو، با توضیح اجباری)
3. آیا `Category.CONVERSION` باید به seed پیش‌فرض دسته‌بندی‌ها اضافه شود؟ (پیشنهاد: بله، در فاز بعد)
4. آیا `TransactionType.TRANSFER` باید جایگزین الگوی فعلی «EXCHANGE + from/to» شود؟ (پیشنهاد: نگه‌داشتن هر دو برای سازگاری)

---

## ⛔ پایان Plan — اجرا فقط پس از تأیید

