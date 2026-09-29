# PHASE 27 — Trade Contract

> **نوع سند:** Audit + Contract + Migration Plan + Risk Assessment
> **تاریخ:** 2026-09-28
> **وضعیت:** ✅ فقط سند — هیچ کدی نوشته/تغییر نشده است (طبق قانون «فقط Audit + Plan»)
> **پیش‌نیاز:** Phase 26 تأییدشده (`PHASE26_DOMAIN_ARCHITECTURE.md`)
> **خروجی Phase 28 بر پایهٔ این قرارداد:** `PHASE28_PERSONAL_TRADING_ACCOUNT.md`

---

## ۰. تصمیمات تأییدشده (ورودی این فاز)

| # | موضوع | تصمیم |
| :-- | :--- | :--- |
| ۱ | `PropAccount ← Finance Account` | 🔴 **حذف** — `PropAccount` حساب معاملاتی است نه مالی. جایگزین: `PropWithdrawal.destination_account_id` → مالی |
| ۲ | Two-Head Migration | ✅ **گزینه A** — حذف `d4e5f6a7b8c9` + `alembic stamp f1a2b3c4d5e6` |
| ۳ | `StrategyVersion.test_type` | ✅ **Enum(`TestType`)** (هم‌جنس با `Trade.test_type`) |
| ۴ | `AnalysisScope` | ✅ افزودن `PERSONAL_ACCOUNT`، حذف/Deprecate `BROKER` |
| ۵ | `Broker` | ✅ مستقل؛ مهاجرت `Account.broker_name → Broker.name`؛ حذف `Account.broker_name` |

---

## ۱. Audit تکمیلی (Contract-Focused)

### ۱.۱ وضعیت فعلی `TestType`

`backend/app/models/strategy.py:34-37`
```python
class TestType(str, enum.Enum):
    BACKTEST = "backtest"
    FORWARD  = "forward"
    REAL     = "real"        # ← شخصی و پراپ هر دو با همین مقدار
```

- مقادیر در دیتابیس به‌صورت **NAME** ذخیره می‌شوند (`BACKTEST`/`FORWARD`/`REAL`) — نکتهٔ مهم که `test_scope.py` و migration به آن اشاره کرده‌اند.
- REAL مبهم ⇒ شخصی و پراپ قابل تفکیک نیستند مگر با نگاه به `finance_account_id`/`prop_stage_id`.

### ۱.۲ وضعیت فعلی `version_id`

- `Trade.version_id` → `nullable=True` (`strategy.py:112`).
- **باگ import:** `api/imports.py` مسیر `elif prop_stage_id` مقدار `version_id` را به `save_trades` پاس **نمی‌دهد** (خطوط ۶۴–۶۹ و ۱۶۰–۱۶۵) ⇒ معاملات REAL_PROP ممکن است `version_id=NULL` داشته باشند.
- `TradeValidator` **از قبل** `version_id` را برای REAL اجباری می‌داند، اما به‌علت باگ import این قانون در DB نقض می‌شود.

### ۱.۳ وضعیت فعلی `AnalysisScope`

`backend/app/models/strategy.py:40-52`
```python
class AnalysisScope(str, enum.Enum):
    VERSION    = "version"
    PROP_STAGE = "prop_stage"
    BROKER     = "broker"    # ← وابسته به Account.type=BROKER
```

مصرف‌ها: `analytics.py:888` (POST/GET تحلیل بروکر)، `analysis_service.py:52`، `_guard_analyzable`، PDA (خط ۹۲۸). scope_key = `str(finance_account_id)`.

### ۱.۴ نقاط اتصال Domain مختلط (لیست کامل برای Migration)

