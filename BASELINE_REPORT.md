# 📋 BASELINE_REPORT.md — Phase 0: Repository Audit

> **نوع سند:** Audit فقط — **هیچ کدی تغییر نکرده است** (فقط خواندن + این گزارش).
> **تاریخ audit:** ۱۴۰۵/۰۷/۰۹ (2026-09-29)
> **مدل:** deepseek/deepseek-v4.1-flash
> **Auto-approve:** غیرفعال (هیچ commit / migration / تغییر کد انجام نشد)
> **محیط:** Windows · PowerShell · venv: `backend/venv` (Python 3.12, SQLAlchemy 2.1.1, Alembic 1.20.0)

---

## بخش ۱ — وضعیت Git

### `git status`
```
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
	modified:   backend/app/api/analytics.py
	modified:   backend/app/api/finance.py
	modified:   backend/app/api/prop.py
	modified:   backend/app/models/finance.py
	modified:   backend/app/models/strategy.py
	modified:   backend/app/services/prop_rule_engine.py

Untracked files:
	PHASE36_IMPL_REPORT.md
	backend/benchmarks/
	backend/migrations/versions/c9d0e1f2a3b4_phase36_indexes.py
	backend/tests/test_phase36_performance.py

no changes added to commit
```

⚠️ **یافتهٔ مهم:** working tree **تمیز نیست** — کل کار **Phase 36 (Performance)** کامیت **نشده** است
(۶ فایل modified + ۴ فایل/پوشه untracked).

### `git log --oneline -15`
```
c92ed12 (HEAD -> main, origin/main, origin/HEAD) Phase 32-35: Prop Rule Engine + Withdrawal + Analysis Context + Transfer UI
75d21da Phase 30-32: Import Engine + Duplicate Integrity + Prop Rule Engine Audit
56d9cfc Phase 26-28: Domain Architecture + Trade Contract + PersonalTradingAccount
a42ecad Add FINAL_BLUEPRINT.md - Complete project documentation (Phase 1-25)
e33a658 Phase 25: Soft delete trades + filters
7b40c6b Phase 25: Soft delete trades + batch delete
c502488 Phase 24: Fork improvements + Launcher + Syntax fixes
8045da9 Replace start.cmd with start.vbs + splash.hta
40eecef Phase 24: Fork improvements (test_type, status, rules_note, tree)
5d6360d Phase 23: Fix analysis page scoping (5 bugs)
a732e3e Phase 22: Financial reports (9 endpoints + 6 tabs)
4a360c6 Phase 20-21: Multi-scope analysis + Finance Bridge
9fd024e Phase 20: Multi-scope analysis (6 tabs) + Real money dashboard
cb4c919 Phase 18: Auto-migration protection
9b08a94 Add start.cmd launcher
```

### `git branch -a` / `git remote -v`
```
* main
  remotes/origin/HEAD -> origin/main
  remotes/origin/main

origin  https://github.com/yasan1367-svg/MokTradeDesk.git (fetch)
origin  https://github.com/yasan1367-svg/MokTradeDesk.git (push)
```

| مورد | مقدار |
|:---|:---|
| آخرین commit | `c92ed12` (Phase 32-35) |
| Branch | `main` (تنها branch؛ فقط `origin/main`) |
| Remote | `origin` → GitHub `yasan1367-svg/MokTradeDesk` |
| کد کامیت‌نشده | ✅ دارد (Phase 36) |

---

## بخش ۲ — وضعیت Alembic

### `alembic current`
```
c9d0e1f2a3b4 (head)
```

