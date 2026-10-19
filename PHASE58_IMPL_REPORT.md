# Phase 58 — Configurable Drawdown Basis & Daily/Total DD Modes

## 1. Objective

Allow Prop stage evaluation to use configurable:

- **dd_basis** (`balance` | `equity`) — whether Total DD and Equity/Balance rule checks
  include open (floating) trade PnL.
- **daily_dd_mode** (`static` | `trailing`) — daily loss measured as net day result or
  largest intraday peak-to-trough move.
- **total_dd_mode** (`static` | `trailing`) — Total DD measured from initial balance or
  from running equity peak.

Floating PnL is included in DD calculations **only** when `dd_basis="equity"`.
`ready_to_pass` is now derived from every `rule_check` severity (including floating-loss
and stage-status violations), not from closed-trade-only flags.

## 2. Changes

### 2.1 Model (`backend/app/models/prop.py`)

```python
dd_basis       = Column(String(20), default="balance", nullable=False, server_default="balance")
daily_dd_mode  = Column(String(20), default="static",  nullable=False, server_default="static")
total_dd_mode  = Column(String(20), default="static",  nullable=False, server_default="static")
```

The legacy `dd_mode` column remains (for backward compatibility) and is no longer used
by the evaluator. The Phase 58 migration copies its value into `total_dd_mode` for
existing rows.

### 2.2 Migration (`backend/migrations/versions/58a1b2c3d4e5_phase58_prop_dd_config.py`)

- Chained to `54a1b2c3d4e5` (current head at implementation time).
- Adds `daily_dd_mode` and `total_dd_mode` columns (idempotent, `server_default="static"`).
- Migrates existing `dd_mode` (Phase 47) → `total_dd_mode` where value is `static` or `trailing`.
- `dd_basis` already exists from Phase 47 migration; Phase 58 does not re-add it.
- `downgrade()` drops only the two new columns.

### 2.3 Evaluator (`backend/app/services/prop_rule_engine.py`)

**`_evaluate_stage_with_trades`**
- `dd_basis` selects the equity curve:
  - `balance` → `calculate_equity_curve` (closed-trade realized equity).
  - `equity` → `calculate_equity_with_floating` (includes open-trade PnL).
- `daily_dd_mode` delegates to new `_daily_drawdowns` helper.
- `total_dd_mode` delegates to `calculate_static_dd` or `calculate_peak_to_trough_dd`
  from `drawdown_engine`.
- `equity` always = realized `balance` + `floating_pnl` (matching historical `current_profit`).
- `current_profit` = closed PnL + floating PnL (historical semantics preserved).
- `ready_to_pass` = `(not unconfigured) & target_reached & min_days_met & ALL rule_checks != VIOLATION`.
- Invalid mode values → stage becomes `unconfigured` (fail-closed).

**`_daily_drawdowns`** (new helper)
- Groups closed trades by adjusted UTC day.
- `static` mode: `max(0, -sum(PnL))` per day.
- `trailing` mode: maximum `peak - running_equity` within the day.
- When `floating_pnl` is provided (equity basis), today's floating position is
  appended as the last point in today's series.

**`_build_rule_checks`**
- Added `dd_basis_value`, `dd_basis`, `floating_enabled` parameters.
- EQUITY_BALANCE rule uses `dd_basis_value` (not global `equity`).
- FLOATING_PNL rule severity is `PASS` when `floating_enabled=False` — floating loss
  still appears in output but does not block pass or raise overall severity.

### 2.4 API (`backend/app/api/prop.py`)

- `StageRules` and `StageRulesUpdate` schemas accept `dd_basis`, `daily_dd_mode`, `total_dd_mode`.
- Pydantic `model_validator` rejects values outside `{balance,equity}` / `{static,trailing}`.
- `update_stage_rules` endpoint writes the three new fields.
- `pass_stage` endpoint propagates the new fields to the next stage (defaults from current stage).
- `get_account_detail` response includes `dd_basis`, `daily_dd_mode`, `total_dd_mode`.

### 2.5 Frontend

**`frontend/src/api/client.ts`**
- `updateStageRules` data type extended with `dd_basis`, `daily_dd_mode`, `total_dd_mode`.
- `passStageWithRules` `nextStageRules` type extended.

