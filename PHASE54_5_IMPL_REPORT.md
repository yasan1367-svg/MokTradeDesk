# PHASE 54.5 — EquityEngine Implementation Report

## Status

**Complete; paused after task 54.5 as requested.** Task 54.4 was committed separately as `d99576c`. No existing API was changed and no commit was created for 54.5.

## Implementation

- Added `backend/app/domain/risk/equity_engine.py`:
  - `calculate_equity_curve(...)` starts from the supplied balance, sorts eligible closed trades by `close_time`, and returns the initial point plus one realized balance/equity point per trade.
  - `calculate_equity_with_floating(...)` keeps `balance` based on closed trades and adds the aggregate open-trade floating net PnL to the final `equity`; the final point also exposes `floating_pnl`.
  - Both calculations exclude trades with `is_deleted=True`. The realized-curve function also ignores open trades (`close_time is None`).
  - Net PnL reuses the project's shared `app.services.metrics.net_pnl` helper, which includes PnL, commission, and swap.
- Added `backend/tests/test_phase54_equity_engine.py` covering initial balance and chronological ordering, $10,000 + $100 - $50, floating PnL, negative PnL, and soft-deleted trade exclusion.

## Validation

- Requested focused command: `venv\Scripts\python.exe -m pytest tests/test_phase54_equity_engine.py -q -p no:warnings` — **5 passed**.
- Full backend suite: `venv\Scripts\python.exe -m pytest -q -p no:warnings` — **passed**, with one expected xfail and no reported failures.
- Python compilation succeeded for the engine and tests; `git diff --check` reported no whitespace errors.

## Floating PnL Contract

Open-trade floating PnL is represented by the trade's current `pnl + commission + swap`. This engine does not derive floating PnL from market prices because the Trade model does not expose a current market price/mark-to-market input. The function returns a final equity point, rather than synthesizing time-series points for open trades.

## Files

- Added: `backend/app/domain/risk/equity_engine.py`
- Added: `backend/tests/test_phase54_equity_engine.py`
- Added: `PHASE54_5_IMPL_REPORT.md`

## Stop Point

Task 54.5 is complete. Tasks 54.6–54.8 have not been started. Await review/approval before continuing; no commit was made for this task.