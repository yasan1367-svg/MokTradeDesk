# PHASE 54.3 — PositionSizingEngine Implementation Report

## Status

**Complete; paused after task 54.3 as requested.** Task 54.2 and its audit reports were committed separately in `ee90e5f`. No API was changed and no commit was created for 54.3.

## Implementation

- Added `backend/app/domain/risk/position_sizing.py` with `calculate_position_size(...)` using the requested risk-budget formula:
  - `risk_budget = account_equity * risk_percent / 100`
  - per-lot total risk includes stop-distance price risk and round-trip commission
  - volume is floored to the lot step, then constrained by minimum and maximum lot
  - minimum lot is rejected with `min_lot_exceeds_risk_budget` if it exceeds budget
  - invalid/nonpositive denominator or lot step returns `invalid_risk`
- Used `math.nextafter` immediately before `floor` to prevent binary floating-point representation from incorrectly flooring an exact lot-step multiple (for example, 0.3 / 0.1) one step too low.
- Added `backend/tests/test_phase54_position_sizing.py` with all seven requested cases plus one invalid-lot-step case.

## Validation

- Requested focused command: `venv\Scripts\python.exe -m pytest tests/test_phase54_position_sizing.py -q -p no:warnings` — **8 passed**.
- Full backend suite: `venv\Scripts\python.exe -m pytest -q -p no:warnings` — **passed**, with one expected xfail and no reported failures.
- Python compilation completed successfully for the engine and its tests; `git diff --check` reported no whitespace errors.

## Scenario Results

- EURUSD: $5,000 equity, 1% budget, 20-pip stop, $10/pip/lot, zero commission → **0.25 lots**, $50 total risk.
- EURUSD: same setup with a 40-pip stop → **0.125 lots**, half the volume.
- XAUUSD: $5,000 equity, 0.5% budget, $5 stop, $1 per price unit per lot → **5 lots**, $25 price risk.
- DJI30 commission case → **7.14 lots**, $99.96 total risk against $100 budget.
- Minimum lot above budget is rejected; a 0.1 lot step rounds down to 0.3; max volume is capped at configured maximum.

## Files

- Added: `backend/app/domain/risk/position_sizing.py`
- Added: `backend/tests/test_phase54_position_sizing.py`
- Added: `PHASE54_3_IMPL_REPORT.md`

## Stop Point

Task 54.3 is complete. Tasks 54.4–54.8 have not been started. Await review/approval before continuing; no commit was made for this task.