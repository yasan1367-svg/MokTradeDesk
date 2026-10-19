# PHASE 26 — Domain Architecture Audit

> **نوع سند:** Audit (بدون هیچ تغییر کد)
> **تاریخ:** 2026-09-28
> **وضعیت:** ✅ فقط خواندن — هیچ فایل کدی تغییر نکرده است
> **دامنه:** `backend/` (Models · Schemas · API · Services · Utils · Migrations · Tests) + `frontend/src/`

---

## ۰. خلاصهٔ مدیریتی (Executive Summary)

مشکل اصلی تأییدشده و دقیقاً همان چیزی است که در شرح فاز گفته شده:

> **`Trade` هم به «حساب معاملاتی شخصی» و هم به «حساب مالی/بروکر» با یک ستون واحد (`finance_account_id` → `accounts.id`) وصل می‌شود، و مدل `Account` همزمان نقش Trading و Financial را بازی می‌کند.**

یافته‌های کلیدی:

| # | یافته | شدت |
| :-- | :--- | :--- |
| ۱ | `Trade.finance_account_id` → `accounts.id`، بدون تفکیک Trading/Finance | 🔴 بحرانی |
| ۲ | مدل `Account` با `AccountType = {BANK, EXCHANGE, CRYPTO_WALLET, BROKER, PROP}` هم پول و هم حساب معاملاتی را پوشش می‌دهد | 🔴 بحرانی |
| ۳ | `PropAccount.finance_account_id` → `accounts.id` (اتصال پراپ به «حساب مالی» نه «حساب معاملاتی پراپ») | 🟡 نیازمند بازبینی |
| ۴ | **دو Alembic head** همزمان وجود دارد (`d4e5f6a7b8c9` و `f1a2b3c4d5e6`) که هر دو `is_deleted` را به `trades` اضافه می‌کنند | 🔴 بحرانی (بلوکر Migration) |
| ۵ | `Trade.version_id` و `Trade.test_type` هر دو `nullable` هستند (نقض قرارداد «version_id اجباری») | 🟠 مهم |
| ۶ | باگ Import: مسیر پراپ `version_id` را به `save_trades` پاس نمی‌دهد (مستندشده در `ANALYSIS.md`) | 🟠 مهم |
| ۷ | `TestType` فقط سه مقدار دارد (`BACKTEST/FORWARD/REAL`) — `REAL_PERSONAL`/`REAL_PROP` وجود ندارد | 🟠 مهم |
| ۸ | `AnalysisResult`/`AnalysisRun` هم `finance_account_id` (→ accounts) دارند و scope=BROKER روی همان Account سوار است | 🟡 نیازمند بازبینی |

---

## ۱. نقشهٔ دامنهٔ فعلی (As-Is)

```
┌───────────────────────── STRATEGY (موجود) ──────────────────────────┐
│  Strategy ──< StrategyVersion ──< Trade                             │
│                     │ test_type: String|null (BACKTEST/FORWARD/REAL)│
│                     └──< AnalysisResult / AnalysisRun (scope=VERSION)│
└─────────────────────────────────────────────────────────────────────┘
                    ▲
                    │ version_id (nullable=True) ⚠️
┌───────────────────┴─────────────────────────────────────────────────┐
│                          Trade (مرکز ثقل)                            │
│  id, version_id?, prop_stage_id?, finance_account_id?  ← ⚠️ اختلاط   │
│  test_type: Enum(BACKTEST/FORWARD/REAL), source, pnl, is_deleted... │
└──────┬───────────────────────────────────┬──────────────────────────┘
       │ prop_stage_id (nullable)          │ finance_account_id (nullable)
       ▼                                   ▼
┌──────────────────── PROP ────────────┐  ┌──────── FINANCE ──────────┐
│ PropFirm                            │  │ Account                   │
│  └──< PropAccount                   │  │  type: BANK|EXCHANGE|     │
│        │ finance_account_id ⚠️ ─────┼──┼──CRYPTO_WALLET|BROKER|PROP│
│        ├──< PropStage ──< Trade     │  │  balance, currency, ...   │
│        │      (scope=PROP_STAGE)    │  │  └──< Transaction         │
│        ├──< PropCost                │  │        (account_id,       │
│        └──< PropWithdrawal          │  │         related_trade_id) │
│              (destination_account)  │  └───────────────────────────┘
└─────────────────────────────────────┘
```

