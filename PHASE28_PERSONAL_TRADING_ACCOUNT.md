# PHASE 28 — PersonalTradingAccount (Implementation)

> **نوع سند:** Implementation Report
> **تاریخ:** 2026-09-28
> **وضعیت:** ✅ اجرا شد — Migration + Models + Contract + Tests سبز
> **پیش‌نیاز:** Phase 26 (`PHASE26_DOMAIN_ARCHITECTURE.md`) + Phase 27 (`PHASE27_TRADE_CONTRACT.md`)
> **دامنه:** Backend فقط (UI صفحهٔ مستقل `Broker` طبق تصمیم شما به فاز بعد موکول شد)

---

## ۰. خلاصهٔ نتایج

| گام | عنوان | وضعیت | نتیجه |
| :-- | :--- | :---: | :--- |
| **۰** | حل Two-Head | ✅ | تنها head = `f1a2b3c4d5e6` → سپس `c3d4e5f6a7b8` |
| **۱** | مدل‌های TRADING + Migration | ✅ | `brokers` + `personal_trading_accounts` ساخته شد |
| **۲** | Trade Contract (DB) | ✅ | `version_id NOT NULL` + `ck_trades_classification` |
| **۳** | پاک‌سازی FINANCE + حذف پل پراپ | ✅ | `Account.broker_name`/`prop_firm_*` و `PropAccount.finance_account_id` حذف |
| **۴** | تست‌ها | ✅ | **۹۷ تست سبز** + round-trip migration |

**دیتابیس:**
```
alembic heads   →  c3d4e5f6a7b8 (head)   ← یک head
alembic current →  c3d4e5f6a7b8
upgrade → downgrade → upgrade  →  ROUNDTRIP OK
```

---

## ۱. گام ۰ — حل Two-Head (تصمیم گزینه A)

**پیش از:** دو head موازی روی `e5f6a7b8c9d0`:
- `d4e5f6a7b8c9` (untracked، تکراری)
- `f1a2b3c4d5e6`

**اجرا شد:**
```powershell
# ۱) پشتیبان امن
Copy-Item .\migrations\versions\d4e5f6a7b8c9_add_is_deleted_to_trades.py .\backups\phase28\...bak
Copy-Item .\trading_desk.db .\backups\phase28\trading_desk.db.bak

# ۲) حذف فایل تکراری/untracked
Remove-Item .\migrations\versions\d4e5f6a7b8c9_add_is_deleted_to_trades.py

# ۳) هم‌ترازی DB (DB از قبل ستون is_deleted را داشت)
python -m alembic stamp --purge f1a2b3c4d5e6
```

**نکتهٔ عملیاتی:** `alembic stamp f1a2b3c4d5e6` شکست خورد (`Can't locate revision identified by 'd4e5f6a7b8c9'`) چون DB به revision حذف‌شده اشاره می‌کرد؛ با `--purge` حل شد.

**نتیجه:** `alembic heads` → تنها `f1a2b3c4d5e6`؛ `alembic_version` دیتابیس = `f1a2b3c4d5e6`.

---

## ۲. گام ۱ — مدل‌های TRADING + Migration `a1b2c3d4e5f6`

### ۲.۱ فایل جدید: `backend/app/models/trading.py`

```python
class Broker(Base):
    __tablename__ = "brokers"
    id, name, website?, notes?, is_active, created_at
    accounts = relationship("PersonalTradingAccount", back_populates="broker")

class PersonalTradingAccount(Base):
    __tablename__ = "personal_trading_accounts"
    id, broker_id (FK brokers.id, NOT NULL), account_number (NOT NULL),
    account_label?, currency (Enum(Currency)), initial_balance, current_balance,
    is_active, created_at
    broker = relationship("Broker", back_populates="accounts")
    trades = relationship("Trade", back_populates="personal_trading_account")
```

### ۲.۲ تغییر `models/strategy.py` — Trade

```python
version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=False, index=True)
personal_trading_account_id = Column(Integer, ForeignKey("personal_trading_accounts.id"), nullable=True, index=True)
prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True)
test_type = Column(Enum(TestType), nullable=False, default=TestType.BACKTEST, index=True)
# finance_account_id  ← حذف شد
```
+ `personal_trading_account = relationship("PersonalTradingAccount", back_populates="trades")`

### ۲.۳ Migration `a1b2c3d4e5f6_phase28_trading_domain.py`