| فایل | موارد وابسته به `finance_account_id` / `Account.BROKER` / `Account.PROP` |
| :--- | :--- |
| `models/strategy.py` | `Trade.finance_account_id`, `AnalysisResult.finance_account_id`, `AnalysisRun.finance_account_id`, `AnalysisScope.BROKER` |
| `models/finance.py` | `Account.broker_name`, `AccountType.BROKER`, `AccountType.PROP` |
| `models/prop.py` | `PropAccount.finance_account_id` |
| `api/trades.py` | `TradeUpdate.finance_account_id`, `ManualTradeCreate.finance_account_id`, `test_type` map، فیلتر `get_trades` |
| `api/imports.py` | پارامتر ندارد؛ `finance_account_id=None`؛ باگ `version_id` |
| `api/analytics.py` | `analyze/broker/{finance_account_id}`, `analysis/broker/...`, `_guard_analyzable`, PDA, headless KPIs (`AccountType.BROKER`, `AccountType.PROP`) |
| `api/finance.py` | `AccountCreate/Update.broker_name`, `AccountType.BROKER/PROP` در summary/real-pnl/spendable |
| `api/broker.py` | کل فایل روی `Account.type=BROKER` |
| `api/prop.py` | `_ensure_finance_account`, `PropAccountCreate.create_finance_account`, `get/create finance-account`, `withdraw` (`Account.type != PROP`) |
| `services/analysis_service.py` | `analyze_broker(finance_account_id)`, `_analyze(...finance_account_id)` |
| `services/finance_sync_service.py` | `_find_account` (BROKER → Account، پراپ → PropAccount.finance_account_id) |
| `services/import_service.py` | `save_trades(finance_account_id=...)` |
| `utils/trade_validator.py` | `validate_classification(...finance_account_id...)` |
| `frontend/*` | `getFinanceAccounts`, `createFinanceAccount`, `AnalysisPage.tsx:71`, `TradesPage.tsx:994`, `AccountForm.tsx`, `FinancePage.tsx` |
| `tests/*` | `test_analysis_phase23.py`، `test_analysis_scope.py`، `test_soft_delete_filters.py` |

---

## ۲. Contract نهایی (قرارداد معامله)

### ۲.۱ `TestType` جدید (۴ مقدار)

```python
class TestType(str, enum.Enum):
    BACKTEST      = "backtest"
    FORWARD       = "forward"
    REAL_PERSONAL = "real_personal"
    REAL_PROP     = "real_prop"
```

**نگاشت مهاجرت:** `REAL` + `finance_account_id` → `REAL_PERSONAL` | `REAL` + `prop_stage_id` → `REAL_PROP`.

### ۲.۲ جدول ارجاع (Reference Table)

| نوع | `StrategyVersion` (`version_id`) | `PersonalTradingAccount` | `PropStage` (`prop_stage_id`) |
| :--- | :---: | :---: | :---: |
| **BACKTEST** | ✅ اجباری | ❌ ممنوع | ❌ ممنوع |
| **FORWARD** | ✅ اجباری | ❌ ممنوع | ❌ ممنوع |
| **REAL_PERSONAL** | ✅ اجباری | ✅ اجباری | ❌ ممنوع |
| **REAL_PROP** | ✅ اجباری | ❌ ممنوع | ✅ اجباری |

**قانون طلایی:** `REAL_PERSONAL` **XOR** `REAL_PROP`.
`version_id` برای **همهٔ** انواع اجباری است.

### ۲.۳ جدول صدق اعتبارسنجی (Truth Table)

| test_type | version_id | personal_trading_account_id | prop_stage_id | نتیجه |
| :--- | :---: | :---: | :---: | :---: |
| BACKTEST | ✅ | NULL | NULL | ✅ معتبر |
| BACKTEST | ✅ | مقدار | NULL | ❌ خطا |
| BACKTEST | ✅ | NULL | مقدار | ❌ خطا |
| FORWARD | ✅ | NULL | NULL | ✅ معتبر |
| FORWARD | ✅ | مقدار | NULL | ❌ خطا |
| REAL_PERSONAL | ✅ | مقدار | NULL | ✅ معتبر |
| REAL_PERSONAL | ✅ | NULL | NULL | ❌ خطا |
| REAL_PERSONAL | ✅ | مقدار | مقدار | ❌ خطا (XOR) |
| REAL_PROP | ✅ | NULL | مقدار | ✅ معتبر |
| REAL_PROP | ✅ | NULL | NULL | ❌ خطا |
| REAL_PROP | ✅ | مقدار | مقدار | ❌ خطا (XOR) |
| هر نوع | NULL | — | — | ❌ خطا (version_id اجباری) |

