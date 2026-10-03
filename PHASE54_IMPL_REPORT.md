# PHASE 54 — Risk Core Foundation: Final Implementation Report

## Summary

Phase 54 added a central risk-calculation foundation under `backend/app/domain/risk/`. The work is split into independent engines and a coordinating facade. Existing API routes were not changed. Tasks 54.1–54.7 are implemented; task 54.8 is this report. **No commit was made for this final report.**

The final full backend test run completed with **460 passed, 1 xfailed**. The seven Phase 54 test files contain **38 collected tests**, not 44. The xfail is an existing expected failure; pytest reported no failures.

## Eight Tasks

| Task | Result | Main deliverables |
|---|---|---|
| **54.1 InstrumentSpec** | Complete, committed | SQLAlchemy model, Alembic migration with four seed instruments, two model tests; commit `6eaa40e` |
| **54.2 CommissionEngine** | Complete, committed | Round-trip commission helper and two tests; commit `ee90e5f` also includes both audit reports |
| **54.3 PositionSizingEngine** | Complete, committed | Risk-budget/lot sizing, seven requested scenarios plus invalid-step case; eight tests; commit `386a360` |
| **54.4 REngine** | Complete, committed | R multiple, expectancy and seven-bucket R distribution; 11 tests; commit `d99576c` |
| **54.5 EquityEngine** | Complete, committed | Realized equity curve and final equity with floating PnL; five tests; commit `e14bf96` |
| **54.6 DrawdownEngine** | Complete, committed | Static DD, peak-to-trough DD and elapsed duration; five tests; commit `c4b69f2` |
| **54.7 RiskEngine Facade** | Complete, committed | Scope-aware orchestration, instrument lookup, sizing and metrics; five tests; commit `e3d62ce` |
| **54.8 Final report** | Complete, not committed | This document |

## New Risk Architecture

`backend/app/domain/risk/` now contains:

- `instrument_spec.py` — broker-independent instrument contract, tick, lot, commission and currency metadata.
- `commission_engine.py` — one-side commission to round-trip commission conversion.
- `position_sizing.py` — risk-budget sizing including round-trip commission, lot-step rounding and min/max constraints.
- `r_engine.py` — realized R multiple, expectancy R and histogram buckets.
- `equity_engine.py` — realized balance/equity curve and a final point adjusted for open-trade floating PnL.
- `drawdown_engine.py` — static and peak-to-trough drawdown plus elapsed drawdown duration.
- `risk_engine.py` — facade coordinating trade loading, scope filtering and the engines above.

The instrument model is registered by `backend/app/main.py` and `backend/migrations/env.py`. The facade remains a domain entry point; it is **not wired into an API route** in this phase.

## Instrument Migration and Seed Data

- Migration: `backend/migrations/versions/54a1b2c3d4e5_phase54_instrument_specs.py`
- Revision: `54a1b2c3d4e5`, parent `f53a1b2c3d4e`
- Creates `instrument_specs` and seeds `EURUSD`, `GBPUSD`, `XAUUSD` and `DJI30`.
- A temporary SQLite database was upgraded through the full migration chain; seed rows were verified and downgrade back to `f53a1b2c3d4e` successfully removed the new table.

**Local database caution:** the final `alembic current` check reports local DB revision `f53a1b2c3d4e`, while Alembic head is `54a1b2c3d4e5`. The current local database has not been upgraded to Phase 54. No migration was run against it as part of final validation. Back up the DB, then explicitly run `alembic upgrade head` when ready to apply the new table and seeds.

## Contracts and Assumptions