**نتیجه:** `Account` (FINANCE) عملاً دو Domain را همزمان سرو می‌کند:
- **Trading Account** → `type = BROKER` (حساب معاملاتی شخصی روی بروکر)
- **Financial Account** → `type ∈ {BANK, EXCHANGE, CRYPTO_WALLET}` (فقط پول)
- **حالت مرزی** → `type = PROP` (حساب مالی متناظر با پراپ)

---

## ۲. Audit مدل `Trade`

**فایل:** `backend/app/models/strategy.py:107-152`

| ستون | نوع | nullable | نکته |
| :--- | :--- | :--- | :--- |
| `id` | Integer PK | ❌ | — |
| `version_id` | FK `strategy_versions.id` | ✅ **True** | ⚠️ برخلاف قرارداد Phase 27 (باید False شود) |
| `prop_stage_id` | FK `prop_stages.id` | ✅ True | مسیر PROP |
| `finance_account_id` | FK `accounts.id` | ✅ True | 🔴 **ستون مورد بحث — باید حذف/جدا شود** |
| `source` | Enum(`TradeSource`) | ❌ | MT4_IMPORT / SOFT4X_IMPORT / MANUAL |
| `test_type` | Enum(`TestType`) | ✅ (default BACKTEST) | ⚠️ فقط ۳ مقدار؛ نیاز به ۴ مقدار |
| `is_deleted` | Boolean | ❌ (default False) | Soft Delete مرحله ۲۵ |
| `trade_hash` | String(32) | ✅ | Duplicate Detection |

**Relationships:** `version`, `prop_stage`, `finance_account`, `reviews`.

### نتیجه‌گیری Trade
- ستون `finance_account_id` دقیقاً نقطهٔ اختلاط Domain است.
- `version_id` nullable است و باید اجباری شود (Phase 27).
- `test_type` باید از ۳ به ۴ مقدار گسترش یابد (Phase 27).

---

## ۳. Audit مدل `Account`

**فایل:** `backend/app/models/finance.py:47-81`

```python
class AccountType(str, enum.Enum):
    BANK = "bank"
    EXCHANGE = "exchange"
    CRYPTO_WALLET = "crypto_wallet"
    BROKER = "broker"   # ← Trading Account قاطی‌شده
    PROP = "prop"       # ← حالت مرزی

class Account(Base):
    __tablename__ = "accounts"
    id, name, type, currency, balance,
    card_number, broker_name, prop_firm_name, prop_firm_id
```

### مصرف‌کنندگان `Account.type == BROKER` (یعنی «حساب معاملاتی شخصی»):

| فایل | خط | کاربرد |
| :--- | :--- | :--- |
| `api/analytics.py` | 286, 308, 317, 433, 501, 700 | سود/موجودی/تحلیل بروکر |
| `api/broker.py` | 33 | برداشت‌های بروکر (Payout) |
| `api/finance.py` | 480, 1168, 1204 | آمار، خلاصه، دارایی قابل‌برداشت |
| `services/finance_sync_service.py` | 105 | یافتن حساب برای همگام‌سازی معامله |
| `tests/test_analysis_phase23.py` | 200–224 | ساخت حساب بروکر در تست |
| `tests/test_soft_delete_filters.py` | 114 | تحلیل بروکر |

**نتیجه‌گیری Account:** `Account` باید **فقط Financial** بماند و `type=BROKER/PROP` از آن حذف (یا بی‌استفاده) شود؛ حساب‌های معاملاتی به مدل جدید `PersonalTradingAccount` منتقل شوند.