### `alembic history` (head → base)
```
b8c9d0e1f2a3 -> c9d0e1f2a3b4 (head), phase36_indexes
a7b8c9d0e1f2 -> b8c9d0e1f2a3, phase34_35_analysis_context
f6a7b8c9d0e1 -> a7b8c9d0e1f2, phase33_prop_withdrawal
d4e5f6a7b8c9 -> f6a7b8c9d0e1, phase32_rule_engine
c3d4e5f6a7b8 -> d4e5f6a7b8c9, phase30_import_engine
b2c3d4e5f6a7 -> c3d4e5f6a7b8, phase28_finance_cleanup
a1b2c3d4e5f6 -> b2c3d4e5f6a7, phase28_trade_contract
f1a2b3c4d5e6 -> a1b2c3d4e5f6, phase28_trading_domain
e5f6a7b8c9d0 -> f1a2b3c4d5e6, add is_deleted to trades — Phase 25
a3f7c21b9d84 -> e5f6a7b8c9d0, add test_type to strategy_version — Phase 24
9f1a2b3c4d5e -> a3f7c21b9d84, phase20_analysis_scope
b7d4e19c2f83 -> 9f1a2b3c4d5e, merge_personal_into_finance
51ea09b4aa3d -> b7d4e19c2f83, link_prop_to_finance
1771fcd3af2f -> 51ea09b4aa3d, add_finance_tables
c4838cd01bbd -> 1771fcd3af2f, add_analysis_runs_table
<base> -> c4838cd01bbd, initial schema with trade_hash
```

**Alembic head فعلی:** `c9d0e1f2a3b4` (تک-head ✅ — بدون branch دوگانه)

### `ls migrations/versions/` (۱۶ فایل)
```
1771fcd3af2f_add_analysis_runs_table.py
51ea09b4aa3d_add_finance_tables.py
9f1a2b3c4d5e_merge_personal_into_finance.py
a1b2c3d4e5f6_phase28_trading_domain.py
a3f7c21b9d84_phase20_analysis_scope.py
a7b8c9d0e1f2_phase33_prop_withdrawal.py
b2c3d4e5f6a7_phase28_trade_contract.py
b7d4e19c2f83_link_prop_to_finance.py
b8c9d0e1f2a3_phase34_35_analysis_context.py
c3d4e5f6a7b8_phase28_finance_cleanup.py
c4838cd01bbd_initial_schema_with_trade_hash.py
c9d0e1f2a3b4_phase36_indexes.py
d4e5f6a7b8c9_phase30_import_engine.py
e5f6a7b8c9d0_add_test_type_to_strategy_version.py
f1a2b3c4d5e6_add_is_deleted_to_trades.py
f6a7b8c9d0e1_phase32_rule_engine.py
```

---

## بخش ۳ — مدل‌های موجود

### `ls backend/app/models/`
```
finance.py
imports.py
personal.py
prop.py
settings.py
strategy.py
trading.py
__init__.py
```

> ⚠️ `models/__init__.py` **خالی** است ⇒ مدل‌ها فقط از طریق import مستقیم ماژول‌ها ثبت می‌شوند
> (`migrations/env.py` و `app/main.py`). ریسک ظریف برای `alembic autogenerate`.

### ۳.۱ `models/strategy.py` — خلاصهٔ ساختار
| موجودیت | جدول | نکته |
|:---|:---|:---|
| `StrategyStatus` (enum) | — | ۱۰ مقدار |
| `TradeSource` (enum) | — | MT4_IMPORT / SOFT4X_IMPORT / MANUAL |
| `TestType` (enum) | — | BACKTEST / FORWARD / REAL_PERSONAL / REAL_PROP |
| `AnalysisScope` (enum) | — | VERSION / PROP_STAGE / PERSONAL_ACCOUNT |
| `AnalysisStatus` (enum) | — | PENDING / RUNNING / COMPLETED / FAILED (فاز ۳۵) |
| `Strategy` | `strategies` | — |
| `StrategyVersion` | `strategy_versions` | `test_type` (String), `forked_from_version_id` |
| `Trade` | `trades` | Classification Contract + `trade_hash` + `is_deleted` + `screenshot_path` |
| `CustomTimeInterval` / `TimePoint` | — | بازه‌های زمانی سفارشی |
| `AnalysisResult` | `analysis_results` | «وضعیت جاری» + `UniqueConstraint(scope, scope_key)` + `analysis_run_id` |
| `AnalysisRun` | `analysis_runs` | تاریخچهٔ اجراها + `scope_id`/`filters_snapshot`/`trade_count`/`status` |
| `AnalysisScopeRecord` | `analysis_scopes` | دامنهٔ تحلیل (فاز ۳۴ — نام کلاس متفاوت از enum) |
| `SymbolMapping` | `symbol_mappings` | — |