ترتیب داخل migration (حیاتی برای جلوگیری از از دست رفتن نگاشت):
1. `UPDATE trades` : `REAL` + `finance_account_id` → `REAL_PERSONAL`
2. `UPDATE trades` : `REAL` + `prop_stage_id` → `REAL_PROP`
3. `DELETE trades` : `REAL` بی‌مقصد + `version_id IS NULL`
4. `create_table("brokers")` + `create_table("personal_trading_accounts")`
5. مهاجرت `accounts(type=BROKER)` → `Broker` + `PersonalTradingAccount` (نگاشت id)
6. افزودن `trades.personal_trading_account_id` + backfill + حذف `finance_account_id`
7. `DELETE accounts WHERE type='BROKER'`

**خروجی روی دادهٔ واقعی:** `BACKTEST=153`، `REAL_PROP=22` (نگاشت صحیح)، ۰ معامله با `finance_account_id`، ۰ رکورد `version_id NULL` برای حذف.

---

## ۳. گام ۲ — Trade Contract در سطح DB (`b2c3d4e5f6a7`)

```python
# TestType جدید (models/strategy.py)
class TestType(str, enum.Enum):
    BACKTEST = "backtest"
    FORWARD = "forward"
    REAL_PERSONAL = "real_personal"
    REAL_PROP = "real_prop"
```

**Migration `b2c3d4e5f6a7`:**
- `trades.version_id` → `NOT NULL`
- `trades.test_type` → `NOT NULL`
- افزودن `CheckConstraint ck_trades_classification`:
```sql
(test_type IN ('BACKTEST','FORWARD') AND personal_trading_account_id IS NULL AND prop_stage_id IS NULL)
OR (test_type = 'REAL_PERSONAL' AND personal_trading_account_id IS NOT NULL AND prop_stage_id IS NULL)
OR (test_type = 'REAL_PROP' AND prop_stage_id IS NOT NULL AND personal_trading_account_id IS NULL)
```
- ایندکس‌های `ix_trades_version_id` و `ix_trades_test_type`

**SQL تأییدشدهٔ جدول (از DB واقعی):** `version_id INTEGER NOT NULL`، `test_type VARCHAR(8) NOT NULL`، و `CONSTRAINT ck_trades_classification CHECK (...)`.

### ۳.۱ بازنویسی `utils/trade_validator.py`

امضا: `validate_classification(test_type, version_id, personal_trading_account_id, prop_stage_id)`
قوانین طبق جدول ارجاع Phase 27:
- `version_id` برای **همه** اجباری
- `BACKTEST`/`FORWARD`: هیچ‌کدام از دو
- `REAL_PERSONAL`: فقط حساب شخصی
- `REAL_PROP`: فقط مرحله پراپ (XOR)

---

## ۴. گام ۳ — پاک‌سازی FINANCE + حذف پل پراپ (`c3d4e5f6a7b8`)

**تغییرات مدل:**
| فایل | تغییر |
| :--- | :--- |
| `models/finance.py` | `AccountType` → فقط `BANK/EXCHANGE/CRYPTO_WALLET`؛ حذف `Account.broker_name`/`prop_firm_name`/`prop_firm_id` + relationship `prop_firm` |
| `models/prop.py` | حذف `PropAccount.finance_account_id` + relationship `finance_account` |
| `models/strategy.py` | `AnalysisScope` → `VERSION/PROP_STAGE/PERSONAL_ACCOUNT`؛ `AnalysisResult`/`AnalysisRun`: `finance_account_id` → `personal_trading_account_id` |

**Migration `c3d4e5f6a7b8`:**
1. `prop_accounts` → حذف `finance_account_id`
2. `accounts` → حذف `broker_name`/`prop_firm_name`/`prop_firm_id`
3. `DELETE accounts WHERE type NOT IN ('BANK','EXCHANGE','CRYPTO_WALLET')`
4. `analysis_results`/`analysis_runs` → `finance_account_id` → `personal_trading_account_id` + `scope 'BROKER'` → `'PERSONAL_ACCOUNT'`

**نتیجهٔ DB:** `accounts` خالی شد (تنها رکورد PROP حذف شد؛ ۰ ارجاع در transactions/withdrawals)، `prop_accounts` بدون `finance_account_id`، `analysis_results` دارای `personal_trading_account_id`.

---

## ۵. گام ۴ — تست‌ها

