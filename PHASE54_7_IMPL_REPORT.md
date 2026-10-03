# PHASE 54.7 — RiskEngine Facade Implementation Report

## Status

**Complete; paused after task 54.7 as requested.** Task 54.6 was committed separately as `c4b69f2`. No existing API was changed and no commit was created for 54.7.

## Implementation

- Added `backend/app/domain/risk/risk_engine.py` with the `RiskEngine.calculate_risk_metrics(...)` facade and helpers for trade loading, instrument lookup, daily returns, Sharpe, and Sortino.
- Scope handling follows the existing analytics contract: `real` includes personal/prop real trades, `backtest` and `forward` select their respective test types, and `all` leaves test type unrestricted. Invalid scope raises `ValueError`.
- Queries exclude soft-deleted trades and optionally filter the trade symbol (case-insensitive by normalization).
- The facade uses the existing equity, drawdown, R, and position-sizing engines. R metrics use closed trades; equity curves likewise use closed trades. Initial balance defaults to $10,000 only when omitted (`None`).
- With an instrument spec and a trade containing an SL, position sizing uses the latest eligible trade's entry/SL, `tick_value / tick_size` as value per price unit, and that instrument's lot/commission constraints. Price-distance subtraction uses `Decimal(str(...))` to avoid binary-float drift from common decimal price inputs.
- Daily returns aggregate closed-trade net PnL by closing date and divide by opening balance for the day. Sharpe and Sortino use population deviations and are not annualized, consistent with current analytics behavior.
- Added `backend/tests/test_phase54_risk_engine.py` covering facade metrics, symbol/instrument sizing, backtest scope, real scope, and empty trades.

## Validation

- Requested focused command: `venv\Scripts\python.exe -m pytest tests/test_phase54_risk_engine.py -q -p no:warnings` — **5 passed**.
- Full backend suite: `venv\Scripts\python.exe -m pytest -q -p no:warnings` — **passed**, with one expected xfail and no reported failures.
- Python compilation succeeded for the facade and tests; `git diff --check` reported no whitespace errors.

## Scope / Balance Notes

- Real scope currently combines all real personal and prop trades, following the existing analytics `scope="real"` contract; this facade does not add account/stage-specific filtering.
- If no explicit initial balance is passed, the facade uses the requested fixed $10,000 default. It does not infer or currency-convert account balances.
- The facade is not wired into an API endpoint; existing APIs remain unchanged as required.

## Files

- Added: `backend/app/domain/risk/risk_engine.py`
- Added: `backend/tests/test_phase54_risk_engine.py`
- Added: `PHASE54_7_IMPL_REPORT.md`

## Stop Point

Task 54.7 is complete. Task 54.8 has not been started. Await review/approval before continuing; no commit was made for this task.