**نکات مهم:**
- `Trade.__table_args__` شامل `CheckConstraint("ck_trades_classification")` (XOR بین
  `personal_trading_account_id` و `prop_stage_id` بر اساس `test_type`).
- `Trade.prop_stage_id` و `Trade.close_time` → `index=True` (فاز ۳۶).
- `Trade.screenshot_path` (legacy، String) **هم‌زمان** با جدول `Screenshot` وجود دارد ⇒ مفهوم تکراری.
- `Trade` همهٔ مبالغ را `Float` نگه می‌دارد (بدون `Numeric`).

### ۳.۲ `models/personal.py` (کامل)
```python
class JournalReview(Base):
    __tablename__ = "journal_reviews"
    id, trade_id(FK trades.id), setup_quality, execution_quality,
    rule_violations(Text), notes, lessons, rating, created_at
    trade = relationship("Trade", back_populates="reviews")
    screenshots = relationship("Screenshot", back_populates="review", cascade="all, delete-orphan")

class Screenshot(Base):
    __tablename__ = "screenshots"
    id, entity_type(String NOT NULL), entity_id(Integer NOT NULL),
    review_id(FK journal_reviews.id, nullable=True), file_path(String NOT NULL),
    file_hash, description, uploaded_at
    review = relationship("JournalReview", back_populates="screenshots")
```
> الگوی `entity_type` + `entity_id` (Polymorphic دستی)؛ بدون FK مستقیم به trade/prop/personal.

### ۳.۳ `models/prop.py` — خلاصهٔ ساختار
| موجودیت | جدول | نکته |
|:---|:---|:---|
| `StageType` / `StageStatus` / `FailureReason` (enum) | — | — |
| `RuleType` / `Severity` (enum) | — | فاز ۳۲ |
| `WithdrawalStatus` (enum) + `WITHDRAWAL_TRANSITIONS` | — | فاز ۳۳ |
| `PropFirm` | `prop_firms` | — |
| `PropFirmDefaultRules` | `prop_firm_default_rules` | — |
| `PropAccount` | `prop_accounts` | `currency` **String** (نه Enum) · بدون `broker_id` |
| `PropStage` | `prop_stages` | قوانین مرحله + `current_profit` / `total_withdrawn` (cache) |
| `PropWithdrawal` | `prop_withdrawals` | فاز ۳۳: `currency`/`status`/`reference`/`transaction_id`/`created_at` |
| `PropCost` | `prop_costs` | `cost_type` و `currency` **String** |
| `PropAlert` | `prop_alerts` | بدون `type`/`severity`/`dedupe_key` (سادهٔ فاز ۶) |
| `RuleViolation` | `rule_violations` | فاز ۳۲ (append-only تاریخچهٔ ارزیابی) |

**نکات مهم:**
- `models/prop.py` خط ۷: `from .finance import Currency` ⇒ وابستگی PROP → FINANCE در سطح مدل.
- `PropAccount.currency`، `PropCost.currency`، `PropCost.cost_type` = `String` ⇒ ناهمگونی با `Currency` Enum.
- `PropAlert.is_read` از نوع `Integer` (نه `Boolean`).

---

## بخش ۴ — جستجوی موجودیت‌های مشکوک

> ⚠️ نکتهٔ فنی: الگوی درخواستی `--include=".py"` و `**` در PowerShell بازگشتی نیست؛
> جستجوها با `Get-ChildItem -Recurse | Select-String` معادل‌سازی و دوباره اجرا شدند.