### ۲.۴ فیلد نهایی `Trade` (پس از Phase 28)

| ستون | نوع | nullable | توضیح |
| :--- | :--- | :---: | :--- |
| `version_id` | FK `strategy_versions.id` | **❌ False** | اجبار جدید |
| `personal_trading_account_id` | FK `personal_trading_accounts.id` | ✅ True | فقط REAL_PERSONAL |
| `prop_stage_id` | FK `prop_stages.id` | ✅ True | فقط REAL_PROP |
| `test_type` | Enum(`TestType`) | ❌ False | ۴ مقدار |
| `finance_account_id` | — | — | 🔴 **حذف می‌شود** |

### ۲.۵ اعتبارسنجی در دو لایه

**لایهٔ Application** — بازنویسی `TradeValidator.validate_classification(test_type, version_id, personal_trading_account_id, prop_stage_id)` طبق جدول ۲.۳.

**لایهٔ DB** — `CheckConstraint` پیشنهادی روی SQLite:

```sql
CHECK (
  version_id IS NOT NULL AND (
       (test_type IN ('BACKTEST','FORWARD')
          AND personal_trading_account_id IS NULL AND prop_stage_id IS NULL)
    OR (test_type = 'REAL_PERSONAL'
          AND personal_trading_account_id IS NOT NULL AND prop_stage_id IS NULL)
    OR (test_type = 'REAL_PROP'
          AND prop_stage_id IS NOT NULL AND personal_trading_account_id IS NULL)
  )
)
```

> نکته: مقدار enum به‌صورت NAME ذخیره می‌شود؛ در CHECK از همان NAME استفاده شود.

### ۲.۶ `AnalysisScope` جدید

```python
class AnalysisScope(str, enum.Enum):
    VERSION          = "version"
    PROP_STAGE       = "prop_stage"
    PERSONAL_ACCOUNT = "personal_account"   # ← جای BROKER
    # BROKER → حذف/Deprecated
```

نگاشت: رکوردهای `scope='BROKER'` → `'PERSONAL_ACCOUNT'`؛ `scope_key = str(personal_trading_account_id)`.
فیلد FK در `AnalysisResult`/`AnalysisRun`: `finance_account_id` → **`personal_trading_account_id`** (FK → `personal_trading_accounts.id`).

### ۲.۷ مدل‌های TRADING جدید (طبق درخواست Phase 28)

```python
class Broker(Base):
    __tablename__ = "brokers"
    id, name, website?, notes?, is_active, created_at
    accounts = relationship("PersonalTradingAccount", back_populates="broker")

class PersonalTradingAccount(Base):
    __tablename__ = "personal_trading_accounts"
    id, broker_id (FK brokers.id, NOT NULL), account_number, account_label?,
    currency (Enum(Currency)), initial_balance, current_balance, is_active, created_at
    broker = relationship("Broker", back_populates="accounts")
    trades = relationship("Trade", back_populates="personal_trading_account")
```

### ۲.۸ دامنهٔ FINANCE نهایی

- `Account` = **فقط پول**: `BANK | EXCHANGE | CRYPTO_WALLET`.
- `AccountType.BROKER` → **حذف** (به `PersonalTradingAccount` منتقل شد).
- `AccountType.PROP` → **حذف** (پل `PropAccount.finance_account_id` حذف شد).
- `Account.broker_name` → **حذف** (به `Broker.name` منتقل شد).
- `PropWithdrawal.destination_account_id` → FK به `accounts.id` (مالی) **حفظ**.
- `PropAccount.finance_account_id` → 🔴 **حذف**. `_ensure_finance_account()` و endpointهای `finance-account` حذف می‌شوند.

