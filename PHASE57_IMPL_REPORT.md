# Phase 57 — Analytics Correction

## Summary

Corrected analytics expectancy, daily return ratios, tail-loss measures, and risk-of-ruin handling. The optional risk management UI now displays dollar and percentage VaR/CVaR and handles missing risk-of-ruin estimates safely.

## Changes

- `backend/app/api/analytics.py`
  - Both `/risk-metrics` and `/risk-advanced` calculate expectancy R through `calculate_expectancy_r` using stored trade `r_multiple` values. Valid zero-R observations remain included; only missing (`None`) values are excluded.
  - Both endpoints calculate daily percentage returns using `RiskEngine._daily_returns_from_trades`, then delegate Sharpe and Sortino to `RiskEngine`.
  - VaR/CVaR remain dollar-denominated under the existing `var_95` / `cvar_95` API keys, are expressed as nonnegative losses, and now include `var_95_percent` / `cvar_95_percent` relative to the scope's initial balance.
  - Added `calculate_risk_of_ruin(...)`, an R-based estimate returning `None` for invalid or insufficient data. Endpoint estimates require at least two non-zero, valid R observations.
- `backend/app/domain/risk/risk_engine.py`
  - Added daily PnL aggregation by close date and normalized returns against opening equity, supporting both ORM-like objects and projected analytics rows.
- `backend/tests/test_phase57_analytics_correction.py`
  - Added eight regression tests for R expectancy and zero-R retention, missing/insufficient risk-of-ruin data, daily returns, both analytics endpoints' ratios, and dollar/percentage VaR/CVaR.
- `backend/tests/test_phase53_risk_metrics.py`
  - Updated the existing ratio reference values to daily percentage returns, matching the corrected API contract.
- `frontend/src/pages/RiskManagementPage.tsx`
  - Displays VaR/CVaR in dollars and as a percentage; missing risk-of-ruin data is shown as unavailable rather than treated as a number.

## Calculation notes

- The endpoints do not accept a per-trade risk setting. Risk-of-ruin uses a documented 1% assumed equity risk per trade and the existing 50% ruin-floor default. Dollar VaR/CVaR are rounded to cents; percentage fields are rounded to four decimal places.
- Existing VaR/CVaR fields retain their names and dollar units to avoid breaking current consumers; the new percentage fields are additive.

## Validation

- `backend/venv/Scripts/python.exe -m pytest tests/test_phase57_analytics_correction.py -q -p no:warnings` — passed (8 tests).
- `backend/venv/Scripts/python.exe -m pytest -q -p no:warnings` — passed (one existing expected xfail; no failures).
- `backend/venv/Scripts/python.exe -m ruff check app/api/analytics.py app/domain/risk/risk_engine.py tests/test_phase57_analytics_correction.py tests/test_phase53_risk_metrics.py` — passed.
- `frontend/npx tsc -b --force` — passed.
- `frontend/npx vitest run` — passed (29 tests across 4 files).
- `frontend/npm run build` — passed.
- `git diff --check` — passed.

## Git

Commit and push status: recorded after validation in the completion summary.