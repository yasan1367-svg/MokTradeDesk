# Phase 55 — Remove `suggested_lots` and `position_sizing`

## Executive summary

Removed the legacy position-sizing suggestions from the `/api/analytics/risk-metrics` response and Risk Management page. The account-balance calculation remains internal because it is still used to calculate `risk_of_ruin` and `open_risk_percent`.

The independent Phase 54 Risk Core position-sizing domain engine and its tests are unchanged; this phase removes the obsolete sizing suggestions from the legacy analytics endpoint/UI, not that separate engine.

## Rationale

The user calculates real trade size through MT4 and Glory Money Management and imports the actual `size` with trades. The legacy `suggested_lots` value was not useful for that workflow and relied on simplified assumptions, so the sizing suggestion UI and payload have been removed.

## Changes

- `backend/app/api/analytics.py`
  - Removed the sizing suggestion calculations and `position_sizing` response section from `get_risk_metrics`.
  - Removed the stop-loss and open-price columns that were only needed by those suggestions.
  - Kept the scoped average balance calculation (`avg_b`) for `risk_of_ruin` and `open_risk_percent`.
  - Preserved `risk_of_ruin` and `open_risk_percent` in the response.
- `frontend/src/pages/RiskManagementPage.tsx`
  - Removed the Position Sizing card, including suggested volume/lots and displayed average balance.
  - Kept the Risk Metrics UI, including risk of ruin and open exposure/risk percentage.
- `backend/tests/test_phase53_risk_metrics.py`
  - Replaced old response assertions for `position_sizing.avg_balance` with checks that sizing is absent and risk metrics remain present.
- `frontend/src/api/client.ts`
  - No change: it has no `position_sizing` or sizing response types to remove.
- `backend/tests/test_phase44_scope.py`
  - No change: it does not assert sizing-related response fields.

## Validation

- Backend full suite: `backend\venv\Scripts\python.exe -m pytest -q -p no:warnings` — completed with no failures and one expected `x` (xfail) in the progress output.
- Frontend TypeScript: `npx tsc -b --force` — proceeded to the next command in the validated chain, indicating success.
- Frontend Vitest: `npx vitest run` — **4 test files passed, 29 tests passed**.
- Frontend production build: `npm run build` — TypeScript build proceeded to Vite; Vite reported `✓ built in 4.14s`.
- `git diff --check` — passed.

The terminal wrapper reported an abnormal exit after the long-running chained commands had printed their successful completion output. The validation results above are based on the actual pytest/Vitest/Vite output; the wrapper exit anomaly is noted for transparency.

## Ready for Phase 56

Legacy `suggested_lots`/`position_sizing` suggestions are removed from the risk-metrics API and Risk Management UI. Risk of ruin and open-risk metrics are retained. The separate Phase 54 Risk Core remains intact.