**`frontend/src/pages/PropPage.tsx`**
- `Stage` interface: added `dd_basis`, `daily_dd_mode`, `total_dd_mode`.
- `editRules` state: added select controls for DD basis, daily mode, total mode.
- Edit form: three new `<select>` dropdowns added.
- `handleSaveStageRules`: sends new fields.
- Pass modal: three new `<select>` dropdowns for next-stage rules.
- `handleConfirmPass` button: disabled when `!passProgress.ready_to_pass` (not just DD violations).
- `handleOpenPassModal` initializes new fields to defaults.

## 3. Compatibility

| Aspect | Decision |
|--------|----------|
| `current_profit` | Still closed + floating (historical contract). |
| `ready_to_pass` | Now uses full `rule_checks` severity. A floating-loss violation in equity basis blocks pass. |
| Profit target | Still measured on closed PnL only. Floating profit does not qualify a pass. |
| Legacy `dd_mode` | Preserved in DB, not read by evaluator; value is migrated to `total_dd_mode`. |
| `dd_basis` column | Already exists from Phase 47; Phase 58 migration does not re-add it. |
| Existing test suite | All 480 backend tests pass (including new Phase 58 cases); 29 frontend tests pass. |

## 4. Tests Added

### Backend — `test_phase47_prop_rules.py` (11 new cases)

1. `test_prop_stage_new_drawdown_defaults` — default values assert.
2. `test_equity_basis_includes_floating_loss_and_blocks_pass` — open -1200 on equity basis ⇒ VIOLATION for both EQUITY_BALANCE and FLOATING_PNL, `ready_to_pass=False`.
3. `test_balance_basis_ignores_floating_for_drawdown_and_pass` — balance basis, floating loss ⇒ PASS for FLOATING_PNL rule, max_total_dd=0.
4. `test_daily_drawdown_modes[static|trailing]` — two same-day trades: static=0, trailing=300.
5. `test_total_drawdown_modes[static|trailing]` — two-day up-down: static=0, trailing=300.
6. `test_ready_to_pass_requires_target_days_and_no_violations` — stage-status VIOLATION blocks pass.
7. `test_invalid_mode_fails_closed` — `daily_dd_mode="unsupported"` ⇒ `unconfigured=True`.
8. `test_ready_to_pass_is_false_until_profit_target_reached` — 499 of 500 target ⇒ not ready.
9. `test_ready_to_pass_is_false_until_minimum_days_reached` — target hit but 1 of 2 days ⇒ not ready.
10. `test_equity_basis_open_floating_drawdown_fails_total_rule` — -1200 open on equity ⇒ max_total_dd=1200 violated.
11. `test_equity_basis_open_floating_loss_counts_daily_dd` — -700 open on equity ⇒ daily_dd violated.

### Backend — `test_phase32_rule_engine.py` (2 new cases)

12. `test_stage_rules_endpoint_updates_modes_and_rejects_invalid_mode` — PATCH rules 200/422.
13. `test_account_detail_exposes_drawdown_modes` — GET account detail returns mode fields.

### Backend — `test_phase58_prop_migration.py` (1 new case)

14. `test_phase58_migration_adds_modes_and_preserves_legacy_total_mode` — SQLite migration integrity.

### Frontend

29 existing Vitest tests pass. TypeScript strict build succeeds.

## 5. Validation Summary

| Check | Result |
|-------|--------|
| Backend pytest (480 tests) | All passed, 1 expected xfail |
| Frontend vitest (29 tests) | All passed |
| Frontend `tsc -b && vite build` | Succeeded |
| Migration applied | `54a1b2c3d4e5` → `58a1b2c3d4e5` |
| `alembic current` | `58a1b2c3d4e5 (head)` |
| `alembic heads` | Single head |
| Git diff —check | Clean |
| Working tree | 7 modified + 2 new files |

## 6. Files Changed

```
 M backend/app/api/prop.py                    # +40  lines — schemas, validators, endpoints
 M backend/app/models/prop.py                 # +4   lines — mode columns
 M backend/app/services/prop_rule_engine.py   # +196/-37 lines — full mode-aware evaluation
 M backend/tests/test_phase32_rule_engine.py  # +32  lines — API endpoint tests
 M backend/tests/test_phase47_prop_rules.py   # +156 lines — engine tests
 M frontend/src/api/client.ts                 # +6   lines — TypeScript types
 M frontend/src/pages/PropPage.tsx            # +77  lines — edit form & pass modal selectors
A  backend/migrations/versions/58a1b2c3d4e5_phase58_prop_dd_config.py  (new migration)
A  backend/tests/test_phase58_prop_migration.py                        (new migration test)
```