### ۴.۱ `AnalysisRun | analysis_run | analysis_runs` → ✅ **پیاده‌سازی‌شده**
`app/`:
```
app/api/analytics.py:10      from ..models.strategy import ..., AnalysisRun, ...
app/api/analytics.py:987     runs = db.query(AnalysisRun).filter(
app/api/analytics.py:988         AnalysisRun.version_id == version_id
app/api/analytics.py:989     ).order_by(AnalysisRun.created_at.desc()).all()
app/models/strategy.py:119   analysis_runs = relationship(
app/models/strategy.py:282   analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), ...)
app/models/strategy.py:292   analysis_run = relationship("AnalysisRun", ...)
app/models/strategy.py:296   class AnalysisRun(Base):
app/models/strategy.py:297       __tablename__ = "analysis_runs"
app/services/analysis_service.py:137  run = AnalysisRun(
app/services/analysis_service.py:159  result.analysis_run_id = run.id
app/utils/trade_scope.py:46  """... AnalysisResult / AnalysisRun ..."""
```
`tests/`: `test_analysis_scope.py` (۱۱ ارجاع)، `test_phase34_35_analysis_context.py` (۱۴ ارجاع)
⇒ **موجود است**: مدل + سرویس + API (`GET /api/analytics/{version_id}/history`) + تست.

### ۴.۲ `Screenshot` → ✅ **موجود** (اما دوگانه با `Trade.screenshot_path`)
```
app/models/personal.py:25   class Screenshot(Base):       ← جدول screenshots
app/models/strategy.py:160  screenshot_path = Column(String, nullable=True)   ← legacy
app/api/personal.py:10      from ..models.personal import JournalReview, Screenshot
app/api/personal.py:51      POST /journal/reviews/{review_id}/screenshots
app/api/personal.py:96      GET  /journal/reviews/{review_id}/screenshots
app/api/personal.py:114     DELETE /journal/reviews/screenshots/{screenshot_id}
app/api/trades.py:12        from ..models.personal import Screenshot
app/api/trades.py:108       def _get_screenshots_count_map(...)
app/api/trades.py:113-116   query(Screenshot.entity_id, count) ... entity_type == "trade"
app/main.py:146             storage/screenshots (StaticFiles mount: /storage)
```
> ⚠️ **دو منبع حقیقت برای اسکرین‌شات:** `Trade.screenshot_path` (String) و جدول `Screenshot`
> (`entity_type`/`entity_id`). `entity_type` = `"trade"` یا `"review"`.

### ۴.۳ `ImportBatch | import_batch | import_batches` → ✅ **پیاده‌سازی‌شده (فاز ۳۰/۳۱)**
```
app/models/imports.py:103   class ImportBatch(Base):        ← import_batches
app/models/imports.py:137   class ImportBatchRow(Base):     ← import_batch_rows
app/models/imports.py:187   ImportIdentity.batch_id → import_batches.id
app/services/import_engine.py:28,29,706,726,796,808,828,856,1090   (منطق کامل)
app/api/import_engine.py:276  GET  /batches
app/api/import_engine.py:292  GET  /batches/{batch_id}
app/api/import_engine.py:50,298  (CommitRequest / توضیحات)
```

### ۴.۴ `FinancialAccount | FinancialTransaction` → ❌ **مدل وجود ندارد** (فقط در متن/کامنت)
```
app/api/prop.py:900         (توضیح: FinancialTransaction از نوع PROFIT)
app/models/imports.py:15    (کامنت: Import هرگز FinancialAccount نمی‌سازد)
app/models/prop.py:65,190   (کامنت‌های فاز ۳۳)
app/models/trading.py:8,24  (کامنت: FinancialAccount ≠ TradingAccount)
app/services/import_engine.py:14, payout_service.py:1  (کامنت)
tests/test_import_engine.py:8,367  (نام تست)
```
⇒ **هیچ کلاس/جدولی به نام `FinancialAccount` یا `FinancialTransaction` وجود ندارد.**
این‌ها هدف **Phase 37** هستند (یکسان‌سازی نام `Account`/`Transaction`).