---

## ۴. Audit مدل `PropAccount` و سلسله‌مراتب PROP

**فایل:** `backend/app/models/prop.py`

| مدل | جدول | فیلدهای کلیدی |
| :--- | :--- | :--- |
| `PropFirm` | `prop_firms` | name, default_profit_share, website, notes |
| `PropFirmDefaultRules` | `prop_firm_default_rules` | stage_type, profit_target, dds |
| `PropAccount` | `prop_accounts` | prop_firm_id, account_label, account_number, currency, **`finance_account_id`** → `accounts.id` |
| `PropStage` | `prop_stages` | prop_account_id, stage_type(STAGE_1/2/FUNDED_REAL), status, dds, profit_target, profit_share_percentage |
| `PropWithdrawal` | `prop_withdrawals` | prop_stage_id, amount, **`destination_account_id`** → `accounts.id` |
| `PropCost` | `prop_costs` | prop_account_id, cost_type, amount |
| `PropAlert` | `prop_alerts` | prop_stage_id, message |

**نکتهٔ Phase 26:** `PropAccount.finance_account_id` (خط ۶۶) طبق جدول تصمیمات 🟡 **«بازبینی»** است. تحلیل:
- این ستون برای «پل مالی» فاز ۵ اضافه شده تا سود پراپ در حسابداری ثبت شود.
- در معماری هدف، `PropStage` مستقیماً به `Trade` وصل است و «حساب مالی» فقط باید پول (Transaction) را نگه دارد.
- پیشنهاد Phase 27/28: `PropAccount.finance_account_id` یا حفظ شود ولی فارغ از Trading، یا تصمیم نهایی به Phase بعد موکول شود. تصمیم نهایی در Phase 27 گرفته می‌شود.

---

## ۵. Audit مدل `StrategyVersion`

**فایل:** `backend/app/models/strategy.py:73-104`

| ستون | نوع | nullable | نکته |
| :--- | :--- | :--- | :--- |
| `id` | Integer PK | ❌ | — |
| `strategy_id` | FK `strategies.id` | ❌ | — |
| `version_name` | String | ❌ | — |
| `rules_note` | Text | ✅ | — |
| `status` | Enum(`StrategyStatus`) | ✅ | RESEARCH…ARCHIVED |
| `test_type` | **String** | ✅ | ⚠️ فاز ۲۴ — برای فیلتر UI؛ جنس آن String است نه Enum |
| `forked_from_version_id` | FK خودارجاع | ✅ | زیرساخت Fork |

**Relationships:** `strategy`, `forked_from`, `trades`, `analysis_results`, `analysis_runs`.

**نکته:** `StrategyVersion.test_type` (String) با `Trade.test_type` (Enum) **هم‌جنس نیستند** — یک ناهمگونی شناختی که در Phase 27 باید تثبیت شود.

---

## ۶. Audit Schemaها (Pydantic)

| فایل | Schema | فیلدهای Classification |
| :--- | :--- | :--- |
| `api/trades.py:28` | `TradeUpdate` | `test_type?`, `version_id?`, `finance_account_id?`, `prop_stage_id?` |
| `api/trades.py:57` | `ManualTradeCreate` | `test_type="backtest"`, `version_id?`, `finance_account_id?`, `prop_stage_id?` |
| `api/finance.py:45` | `AccountCreate` | `name, type(AccountType), currency, balance, card_number, broker_name, prop_firm_name, prop_firm_id` |
| `api/finance.py:56` | `AccountUpdate` | همان + همه Optional |
| `api/prop.py:89` | `PropAccountCreate` | `prop_firm_id, account_label, ...` |
| `api/strategy.py` (`schemas/strategy.py`) | `VersionCreate` / `VersionResponse` | بدون `test_type` در Response ⚠️ |
| `api/strategies.py:53` | نسخه‌ی inline در endpoint | `test_type?`, `status?` |

