# Phase 56 — Equity & Drawdown Migration

## Executive summary

Migrated analytics equity and drawdown calculations to the Phase 54 EquityEngine and DrawdownEngine while retaining existing response keys and UI expectations. Initial balances now come from referenced personal accounts and prop stages when available; missing or non-real scope balances fall back to `10000`.

## Before migration (56.1)

- Dashboard equity curve and maximum drawdown were calculated manually from cumulative PnL initialized at zero.
- `/risk-metrics` calculated drawdown depth and duration manually; duration was exposed as a count of trades.
- `/risk-advanced` built an equity sequence from zero and calculated peak-to-trough drawdown and its curve inline.
- `analytics.py` did not use the Phase 54 equity or drawdown calculation functions.
- `PersonalTradingAccount.initial_balance` stores personal account opening balance. `PropAccount` has no initial-balance field in the current model; `PropStage.initial_balance` is used for prop trades.

## Implementation (56.2)

- `get_dashboard_data`
  - Uses `calculate_equity_curve`, `calculate_peak_to_trough_dd`, and `calculate_static_dd`.
  - Preserves the legacy cumulative-PnL values and `{date, equity}` response shape for `equity_curve` and the sparkline.
  - Uses the larger of static and peak-to-trough DD for `summary.max_dd`.
- `get_risk_metrics`
  - Uses EquityEngine and all requested DrawdownEngine calculations.
  - Preserves `max_drawdown_depth` as a monetary amount and `max_drawdown_duration` as a trade count to avoid changing the existing API/UI contract. The duration engine identifies the underwater period, whose underwater trade points are counted for that field.
- `get_risk_advanced`
  - Uses EquityEngine for balance/equity points and DrawdownEngine for static/peak-to-trough DD, duration, and point-wise drawdown curve values.
  - Keeps the existing `max_drawdown` and `drawdown_curve` response fields/shapes.
- Initial balance selection deduplicates referenced account/stage IDs, filters by currency when an endpoint provides currency, sums the matching opening balances, and uses `10000` if none are available. Backtest/forward scopes use the assumed balance.
- Added `calculate_drawdown_curve` to `backend/app/domain/risk/drawdown_engine.py` so point-wise drawdowns use the same domain logic.
- Added endpoint tests for personal and prop-stage initial balances and a unit test for point-wise drawdown calculation.
- No frontend/API contract changes were made.

## Validation (56.3)

- Full backend suite: `venv\Scripts\python.exe -m pytest -q -p no:warnings` — passed; progress showed one expected xfail and no failures.
- Collected backend tests: **464**.
- Focused regression tests: `tests\test_phase53_risk_metrics.py tests\test_phase54_drawdown_engine.py` — **12 passed**.
- Frontend TypeScript: `npx tsc -b --force` — passed.
- Frontend Vitest: **4 files, 29 tests passed**.
- Frontend build: `npm run build` — passed (`✓ built in 2.65s`).
- `git diff --check` — passed.

## Files changed

- `backend/app/api/analytics.py`
- `backend/app/domain/risk/drawdown_engine.py`
- `backend/tests/test_phase53_risk_metrics.py`
- `backend/tests/test_phase54_drawdown_engine.py`
- `PHASE56_IMPL_REPORT.md`

## Ready for Phase 57

Equity/drawdown calculations in analytics now use the Phase 54 domain engines, and the existing UI/API response contract remains unchanged.