- No existing API contract was modified.
- Risk scopes follow existing analytics names: `real`, `backtest`, `forward`, `all`. Real includes personal and prop trades; soft-deleted trades are excluded.
- Facade initial balance defaults to 10,000 only when omitted. It does not infer balances or convert currencies across accounts.
- Position sizing uses `tick_value / tick_size` as value per price unit. Decimal conversion is used for entry-to-SL subtraction at the facade boundary to avoid binary-float artifacts in common decimal prices.
- `0R` is a valid observation; `None` is omitted from expectancy and distribution.
- R histogram labels and edge behavior follow current analytics buckets; `3R` is included in the final `> 3R` bucket as in the existing implementation.
- Equity balance represents realized PnL. Open-trade floating PnL is the current stored `pnl + commission + swap` and is added to final equity only; no mark-to-market is inferred because the trade model has no current-price input.
- Drawdown duration is elapsed fractional 24-hour days, ending at recovery to the prior peak or at the last available dated point if still underwater.
- Sharpe/Sortino use daily PnL returns without annualization, consistent with the existing analytics implementation. They are not presented as account-currency-normalized returns across mixed-currency real accounts.

## Validation

- Phase 54 focused tests: **38 collected and passed** across the seven Phase 54 test modules.
- Full backend suite: **460 passed, 1 xfailed**, no test failures.
- Full Alembic chain on a temporary SQLite DB: upgrade, all four seed records, and downgrade verified.
- `git diff --check` and Python compilation checks passed during task implementation.
- Final requested checks: risk module file listing, top-10 git log, working-tree status, full pytest, and `alembic current` were run.

## Technical Debt / Limitations

1. **Migration pending on local DB:** local revision is behind head (`f53a1b2c3d4e` vs `54a1b2c3d4e5`).
2. **Facade is not yet consumed by API/UI:** the engines are callable Python domain functions, but existing analytics endpoints continue their existing calculation paths.
3. **Float arithmetic remains in financial results:** the domain and DB use floats; next-phase work should consider Decimal-based money/price arithmetic and explicit rounding policies.
4. **Mixed real-account currencies:** `scope="real"` can combine prop/personal trades and the facade currently aggregates them without currency conversion or account-specific balance selection.
5. **Floating PnL is a stored snapshot:** it depends on the current `Trade.pnl` field and is not independently marked to market.
6. **Position sizing assumptions:** correctness depends on each broker's tick value, tick size, commission, lot limits and currency conversion being accurate and current.
7. **Duration input contract:** duration expects equity points ordered by time and compatible datetime awareness; the engine does not normalize unsorted dates or naive/aware mixtures.
8. **Input validation scope:** engines guard known invalid denominators and lot steps, but broad finite-number validation (`NaN`/infinity), negative risk percentages, and malformed instrument specs need a dedicated validation task.
9. **Distribution naming:** the last bucket is named `> 3R` while intentionally containing exactly `3R` to preserve the existing chart contract.

## Suggested Next Phase

1. Back up the local database and apply/verify migration `54a1b2c3d4e5` on a disposable copy before updating the normal local DB.
2. Add a separate, reviewed task to integrate `RiskEngine` with a new additive API endpoint (do not silently replace current API outputs); document scope, currency and initial-balance semantics.
3. Add input-boundary validation for non-finite values, sign/range checks and instrument-spec consistency; test actual broker contract examples including non-USD quote currencies and metals/indexes.
4. Decide a money/price precision and rounding policy, then assess migrating risk calculations from float to Decimal.
5. Validate floating PnL and real-account currency handling against broker statements and independently calculated examples before using sizing output for live order decisions.

## Git

Most recent Phase 54 commits, newest first:

```text
e3d62ce Phase 54.7: RiskEngine facade
c4b69f2 Phase 54.6: DrawdownEngine (static, peak-to-trough, duration) + 5 tests
e14bf96 Phase 54.5: EquityEngine (curve + floating) + 5 tests
d99576c Phase 54.4: REngine (R Multiple, Expectancy, Distribution) + 11 tests
386a360 Phase 54.3: PositionSizingEngine with instrument-aware calculation + 8 tests
ee90e5f Phase 54.2: CommissionEngine + audit reports + 2 tests
6eaa40e Phase 54.1: InstrumentSpec model + migration + 4 seed symbols + 2 tests
```

All seven implementation-task commits are present locally. The final report is intentionally **uncommitted** per instruction. The branch is ahead of `origin/main`; no push was performed.

## Stop Point

Phase 54 implementation tasks 54.1–54.8 are complete. No further changes or commits are included in this report step. Await review before starting another phase.