### ۴.۵ `class Account | class Transaction | class LedgerTransaction`
```
app/models/finance.py:14   class AccountType(str, enum.Enum):        ← enum (نه مدل)
app/models/finance.py:38   class TransactionType(str, enum.Enum):    ← enum (نه مدل)
app/models/finance.py:51   class Account(Base):                      ← جدول accounts
app/models/finance.py:99   class Transaction(Base):                  ← جدول transactions
app/api/finance.py:45,53,75,89   AccountCreate/AccountUpdate/TransactionCreate/TransactionUpdate (Pydantic)
```
**هیچ `LedgerTransaction` وجود ندارد** ⇒ «نامشخص/بی‌ربط به کد فعلی».

### ۴.۶ `Decimal | Numeric` در `app/models/` → ❌ **صفر مورد**
```
(none = no matches)
```
⇒ **همهٔ مبالغ `Float` هستند** (Trade.pnl, Account.balance, Transaction.amount, PropStage.*).
عدم دقت اعشاری برای پول ⇒ موضوع Phase 37/38.

### ۴.۷ `utcnow | timezone | UTC` در `app/models/` → ✅ (بدون `utcnow`)
خلاصه (۴۹ مورد؛ نمونه):
```
strategy.py:6,83,105,144,145,162,219,231,279,341,367,368,370,383
finance.py:2,61,93,108,116
prop.py:3,99,116,129,156,177,179,192,207,220,241
imports.py:19,94,115,116,182,183
personal.py:3,19,35
settings.py:2,12,17
trading.py:11,32,53
```
⇒ **هیچ `datetime.utcnow()` باقی نمانده**؛ الگو: `datetime.now(timezone.utc)`.
⚠️ ناهمگونی: بخشی از ستون‌ها `DateTime` (naive) و بخشی `DateTime(timezone=True)` هستند.

---

## بخش ۵ — ساختار API

### دایرکتوری‌ها
```
app/api/       analytics.py  backup.py  broker.py  export.py  finance.py  imports.py
               import_engine.py  personal.py  prop.py  settings.py  strategies.py
               symbol_mappings.py  trades.py  trading.py  __init__.py
app/services/  analysis_service.py  backup_service.py  finance_sync_service.py
               import_engine.py  import_service.py  payout_service.py
               prop_rule_engine.py  __init__.py
app/schemas/   analytics.py  prop.py  strategy.py
```

### endpointها (مسیرهای `@router.*` + prefix از `main.py`)

> prefixها طبق `app/main.py`: `strategies → /api/strategies`, `prop → /api/prop`,
> `personal → /api/personal`, `imports → /api/imports`, `import_engine → /api/imports`,
> `analytics → /api/analytics`, `export → /api/export`, `trades → /api/trades`,
> `symbol_mappings → /api/symbol-mappings`, `settings → /api/settings`,
> `finance → /api/finance`, `broker → /api/broker`, `trading → /api/trading`,
> `backup → /api/backup`