**ناسازگاری‌ها:**
- `schemas/strategy.py:VersionResponse` فیلد `test_type` ندارد، در حالی که مدل دارد و endpointهای دیگری (inline) آن را می‌پذیرند.
- همهٔ Schemaهای Trade فیلد `finance_account_id` دارند که باید با `personal_trading_account_id` جایگزین شود.

---

## ۷. Audit Endpointها

### ۷.۱ Trade + Import (`api/trades.py`, `api/imports.py`)
- `POST /api/trades/manual` → `ManualTradeCreate`؛ map دستی `{"backtest","forward","real"}` (خطوط ۶۰۱–۶۰۵) و سپس `TradeValidator.validate_classification(...)`.
- `PATCH /api/trades/{id}` → `TradeUpdate`؛ همان validation.
- `GET /api/trades/?version_id=&test_type=&prop_stage_id=&finance_account_id=` (فیلترها در `get_trades`).
- `POST /api/imports/soft4x` و `POST /api/imports/mt4` → پارامترها: `version_id?`, `prop_stage_id?`, `test_type="backtest"`؛ **`finance_account_id` نمی‌گیرند** (در کد به‌صراحت `None` پاس می‌شود).

### ۷.۲ Analytics (`api/analytics.py`)
- `POST /api/analytics/analyze/version/{version_id}?test_type=` → scope=VERSION.
- `POST /api/analytics/analyze/prop/{prop_stage_id}` → scope=PROP_STAGE.
- `POST /api/analytics/analyze/broker/{finance_account_id}` → scope=BROKER. 🔴 **نام و پارامتر وابسته به `finance_account_id`.**
- `GET /api/analytics/analysis/{version_id|prop_stage_id|finance_account_id}` + `_guard_analyzable(...)`.
- `_guard_analyzable` (خط ۸۹۷) و PDA (خط ۹۲۸) فیلد `finance_account_id` را برمی‌گردانند.

### ۷.۳ Finance (`api/finance.py`)
- `GET /api/finance/accounts?type=&currency=` → **همه** حساب‌ها شامل BROKER و PROP.
- `POST/PATCH/DELETE /api/finance/accounts` → `AccountCreate` با `type` از `AccountType` (شامل BROKER/PROP).
- `GET /api/finance/accounts/{id}/stats`, `/withdrawals`, `/summary`, `/spendable-assets`, `/net-profit` — همه روی `Account`.

### ۷.۴ Broker (`api/broker.py`)
- `GET /api/broker/payouts`, `/payouts/stats` — تکیه بر `Account.type == AccountType.BROKER`.
- کامنت صریح: «بروکر مدل جداگانه ندارد».

### ۷.۵ Prop (`api/prop.py`)
- CRUD کامل PropFirm/PropAccount/PropStage/PropWithdrawal/PropCost/PropAlert.
- `GET/POST /api/prop/accounts/{id}/finance-account` → مدیریت «حساب مالی متناظر» پراپ.

### ۷.۶ Personal (`api/personal.py`)
- فقط Journal (review/screenshots) و `GET /api/personal/prop-accounts-list`. مدل PersonalAccount قبلاً (Phase 9) حذف شده است.

---

## ۸. Audit Import (`services/import_service.py`, `api/imports.py`)

- `Soft4XImporter` / `MT4Importer` → `save_trades(trades, version_id?, prop_stage_id?, finance_account_id?)` (خط ۳۳۸).
- `Trade(...)` با `finance_account_id=finance_account_id` ساخته می‌شود (خط ۳۶۰).
- **باگ شناخته‌شده (ANALYSIS.md:60):** در `api/imports.py` مسیر `elif prop_stage_id` و `elif personal_account_id` **`version_id` را پاس نمی‌دهند** → معاملات REAL بدون `version_id` ذخیره می‌شوند. در کد فعلی (خطوط ۵۴–۷۰ و ۱۵۰–۱۶۶) فقط `elif prop_stage_id` باقی مانده و همچنان `version_id` را پاس نمی‌دهد.
- `phase 21`: پس از Import/ثبت معامله، `FinanceSyncService.sync_closed_trades()` در صورت وجود `finance_account_id` یا `prop_stage_id` اجرا می‌شود.

