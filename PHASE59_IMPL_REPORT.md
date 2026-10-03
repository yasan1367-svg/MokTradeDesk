# Phase 59 — API Contract & Validation

## Summary

Aligned the Trade API contract across backend and frontend, added explicit FK validation, corrected PATCH omitted-vs-null behavior, and mapped trade persistence/validation errors to stable HTTP responses.

## Existing contract findings

- Frontend trade creation sends lowercase `test_type` values (`backtest`, `forward`, `real_personal`, `real_prop`) and Trade serializers return lowercase enum `.value` values.
- SQLAlchemy `Enum(TestType)` / `Enum(TradeSource)` persists member names in the database (for example `BACKTEST`, `MANUAL`). This internal DB representation is intentional and remains unchanged to avoid altering existing data or requiring a migration.
- `TradeUpdate` is declared in `backend/app/api/trades.py`; before this phase, PATCH treated both omitted fields and explicit `null` as “keep existing value.”
- Trade classification validated the required/XOR shape but did not verify referenced rows existed before persisting.

## Changes

- `backend/app/utils/trade_validator.py`
  - Added `validate_fk` for strategy version, personal trading account, and prop stage.
  - Added `TradeReferenceNotFound` with clear missing-reference messages.
- `backend/app/api/trades.py`
  - Reused canonical Enum conversion for manual creation and PATCH.
  - Validate referenced IDs for both manual create and update; map missing references to HTTP 404.
  - PATCH uses `model_dump(exclude_unset=True)`: omitted fields remain unchanged; explicit `null` clears nullable fields. Explicit null for required fields returns HTTP 400.
  - Changing classification clears omitted incompatible destination references; explicitly supplied destinations remain subject to the classification rules.
  - Map invalid values to HTTP 400 and SQLAlchemy `IntegrityError` to HTTP 409 with rollback. Missing Trade remains HTTP 404.
- `frontend/src/api/client.ts`
  - Added canonical lowercase enum tuples/types and a typed Trade PATCH DTO including nullable fields.
- `frontend/src/pages/TradesPage.tsx`
  - Typed the trade creation selector against the canonical TestType contract.
- Tests
  - Added `backend/tests/test_phase59_api_contract.py` with eight tests for enum storage/API contract, FK validation and 404 mapping, omitted/null PATCH semantics, reclassification, error mapping, and DTO field presence.
  - Added a Vitest assertion for canonical Trade enum values.

## Validation

- `backend/venv/Scripts/python.exe -m pytest tests/test_phase59_api_contract.py -q -p no:warnings` — passed (8 tests).
- `backend/venv/Scripts/python.exe -m pytest -q -p no:warnings` — passed with no failures (one expected xfail).
- `backend/venv/Scripts/python.exe -m ruff check app/api/trades.py app/utils/trade_validator.py tests/test_phase59_api_contract.py` — passed.
- `frontend/npx tsc -b --force` — passed.
- `frontend/npx vitest run` — passed (30 tests across 4 files).
- `frontend/npm run build` — passed.
- `git diff --check` — passed.

## Git

Commit and push status: recorded in the completion summary after publishing.