**`prop.py`** (prefix `/api/prop`):
```
GET    /api/prop/firms
POST   /api/prop/firms
GET    /api/prop/firms/{firm_id}/default-rules
GET    /api/prop/accounts
POST   /api/prop/accounts
GET    /api/prop/accounts/{account_id}
GET    /api/prop/stages/all
GET    /api/prop/stages/{stage_id}/check-pass
POST   /api/prop/stages/{stage_id}/pass
POST   /api/prop/stages/{stage_id}/fail
PATCH  /api/prop/stages/{stage_id}/rules
GET    /api/prop/stages/{stage_id}/trades
POST   /api/prop/stages/{stage_id}/evaluate
GET    /api/prop/stages/{stage_id}/violations
POST   /api/prop/stages/{stage_id}/withdraw
GET    /api/prop/stages/{stage_id}/withdrawals
GET    /api/prop/payouts
GET    /api/prop/payouts/stats
POST   /api/prop/payouts
PUT    /api/prop/payouts/{payout_id}
PATCH  /api/prop/payouts/{payout_id}
DELETE /api/prop/payouts/{payout_id}
POST   /api/prop/payouts/{payout_id}/status
POST   /api/prop/payouts/{payout_id}/transfer
GET    /api/prop/alerts
PATCH  /api/prop/alerts/{alert_id}/read
POST   /api/prop/alerts/generate
POST   /api/prop/costs
GET    /api/prop/accounts/{account_id}/costs
GET    /api/prop/analytics
```

**`trades.py`** (prefix `/api/trades`):
```
GET    /api/trades/
GET    /api/trades/{trade_id}
PATCH  /api/trades/{trade_id}
DELETE /api/trades/{trade_id}
POST   /api/trades/batch-delete
POST   /api/trades/manual
POST   /api/trades/{trade_id}/screenshots
GET    /api/trades/{trade_id}/screenshots
DELETE /api/trades/screenshots/{screenshot_id}
```

**`imports.py`** (prefix `/api/imports`):
```
POST   /api/imports/soft4x
POST   /api/imports/mt4
```

**`import_engine.py`** (prefix `/api/imports` — همان prefix، فاز ۳۰):
```
POST   /api/imports/preview
POST   /api/imports/commit/{batch_id}
POST   /api/imports/batches/{batch_id}/cancel
GET    /api/imports/batches
GET    /api/imports/batches/{batch_id}
GET    /api/imports/profiles
GET    /api/imports/profiles/{profile_id}
POST   /api/imports/profiles
PATCH  /api/imports/profiles/{profile_id}
DELETE /api/imports/profiles/{profile_id}
```

**`analytics.py`** (prefix `/api/analytics`):
```
POST   /api/analytics/analyze/{version_id}
POST   /api/analytics/analyze/version/{version_id}
POST   /api/analytics/analyze/prop/{prop_stage_id}
POST   /api/analytics/analyze/personal-account/{personal_trading_account_id}
GET    /api/analytics/dashboard
GET    /api/analytics/yesterday
GET    /api/analytics/risk-metrics
GET    /api/analytics/risk-advanced
GET    /api/analytics/calendar
GET    /api/analytics/analysis/version/{version_id}
GET    /api/analytics/analysis/prop/{prop_stage_id}
GET    /api/analytics/analysis/personal-account/{personal_trading_account_id}
GET    /api/analytics/{version_id}
GET    /api/analytics/{version_id}/history
POST   /api/analytics/compare
GET    /api/analytics/intervals/
POST   /api/analytics/intervals/
DELETE /api/analytics/intervals/{interval_id}
POST   /api/analytics/intervals/seed-gold
POST   /api/analytics/intervals/seed-dji
```

---

## بخش ۶ — باگ‌های شناخته‌شده (تأیید / رد)

| # | الگو | نتیجه | توضیح |
|:--|:---|:---|:---|
| BUG-01 | `current_profit -= amount` (prop.py) | ❌ **رد** | یافت نشد |
| BUG-02 | `current_profit -= request.amount` (prop.py) | ❌ **رد** | یافت نشد |
| BUG-03 | `sum(t.pnl)` (analysis_service.py) | ❌ **رد** | یافت نشد (الگوی فعلی `basic["net_pnl"]`/`net_pnl` است) |
| BUG-04 | `def _summarize` (analysis_service.py) | ✅ **تأیید** | موجود در خط **۷۲۴** |
| BUG-05 | `def calculate_stage_progress` (analysis_service.py) | ❌ **رد** | حذف شده است |
| BUG-06 | `def pass_stage` (prop.py) | ✅ **تأیید** | موجود در خط **۳۷۷** |