---

## ۹. Audit Validation (`utils/trade_validator.py`)

```python
validate_classification(test_type, version_id, finance_account_id, prop_stage_id)
```

| test_type | قانون فعلی |
| :--- | :--- |
| `BACKTEST` | نیاز به `version_id`؛ **نباید** `finance_account_id`/`prop_stage_id` |
| `FORWARD` | نیاز به `version_id`؛ **نباید** `finance_account_id`/`prop_stage_id` |
| `REAL` | نیاز به `version_id`؛ **XOR**: دقیقاً یکی از `finance_account_id` یا `prop_stage_id` |

**نقاط ضعف نسبت به قرارداد Phase 27:**
1. هیچ تمایزی بین REAL شخصی و REAL پراپ در سطح `TestType` نیست (هر دو `REAL`).
2. «حساب معاملاتی شخصی» با `finance_account_id` بیان می‌شود که همان `Account` مالی است.
3. `version_id` اجباری است ولی نه به‌صورت DB-level (ستون nullable است).

`utils/trade_scope.py` → `analysis_trades_filter()` معاملات REAL را از تحلیل Backtest/Forward کنار می‌گذارد (با نام enum `REAL`).

---

## ۱۰. Audit Services

| سرویس | مسئولیت | وابستگی به Domain مختلط |
| :--- | :--- | :--- |
| `analysis_service.py` | `analyze_version` / `analyze_prop_stage` / `analyze_broker(finance_account_id)` | 🔴 `Trade.finance_account_id` + `AnalysisResult.finance_account_id` |
| `finance_sync_service.py` | همگام‌سازی معامله بسته → `Transaction` | 🔴 `trade.finance_account_id → Account(type=BROKER)` و پراپ `PropAccount.finance_account_id` |
| `import_service.py` | پارس و ذخیرهٔ معاملات | 🔴 `finance_account_id` |
| `prop_rule_engine.py` | ارزیابی قوانین پراپ | بدون اختلاط |
| `backup_service.py` | پشتیبان‌گیری | بدون اختلاط |

`finance_sync_service._find_account` (خطوط ۹۶–۱۲۰) منطق «اول بروکر، بعد پراپ مرحله ۳» را دارد و مستقیماً بین دو Domain پل می‌زند.

---

## ۱۱. Audit Frontend

| فایل | استفاده |
| :--- | :--- |
| `src/api/client.ts:445` | `getFinanceAccounts(params)` → `/api/finance/accounts` |
| `src/api/client.ts:448` | `createFinanceAccount(data)` — `data.type` شامل `broker` |
| `src/api/client.ts:216` | `getFinanceAccountsForDestination()` — مقصد برداشت (type !== prop) |
| `src/pages/AnalysisPage.tsx:71` | `getFinanceAccounts({ type: 'broker' })` → انتخاب حساب بروکر برای تحلیل |
| `src/pages/DashboardPage.tsx:247` | `getFinanceAccounts()` برای ویجت‌های مالی |
| `src/pages/FinancePage.tsx` | CRUD حساب‌های مالی (`createFinanceAccount` با `type`) |
| `src/pages/TradesPage.tsx` / `ImportPage.tsx` | انتخاب حساب مالی برای Classification معامله (فیلد `finance_account_id`) |
| `src/pages/PayoutHistoryPage.tsx` | برداشت‌های بروکر |
| `src/pages/PropPage.tsx` | «حساب مالی متناظر» پراپ |

**نتیجه:** Frontend از یک منبع واحد (`/api/finance/accounts`) هم برای «حساب معاملاتی شخصی» (`type=broker`) و هم «حساب مالی» استفاده می‌کند. Phase 28 باید Endpoint و UI جدا برای `PersonalTradingAccount` اضافه کند.