---

## ۳. دفتر تغییرات (Change Ledger برای Phase 28)

### ۳.۱ Backend — Models
| فایل | تغییر |
| :--- | :--- |
| `models/strategy.py` | `TestType` → ۴ مقدار؛ `Trade`: حذف `finance_account_id`، + `personal_trading_account_id`، `version_id` NOT NULL، `test_type` NOT NULL؛ `AnalysisScope` + PERSONAL_ACCOUNT − BROKER؛ `AnalysisResult/Run`: `finance_account_id` → `personal_trading_account_id` |
| `models/finance.py` | `AccountType` → فقط BANK/EXCHANGE/CRYPTO_WALLET؛ حذف `Account.broker_name` |
| `models/prop.py` | حذف `PropAccount.finance_account_id` و relationship `finance_account` |
| `models/trading.py` (جدید) | `Broker`, `PersonalTradingAccount` |
| `migrations/env.py` | import مدل‌های جدید |

### ۳.۲ Backend — Schemas/API
| فایل | تغییر |
| :--- | :--- |
| `api/trades.py` | Schemaها: `finance_account_id` → `personal_trading_account_id`؛ map `test_type` ۴ مقدار؛ فیلترها و پاسخ‌ها |
| `api/imports.py` | + پارامتر `personal_trading_account_id` + **رفع باگ `version_id`** در مسیر پراپ؛ + `REAL_PERSONAL/REAL_PROP` |
| `api/analytics.py` | `analyze/broker/...` → `analyze/personal-account/...`؛ scope PERSONAL_ACCOUNT؛ حذف ارجاع `AccountType.BROKER/PROP` از KPIها |
| `api/finance.py` | حذف `broker_name` از Schema؛ حذف/بازنگری summary برای BROKER/PROP |
| `api/broker.py` | بازنویسی مبنا از `Account.type=BROKER` → `PersonalTradingAccount` (یا حذف/ادغام) |
| `api/prop.py` | حذف `_ensure_finance_account` و endpointهای `finance-account`؛ بازطراحی `withdraw` (مبدأ = PropStage، مقصد = Account مالی) |
| `api/brokers.py` (جدید) | CRUD بروکر |
| `api/personal_accounts.py` (جدید) یا گسترش `personal.py` | CRUD PersonalTradingAccount |

### ۳.۳ Backend — Services/Utils
| فایل | تغییر |
| :--- | :--- |
| `utils/trade_validator.py` | بازنویسی کامل طبق جدول ۲.۳ |
| `utils/trade_scope.py` | `analysis_trades_filter()` → `test_type NOT IN (REAL_PERSONAL, REAL_PROP)` |
| `services/analysis_service.py` | `analyze_broker` → `analyze_personal_account`؛ `_analyze` پارامتر جدید |
| `services/finance_sync_service.py` | `_find_account`: PersonalTradingAccount (REAL_PERSONAL) / PropAccount→Account مالی (REAL_PROP) |
| `services/import_service.py` | `save_trades`: `personal_trading_account_id` |

### ۳.۴ Frontend
| فایل | تغییر |
| :--- | :--- |
| `api/client.ts` | + `getPersonalTradingAccounts`, `createPersonalTradingAccount`, `getBrokers`؛ حذف/بازنگری `getFinanceAccounts({type:'broker'})` |
| `TradesPage.tsx` | dropdown حساب معاملاتی از منبع جدید |
| `ImportPage.tsx` | مقصد REAL_PERSONAL از منبع جدید + ارسال `version_id` |
| `AnalysisPage.tsx` | تب «حساب شخصی» از endpoint جدید |
| `FinancePage.tsx` / `AccountForm.tsx` | حذف فیلد `broker_name` |
| `PayoutHistoryPage.tsx` | منبع بروکر از `PersonalTradingAccount` |
| `PropPage.tsx` | حذف بخش «حساب مالی متناظر» |