خروجی خام:
```
### BUG-01 current_profit -= amount
### BUG-02 current_profit -= request.amount
### BUG-03 sum(t.pnl)
### BUG-04 def _summarize
app\services\analysis_service.py:724:    def _summarize(self, trades: List[Trade]) -> Dict[str, Any]:
### BUG-05 def calculate_stage_progress
### BUG-06 def pass_stage
app\api\prop.py:377:def pass_stage(stage_id: int, request: PassStageWithRulesRequest, db: Session = Depends(get_db)):
```

---

## بخش ۷ — تست‌ها

### `ls backend/tests/`
```
conftest.py
test_analysis_phase23.py
test_analysis_scope.py
test_duplicate_integrity.py
test_finance.py
test_imports.py
test_import_engine.py
test_phase32_rule_engine.py
test_phase33_withdrawal.py
test_phase34_35_analysis_context.py
test_phase36_performance.py
test_prop.py
test_soft_delete_filters.py
test_trades.py
test_trading_domain.py
__init__.py
```

### `pytest --collect-only -q` (خلاصه)
```
tests/test_analysis_phase23.py: 9
tests/test_analysis_scope.py: 14
tests/test_duplicate_integrity.py: 10
tests/test_finance.py: 23
tests/test_import_engine.py: 20
tests/test_imports.py: 5
tests/test_phase32_rule_engine.py: 12
tests/test_phase33_withdrawal.py: 10
tests/test_phase34_35_analysis_context.py: 10
tests/test_phase36_performance.py: 8
tests/test_prop.py: 10
tests/test_soft_delete_filters.py: 11
tests/test_trades.py: 19
tests/test_trading_domain.py: 6
```

| مورد | مقدار |
|:---|:---|
| تعداد کل تست‌ها | **۱۶۷** (جمع ستون‌های فوق) |
| آخرین اجرای کامل (قبل از این Audit) | `167 passed` ✅ |
| فریم‌ورک | pytest (`backend/pytest.ini` → `testpaths = tests`, `addopts = -q`) |

> تست‌ها **اجرا نشدند** (این Phase فقط Audit است و اجرای تست در دستور آمده بود فقط به‌صورت
> `--collect-only`)؛ اما در Phase 36 آخرین اجرای کامل ۱۶۷ passed بود.

---

## بخش ۸ — گزارش‌های Phase موجود

### ریشهٔ پروژه — `PHASE*.md` (۴۷ فایل)
```
PHASE6_DARKMODE_REPORT.md            PHASE20_DESIGN.md
PHASE6_1_DARKMODE_CHILDREN_REPORT.md PHASE20_REPORT.md
PHASE7_DARKMODE_REPORT.md            PHASE21_REPORT.md
PHASE8_DARKMODE_REPORT.md            PHASE22_REPORT.md
PHASE9_REPORT.md                     PHASE23_REPORT.md
PHASE10_REPORT.md                    PHASE24_REPORT.md
PHASE11_REPORT.md                    PHASE25_REPORT.md
PHASE12_REPORT.md                    PHASE25_PART2_REPORT.md
PHASE13_REPORT.md                    PHASE26_DOMAIN_ARCHITECTURE.md
PHASE14_1_REPORT.md                  PHASE26_REPORT.md
PHASE14_2_REPORT.md                  PHASE27_TRADE_CONTRACT.md
PHASE14_3_REPORT.md                  PHASE28_PERSONAL_TRADING_ACCOUNT.md
PHASE14_4_REPORT.md                  PHASE30_IMPORT_ENGINE.md
PHASE14_5_REPORT.md                  PHASE31_DUPLICATE_INTEGRITY.md
PHASE15_1_REPORT.md                  PHASE32_PROP_RULE_ENGINE.md
PHASE15_2_REPORT.md                  PHASE32_IMPL_REPORT.md
PHASE15_3_REPORT.md                  PHASE33_IMPL_REPORT.md
PHASE15_4_REPORT.md                  PHASE33_FRONTEND_FIX.md
PHASE15_5_7_10_REPORT.md             PHASE33_FRONTEND_TRANSFER.md
PHASE15_11_12_REPORT.md              PHASE34_35_IMPL_REPORT.md
PHASE16_REPORT.md                    PHASE34_35_COMPLETION.md
PHASE17_REPORT.md                    PHASE36_IMPL_REPORT.md
PHASE18_REPORT.md
PHASE19_REPORT.md
```