### ۵.۱ فایل تست جدید: `tests/test_trading_domain.py`
- جدول صدق `TradeValidator` (۱۲ حالت)
- CheckConstraint: `REAL_PERSONAL` بدون حساب → `IntegrityError`؛ `BACKTEST` با prop → `IntegrityError`؛ حالت معتبر → OK
- API: `POST/GET /api/trading/brokers` و `/api/trading/accounts`

### ۵.۲ به‌روزرسانی تست‌های موجود
| فایل | تغییر اصلی |
| :--- | :--- |
| `test_trades.py` | helper با `version_id`؛ تست‌های قرارداد به `REAL_PERSONAL`/`REAL_PROP` |
| `test_imports.py` | `test_type="real"` → `"real_prop"` |
| `test_analysis_phase23.py` | `Account(BROKER)` → `PersonalTradingAccount`؛ endpoint `personal-account` |
| `test_analysis_scope.py` | `TestType.REAL` → `REAL_PERSONAL` + PTA خودکار |
| `test_soft_delete_filters.py` | helper با `db` + `test_type` استنتاجی؛ sync به no-op |
| `test_finance.py` | `type=broker/prop` → `bank`؛ trade با PTA؛ version_id |
| `test_prop.py` | `REAL` → `REAL_PROP` + `version_id` |

### ۵.۳ نتیجهٔ اجرا
```
pytest -q  →  ۹۷ passed
alembic heads  →  یک head
upgrade → downgrade → upgrade  →  ROUNDTRIP OK
```

---

## ۶. فایل‌های تغییریافته

**جدید (۷):**
- `backend/app/models/trading.py`
- `backend/app/api/trading.py`
- `backend/migrations/versions/a1b2c3d4e5f6_phase28_trading_domain.py`
- `backend/migrations/versions/b2c3d4e5f6a7_phase28_trade_contract.py`
- `backend/migrations/versions/c3d4e5f6a7b8_phase28_finance_cleanup.py`
- `backend/tests/test_trading_domain.py`
- `PHASE28_PERSONAL_TRADING_ACCOUNT.md`

**حذف:** `backend/migrations/versions/d4e5f6a7b8c9_add_is_deleted_to_trades.py`

**ویرایش‌شده (۲۲):** `models/{strategy,finance,prop}.py`، `api/{analytics,broker,finance,imports,prop,trades,main}.py`، `services/{analysis_service,finance_sync_service,import_service}.py`، `utils/{trade_scope,trade_validator}.py`، `migrations/env.py`، و ۷ فایل تست.

---

## ۷. تصمیم لازم / موارد باقی‌مانده (نیازمند تأیید)

| # | مورد | وضعیت فعلی | پیشنهاد |
| :-- | :--- | :--- | :--- |
| **A** | `FinanceSyncService` (پل خودکار Trade→حسابداری) | **غیرفعال (no-op)** — چون `Trade` دیگر به حساب مالی وصل نیست | طراحی مجدد در فاز جدا: P&L معاملات کجا و چگونه در FINANCE ثبت شود؟ |
| **B** | تحلیل KPI «پول قابل خرج» (`analytics.spendable`) | بازنویسی شد بر پایهٔ `PersonalTradingAccount` + `REAL_PROP` | تأیید تفسیر جدید |
| **C** | برداشت پراپ | مبدأ = `PropStage` (نه حساب مالی)؛ مقصد = حساب مالی | تأیید |
| **D** | `Account.prop_firm_name/id` | حذف شد (تصمیم شما) | — |
| **E** | Frontend | **دست‌نخورده** — `TradesPage`/`ImportPage`/`AnalysisPage`/`FinancePage`/`PropPage`/`client.ts` هنوز به فیلدها/endpointهای قدیمی اشاره می‌کنند | فاز بعد (خارج از دامنهٔ Phase 28 طبق وظایف تعیین‌شده) |
| **F** | صفحهٔ مستقل `Broker` (UI) | فقط API | فاز بعد (تصمیم شما) |

> ⚠️ **نکتهٔ مهم برای Frontend:** endpointهای تحلیل بروکر به `analyze/personal-account/{id}` و `analysis/personal-account/{id}` تغییر کردند و `finance_account_id` حذف شد؛ همچنین `/api/prop/accounts/{id}/finance-account` و `create_finance_account` دیگر وجود ندارند. تا اصلاح Frontend، بخش‌های مربوطه در UI کار نخواهند کرد.

---

**پایان Phase 28.** — Migration + Models + Contract + Tests، همه تأییدشده.