### ۳.۵ Tests
به‌روزرسانی: `test_trades.py` (Truth Table ۲.۳)، `test_imports.py` (`REAL_PERSONAL`/`REAL_PROP` + version_id)، `test_analysis_phase23.py` و `test_soft_delete_filters.py` (PersonalTradingAccount)، `test_finance.py` (حذف BROKER/PROP).

---

## ۴. Migration Plan (شامل حل Two-Head)

> ⚠️ این یک **پلان** است؛ اجرا در Phase 28 با تأیید شما. طبق درخواست، DB دادهٔ خاصی ندارد.

### گام صفر — حل Two-Head (تصمیم گزینه A)

**وضعیت فعلی (تأییدشده با ابزار):**
```
alembic heads   → d4e5f6a7b8c9 (head) | f1a2b3c4d5e6 (head)
alembic current → d4e5f6a7b8c9
git status      → ?? backend/migrations/versions/d4e5f6a7b8c9_add_is_deleted_to_trades.py
```

**اقدامات:**
```powershell
# ۱) حذف فایل تکراری/untracked
Remove-Item c:\MokTradeDesk\backend\migrations\versions\d4e5f6a7b8c9_add_is_deleted_to_trades.py

# ۲) هم‌ترازی DB با head باقی‌مانده (DB از قبل ستون is_deleted را دارد)
cd c:\MokTradeDesk\backend
.\venv\Scripts\python.exe -m alembic stamp f1a2b3c4d5e6

# ۳) تأیید: باید فقط یک head بماند
.\venv\Scripts\python.exe -m alembic heads
.\venv\Scripts\python.exe -m alembic current
```

**نتیجهٔ مورد انتظار:** `alembic heads` → تنها `f1a2b3c4d5e6 (head)`؛ `alembic current` → `f1a2b3c4d5e6`.

> جایگزین (چون داده دور ریختنی است): حذف کامل فایل `trading_desk.db` و اجرای `alembic upgrade head` از صفر — حتی تمیزتر، اما گزینه A تصمیم شماست.

### گام ۱ — Migration ساخت TRADING (Phase 28)

`revision: a1b2c3d4e5f6` (revises `f1a2b3c4d5e6`)

1. `create_table("brokers")` — id, name, website, notes, is_active, created_at.
2. `create_table("personal_trading_accounts")` — id, broker_id(FK), account_number, account_label, currency, initial_balance, current_balance, is_active, created_at.
3. **Data migration** — برای هر `accounts.type='BROKER'`:
   - `Broker(name = accounts.broker_name or accounts.name)`
   - `PersonalTradingAccount(broker_id, account_number=NULL, account_label=accounts.name, currency=accounts.currency, initial_balance=accounts.balance, current_balance=accounts.balance)`
   - نگاشت `account_id → personal_trading_account_id`.
4. `trades`: + `personal_trading_account_id` (FK)، پرکردن از نگاشت، سپس `drop_column("finance_account_id")`.

### گام ۲ — Migration Contract (`test_type` + `version_id`)

`revision: b2c3d4e5f6a7` (revises `a1b2c3d4e5f6`)

1. `test_type` UPDATE:
   - `REAL` + `finance_account_id IS NOT NULL` → `REAL_PERSONAL` ‎(**ترتیب مهم:** این UPDATE باید **قبل از** `drop finance_account_id` یا با نگاشت موقت انجام شود.)
   - `REAL` + `prop_stage_id IS NOT NULL` → `REAL_PROP`.
2. `version_id` NOT NULL:
   - رکوردهای با `version_id IS NULL` (حاصل باگ import): **پاک‌سازی** (داده دور ریختنی) یا backfill — تصمیم در Phase 28.
   - سپس `batch_alter_table("trades")`: `alter_column("version_id", nullable=False)`.
3. `test_type`: `alter_column(nullable=False)` + افزودن `CheckConstraint` (بند ۲.۵).

### گام ۳ — Migration حذف پل پراپ و پاک‌سازی FINANCE

`revision: c3d4e5f6a7b8` (revises `b2c3d4e5f6a7`)