### `REPORT*.md` در ریشه / `PHASE*.md` و `REPORT*.md` در `backend/`
- ریشه: هیچ فایل با الگوی `REPORT*.md` (فقط `PHASE*_REPORT.md`) — **هیچ**
- `backend/`: **هیچ** فایل `PHASE*.md` یا `REPORT*.md`
- (این گزارش: `BASELINE_REPORT.md` در ریشه پروژه — تنها فایل ساخته‌شده در این Phase)

---

## 🧭 خلاصهٔ یافته‌های کلیدی (برای Phase 1 و بعد)

| # | یافته | اهمیت |
|:--|:---|:---|
| ۱ | **Working tree کامیت‌نشده دارد** (کل Phase 36) | 🔴 قبل از هر فاز جدید باید تصمیم commit گرفته شود |
| ۲ | `FinancialAccount`/`FinancialTransaction` **وجود ندارند** (فقط کامنت) | 🟠 هدف Phase 37 |
| ۳ | **همهٔ مبالغ `Float`**؛ `Decimal/Numeric` صفر مورد | 🔴 دقت پول (Phase 37/38) |
| ۴ | **اسکرین‌شات دوگانه**: `Trade.screenshot_path` + جدول `Screenshot` | 🟠 دو منبع حقیقت |
| ۵ | `models/__init__.py` **خالی** ⇒ ریسک ثبت مدل برای autogenerate | 🟡 |
| ۶ | `PropAccount.currency`/`PropCost.*` از نوع **String** (نه `Currency`) | 🟠 ناهمگونی واحد پول |
| ۷ | `PropAlert.is_read` از نوع **Integer** (نه Boolean) | 🟡 |
| ۸ | ناهمگونی `DateTime` (naive) و `DateTime(timezone=True)` در مدل‌ها | 🟡 |
| ۹ | `_summarize` (analysis_service.py:724) و `pass_stage` (prop.py:377) **باقی‌مانده‌اند** | 🟡 بازبینی لازم |
| ۱۰ | هیچ `datetime.utcnow()` باقی نمانده ✅ | 🟢 |

### ❓ موارد «نامشخص» (طبق قانون: اعلام و رد شدن)
1. **هدف دقیق Phase 38/39:** متن کامل دریافت نشده ⇒ نامشخص.
2. **آیا `LedgerTransaction` در Master Plan مورد انتظار است؟** در کد فعلی هیچ اثری ندارد ⇒ نامشخص.
3. **آیا `AnalysisRun` باید با `AnalysisScopeRecord` یکی شود یا موازی بماند؟** (فعلاً موازی، فاز ۳۴/۳۵) ⇒ تصمیم معماری نامشخص.
4. **واحد پول پیش‌فرض برای مهاجرت `Float → Numeric`:** در سند Master مشخص نبود ⇒ نامشخص.
5. **مقدار واقعی داده در DB کاربر** (تعداد رکوردها برای مهاجرت): در `trading_desk.db` محلی،
   `trades=175`, `transactions=0`, `accounts=0`, `analysis_results=1` بود؛ اما DB واقعی کاربر نامشخص است.

---

## ⛔ پایان Phase 0 — توقف

- ✅ هیچ کدی تغییر نکرد، هیچ migration ساخته نشد، هیچ commit زده نشد.
- ✅ تنها فایل ساخته‌شده: **`BASELINE_REPORT.md`** (طبق دستور).
- ⏸️ منتظر دستور بعدی.