---

## ۱۲. Audit Tests

| فایل تست | پوشش مرتبط |
| :--- | :--- |
| `test_trades.py` | `TradeValidator.validate_classification` با ۳ نوع؛ Soft/Hard Delete |
| `test_imports.py` | Import با `test_type` و `prop_stage_id` (REAL_PROP) |
| `test_analysis_phase23.py` | تحلیل نسخه/پراپ/**بروکر** با `finance_account_id` (خطوط ۲۰۰–۲۲۴) |
| `test_analysis_scope.py` | REAL در تحلیل Backtest/Forward شمرده نشود |
| `test_soft_delete_filters.py` | تحلیل بروکر `Account(type=AccountType.BROKER)` (خط ۱۱۴) |
| `test_finance.py` | حساب‌های مالی |
| `test_prop.py` | قوانین پراپ |

**شکست‌های مورد انتظار پس از Phase 27/28:** همه‌ی تست‌هایی که `Trade(finance_account_id=...)` یا `Account(type=AccountType.BROKER)` می‌سازند باید به‌روزرسانی شوند.

---

## ۱۳. Audit Migrations — ⚠️ یافتهٔ بحرانی

زنجیرهٔ فعلی (خروجی واقعی `alembic history`):

```
<base> → c4838cd01bbd (initial schema)
       → 1771fcd3af2f (analysis_runs)
       → 51ea09b4aa3d (finance tables)
       → b7d4e19c2f83 (prop_accounts.finance_account_id)
       → 9f1a2b3c4d5e (merge personal → finance)
       → a3f7c21b9d84 (phase20 scope)
       → e5f6a7b8c9d0 (strategy_versions.test_type, branchpoint)
       ├── d4e5f6a7b8c9 (head)   ← «Phase 26 soft delete» (⚠️ untracked در git)
       └── f1a2b3c4d5e6 (head)   ← «Phase 25 soft delete»
```

### 🔴 مشکل: دو Head موازی

- **هر دو** migration `d4e5f6a7b8c9` و `f1a2b3c4d5e6`:
  - روی `e5f6a7b8c9d0` بنا شده‌اند،
  - ستون `is_deleted` را به `trades` اضافه می‌کنند.
- `alembic heads` **دو head** برمی‌گرداند.
- `alembic current` → `d4e5f6a7b8c9 (head)` (DB فعلی روی همین است).
- `main.py:112` از `alembic_command.upgrade(cfg, "head")` استفاده می‌کند که با multiple heads خطای `CommandError: Multiple head revisions are present for given argument 'head'` می‌دهد (و در `try/except` فقط لاگ می‌شود → migration خودکار عملاً شکست می‌خورد).
- `d4e5f6a7b8c9` در `git status` به‌صورت `?? (untracked)` است؛ یعنی یک فایل اضافی/اشتباه است.

**تصمیم پیشنهادی (نیازمند تأیید شما):** در ابتدای Phase 28 یکی از دو فایل تکراری حذف یا به merge-revision تبدیل شود. گزینه‌ها در انتهای سند.

---

## ۱۴. ماتریس اختلاط دامنه (Domain Mixing Matrix)

| موجودیت | STRATEGY | TRADING | PROP | FINANCE | ANALYSIS |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Strategy` / `StrategyVersion` | ✅ | | | | ✅ (scope=VERSION) |
| `Trade` | ✅ (`version_id`) | ⚠️ (`finance_account_id`→`Account`) | ✅ (`prop_stage_id`) | ❌ | ✅ (ورودی تحلیل) |
| `Account` | | 🔴 (`type=BROKER`) | 🟡 (`type=PROP`) | ✅ | 🟡 (scope=BROKER) |
| `Transaction` | | | 🟡 (`related_prop_account_id`) | ✅ | |
| `PropFirm/PropAccount/PropStage` | | | ✅ | 🟡 (`finance_account_id`) | ✅ (scope=PROP_STAGE) |
| `AnalysisResult/AnalysisRun` | ✅ | 🟡 (`finance_account_id`) | ✅ | | ✅ |
| `JournalReview/Screenshot` | | ✅ (روی Trade) | ✅ | | |

🔴 = اختلاط بحرانی · 🟡 = نیازمند بازبینی · ⚠️ = نقض قرارداد

---

## ۱۵. معماری هدف (To-Be) — طبق درخواست

```
STRATEGY :  Strategy ──< StrategyVersion ──< Trade
TRADING  :  Broker ──< PersonalTradingAccount ──< Trade
PROP     :  PropFirm ──< PropAccount ──< PropStage ──< Trade
FINANCE  :  (Financial)Account ──< Transaction
ANALYSIS :  StrategyVersion + Context ──< AnalysisResult / AnalysisRun
```

قوانین:
1. `FinancialAccount` **فقط پول** — هرگز حساب معاملاتی نیست.
2. `PersonalTradingAccount` **جدید** و جدا.
3. `Trade.finance_account_id` **حذف** می‌شود.
4. `Trade.version_id` **اجباری** (nullable=False).
5. `TestType` چهار مقدار: `BACKTEST / FORWARD / REAL_PERSONAL / REAL_PROP`.
6. `REAL_PERSONAL` XOR `REAL_PROP`.

جدول Contract نهایی (Phase 27):

| نوع | `StrategyVersion` | `PersonalTradingAccount` | `PropStage` |
| :--- | :---: | :---: | :---: |
| **BACKTEST** | ✅ | ❌ | ❌ |
| **FORWARD** | ✅ | ❌ | ❌ |
| **REAL_PERSONAL** | ✅ | ✅ | ❌ |
| **REAL_PROP** | ✅ | ❌ | ✅ |

---

## ۱۶. جدول تصمیمات (تأییدشده در درخواست)

| مورد | تصمیم | وضعیت اجرا |
| :--- | :--- | :--- |
| Strategy/Version | ✅ حفظ | بدون تغییر |
| Prop hierarchy | ✅ حفظ | بدون تغییر |
| AnalysisRun/Result | ✅ حفظ | بدون تغییر |
| Soft Delete | ✅ حفظ | بدون تغییر |
| Financial Account | 🔴 جدا | Phase 27/28 |
| Personal Trading Account | 🔴 جدید | Phase 28 |
| Trade → Finance Account | ❌ حذف | Phase 28 |
| PropAccount → Finance Account | 🟡 بازبینی | Phase 27 (تصمیم) |
| Migration | ❌ فعلاً | بعد از تأیید Phase 27/28 |

---

## ۱۷. آثار و ریسک (Impact & Risk)

### ۱۷.۱ فایل‌هایی که Phase 27/28 لمس می‌کند

**Backend — Models**
- `models/strategy.py` → `TestType`, `Trade.finance_account_id`, `Trade.version_id`, `Trade.test_type`
- `models/finance.py` → `Account`/`AccountType`
- `models/prop.py` → `PropAccount.finance_account_id`
- `models/personal.py` یا فایل جدید → `Broker`, `PersonalTradingAccount`

**Backend — Services/Utils**
- `utils/trade_validator.py` → بازنویسی کامل classification
- `utils/trade_scope.py` → `analysis_trades_filter` (نام enum REAL)
- `services/analysis_service.py` → `analyze_broker` → `analyze_personal_account`
- `services/finance_sync_service.py` → `_find_account`
- `services/import_service.py` → `save_trades`

**Backend — API**
- `api/trades.py`, `api/imports.py`, `api/analytics.py`, `api/broker.py`, `api/finance.py` (+ روتر جدید `api/brokers.py` / `api/personal_accounts.py`)

**Backend — Migrations**
- حل دو head + migration جدید ساخت `brokers`, `personal_trading_accounts`, تغییر `trades`

**Frontend**
- `api/client.ts`, `TradesPage.tsx`, `ImportPage.tsx`, `AnalysisPage.tsx`, `FinancePage.tsx`, `PayoutHistoryPage.tsx`, `PropPage.tsx`

**Tests**
- `test_trades.py`, `test_imports.py`, `test_analysis_phase23.py`, `test_analysis_scope.py`, `test_soft_delete_filters.py`, `test_finance.py`

### ۱۷.۲ ریسک‌های کلیدی

| # | ریسک | کاهش |
| :-- | :--- | :--- |
| R1 | دو head alembic | حل در گام صفر Phase 28 (زیر) |
| R2 | نام enum `REAL` در DB درج شده؛ تغییر به `REAL_PERSONAL/REAL_PROP` نیازمند data migration | DB فعلی داده خاص ندارد (طبق درخواست) → راه ساده |
| R3 | `finance_sync_service` بین Account و Trade پل می‌زند | بازطراحی map به `PersonalTradingAccount`/`PropAccount` |
| R4 | frontend به یک endpoint متکی است | endpoint جدید `personal-trading-accounts` |
| R5 | تست‌های بروکر روی `Account(type=BROKER)` | به‌روزرسانی به `PersonalTradingAccount` |

### ۱۷.۳ گزینه‌های حل مشکل Migration (انتخاب Phase 28)

| گزینه | توضیح | پیشنهاد |
| :--- | :--- | :--- |
| **A** | حذف فایل untracked `d4e5f6a7b8c9` (چون DB روی آن است → ابتدا `alembic stamp f1a2b3c4d5e6`) | ✅ ساده و امن |
| **B** | ساخت merge-revision که دو head را یکی کند | اگر می‌خواهید تاریخ حفظ شود |
| **C** | بازنویسی هر دو به یک migration واحد | فقط اگر DB خالی و قابل reset باشد |

---

## ۱۸. سؤالات باز (نیازمند تأیید شما قبل از Phase 27)

1. **PropAccount → Finance Account:** حفظ شود (🟡) یا حذف شود؟ (پیشنهاد: حفظ، ولی فقط با Account نوع مالی)
2. **حل two-head migration:** گزینهٔ A یا B؟
3. **`StrategyVersion.test_type`:** به Enum تبدیل شود یا String بماند؟
4. **scope تحلیل REAL_PERSONAL:** مقدار جدید `PERSONAL_ACCOUNT` در `AnalysisScope` اضافه شود (به‌جای BROKER)؟
5. آیا `Broker` جدید باید مستقل از `Account.broker_name` باشد و دادهٔ فعلی مهاجرت کند؟

---

## ۱۹. پیوست: فایل‌های کلیدی Audit‌شده

| مسیر | نقش |
| :--- | :--- |
| `backend/app/models/strategy.py` | Trade, StrategyVersion, TestType, AnalysisResult/Run |
| `backend/app/models/finance.py` | Account, AccountType, Transaction |
| `backend/app/models/prop.py` | PropFirm/Account/Stage/Withdrawal/Cost/Alert |
| `backend/app/models/personal.py` | JournalReview, Screenshot |
| `backend/app/utils/trade_validator.py` | Trade Contract validation |
| `backend/app/utils/trade_scope.py` | فیلتر REAL از تحلیل |
| `backend/app/services/import_service.py` | Import |
| `backend/app/services/analysis_service.py` | تحلیل |
| `backend/app/services/finance_sync_service.py` | پل Trade→Finance |
| `backend/app/api/{trades,imports,analytics,broker,finance,prop,personal}.py` | Endpointها |
| `backend/migrations/versions/*` | زنجیرهٔ migration |
| `backend/tests/*` | تست‌ها |

---

**پایان Phase 26 (Audit).** بدون هیچ تغییر کد. منتظر تأیید شما برای ورود به **Phase 27 — Trade Contract** هستم.