1. `prop_accounts`: `drop_column("finance_account_id")` (+ FK مرتبط).
2. `accounts`: `drop_column("broker_name")`.
3. ردیف‌های `accounts` با `type IN ('BROKER','PROP')` پس از نگاشت گام‌۱ بی‌مصرف می‌شوند — حذف یا حفظ برای audit (تصمیم Phase 28).
4. `analysis_results`/`analysis_runs`: UPDATE `scope='BROKER'` → `'PERSONAL_ACCOUNT'`.
5. `analysis_results`/`analysis_runs`: rename `finance_account_id` → `personal_trading_account_id` (+ FK جدید).

### گام ۴ — اعتبارسنجی نهایی
- `alembic heads` → یک head.
- `alembic upgrade head` بدون خطا.
- `.\venv\Scripts\python.exe -m pytest -q` → همه سرسبز.
- بررسی دستی ستون‌های `trades` + CheckConstraint.

### ترتیب اجرای پیشنهادی (خلاصه)
```
گام۰ حل two-head  →  گام۱ TRADING  →  گام۲ Contract  →  گام۳ پاک‌سازی  →  گام۴ تست

---

## ۵. Risk Assessment

| # | ریسک | احتمال | اثر | کاهش (Mitigation) |
| :-- | :--- | :---: | :---: | :--- |
| R1 | تعارض دو head در `alembic upgrade` | بالا (فعلی) | 🔴 | گام صفر — حذف فایل تکراری + stamp |
| R2 | تغییر NAME enum `REAL` → `REAL_PERSONAL/REAL_PROP` و شکستن دادهٔ قدیمی | متوسط | 🟠 | data migration قبل از تغییر + DB دور ریختنی |
| R3 | `version_id NOT NULL` روی رکوردهای NULL (باگ import) شکست می‌خورد | بالا | 🟠 | پاک‌سازی/backfill در گام ۲ |
| R4 | SQLite از `ALTER COLUMN` پشتیبانی نمی‌کند | بالا | 🟡 | استفاده از `batch_alter_table` (الگوی موجود پروژه) |
| R5 | `AnalysisScope` enum در DB رشتهٔ 'BROKER' دارد → تحلیل‌های قدیمی یتیم | متوسط | 🟡 | UPDATE نگاشت در گام ۳ |
| R6 | حذف `AccountType.BROKER/PROP` باعث ۵۰۰ در endpointهای مالی/بروکر | بالا | 🟠 | به‌روزرسانی هم‌زمان `finance.py`/`broker.py`/`analytics.py` |
| R7 | Frontend به `/finance/accounts?type=broker` وابسته است | بالا | 🟡 | endpoint جدید + به‌روزرسانی `client.ts` و صفحات |
| R8 | تست‌های موجود می‌شکنند (`Account(type=BROKER)`، `finance_account_id`) | بالا | 🟡 | به‌روزرسانی تست‌ها همراه کد |
| R9 | `_ensure_finance_account` حذف شود ولی `withdraw`/`costs` هنوز به آن نیاز داشته باشند | متوسط | 🟠 | بازطراحی `withdraw` (مبدأ=PropStage، مقصد=Account مالی) |
| R10 | از دست رفتن نگاشت هنگام حذف `finance_account_id` قبل از UPDATE test_type | متوسط | 🔴 | ترتیب دقیق گام‌ها (بند گام ۲ هشدار) |

**ریسک باقیماندهٔ قابل‌قبول:** با توجه به «DB بدون دادهٔ خاص»، بزرگ‌ترین ریسک‌ها به سادگی با پاک‌سازی داده و اجرای migrations از صفر خنثی می‌شوند.

---

## ۶. Rollback Plan

| سناریو | اقدام |
| :--- | :--- |
| Migration گام ۱/۲/۳ شکست خورد | `alembic downgrade <revision قبلی>` (هر سه migration باید `downgrade()` کامل داشته باشند — الزام Phase 28) |
| خرابی داده | بازیابی از Backup (`backups/` — سرویس Backup خودکار فاز ۱۷) |
| وضعیت بحرانی سازگاری | حذف `trading_desk.db` + `alembic upgrade head` از صفر (DB دور ریختنی) |
| Two-head برنگشت | فایل `d4e5f6a7b8c9` از git قابل بازیابی نیست (untracked) — کپی محلی نگه داشته شود تا قبل از حذف |

**الزام:** هر migration جدید باید `downgrade()` کامل و تست‌شده داشته باشد.

---

## ۷. Test Plan (برای Phase 28)

### ۷.۱ تست‌های قرارداد (unit)
- Truth Table کامل بند ۲.۳ (۱۲ ردیف) در `test_trades.py` → `TradeValidator.validate_classification`.
- CheckConstraint DB: تلاش برای درج معاملهٔ نامعتبر باید `IntegrityError` بدهد.

### ۷.۲ تست‌های Endpoint
- `POST /api/trades/manual` با هر ۴ نوع (معتبر/نامعتبر).
- `POST /api/imports/{soft4x,mt4}`:
  - `REAL_PROP` **با** `version_id` → ذخیره با `version_id` غیرNULL (تأیید رفع باگ).
  - `REAL_PERSONAL` با `personal_trading_account_id` → ذخیره.
- `POST/GET /api/analytics/analyze/personal-account/{id}` → scope=PERSONAL_ACCOUNT.

### ۷.۳ تست‌های Migration
- `alembic heads` = یک head.
- `upgrade head` → `downgrade` → `upgrade` چرخه‌ای بدون خطا.
- صحت نگاشت داده: `accounts(type=BROKER)` → `Broker` + `PersonalTradingAccount`.

### ۷.۴ تست‌های رگرسیون
- کل سوئیت: `.\venv\Scripts\python.exe -m pytest -q`.
- تست‌های Soft Delete، Prop، Finance، Analysis دست‌نخورده سرسبز.

---

## ۸. سؤالات باز نهایی (قبل از Phase 28)

1. رکوردهای `accounts` با `type IN ('BROKER','PROP')` پس از نگاشت: **حذف** شوند یا برای audit **بمانند**؟ (پیشنهاد: حذف)
2. معاملات با `version_id IS NULL`: **حذف** شوند یا به یک نسخهٔ پیش‌فرض **backfill** شوند؟ (پیشنهاد: حذف — باگ import)
3. `Account.prop_firm_name` / `prop_firm_id` هم حذف شوند (چون پل پراپ حذف شد) یا بمانند؟
4. نام endpoint جدید تحلیل: `analyze/personal-account/{id}` تأیید می‌شود؟
5. آیا `Broker` به UI جدید (صفحهٔ مستقل) نیاز دارد یا فعلاً فقط API؟

---

## ۹. جمع‌بندی و آمادگی Phase 28

قرارداد روشن است:

- **`TestType` → ۴ مقدار** و `version_id` اجباری.
- **`REAL_PERSONAL` XOR `REAL_PROP`** (لایهٔ App + لایهٔ DB).
- **`Trade.finance_account_id` حذف** → `personal_trading_account_id`.
- **`Account` فقط مالی** (BANK/EXCHANGE/CRYPTO_WALLET).
- **`Broker` + `PersonalTradingAccount` جدید** در Domain=TRADING.
- **`PropAccount.finance_account_id` حذف**؛ `PropWithdrawal.destination_account_id` مالی می‌ماند.
- **`AnalysisScope.BROKER` → `PERSONAL_ACCOUNT`**.
- **حل Two-Head** به‌عنوان گام صفر.

با تأیید شما و پاسخ به ۵ سؤال بند ۸، وارد **Phase 28 — PersonalTradingAccount (Implementation)** می‌شویم و پیش از هر تغییر، کد را نشان می‌دهم.

---

**پایان Phase 27 (Trade Contract).** — فقط Audit + Plan؛ هیچ کدی تغییر نکرد.
```

