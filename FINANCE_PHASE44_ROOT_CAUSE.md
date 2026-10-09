# Finance Phase 44 — Root-Cause Audit (Read-only)

**Scope:** `tests/test_phase44_money.py::test_dashboard_no_double_counting` and `tests/test_phase44_scenario.py::test_scenario_no_double_counting` only. No code, tests, migrations, settings, or existing working-tree changes were edited or reverted. No commit or push was made.

## Executive findings

Both tests fail on `spendable_money.net_pnl`, not on their total-balance assertion. The dashboard currently computes this as `finance_metrics.broker_pnl + finance_metrics.funded_pnl`. The current `broker_pnl()` reads closed `REAL_PERSONAL` Trade rows; it does **not** derive PnL from the PTA initial/current balances or cash movements. The test fixtures create PTA balance differences but no personal trades. Thus their expected broker PnL (500 and 200) is absent from the query and actual broker PnL is zero. In the scenario test, funded PnL of 500 is present, so `net_pnl` is 500 rather than 700. In the first test, no funded trade exists either, so it is zero rather than 500.

This is a confirmed code/fixture mismatch. Whether the implementation or test expectation violates the intended product contract is a **CONTRACT AMBIGUITY**: Phase 44 tests and earlier audit documents describe balance-derived broker PnL, while the current modified `finance_metrics.py` explicitly defines broker PnL as closed-trade PnL. Current diff establishes a plausible direct cause, but cannot decide the product contract.

## Test 1: `test_dashboard_no_double_counting`

### Inputs and expected arithmetic

`backend/tests/test_phase44_money.py::_pta` creates one USD `PersonalTradingAccount` with `initial_balance=1000`, `current_balance=1500`. No `Trade`, cash movement, payout, financial account, or bank transaction is created. The test comment and assertion expect broker PnL `1500 − 1000 = 500`, dashboard `net_pnl=500`, and `total_balance=1500` (current balance counted once).

### Actual calculation and result

`backend/app/api/analytics.py` dashboard section around lines 484–491 calls `broker_pnl`, `broker_balance`, `initial_capital`, and `funded_pnl`; sets `spendable_net = broker_pnl + funded_pnl`. `backend/app/services/finance_metrics.py::broker_pnl` sums `Trade.pnl + commission + swap`, filtered to closed `REAL_PERSONAL` trades linked to PTA currency. There are no such rows, hence broker PnL = 0. `funded_pnl` likewise has no matching funded trade, hence 0. Actual dashboard `net_pnl=0.0`, failing the first assertion (`0 != 500`). `broker_balance` is SUM(current_balance)=1500, so the following expected total-balance assertion would not exhibit double counting if reached.

### Root cause, confidence, smallest correction

- **Confirmed immediate cause:** the fixture encodes balance-derived PnL while the current function reads realized personal-trade PnL.
- **Related file/function:** `backend/app/services/finance_metrics.py::broker_pnl`; consumer `backend/app/api/analytics.py` dashboard spendable-money calculation.
- **No payout/internal transfer/bank income/account double count is involved:** none is seeded. The 500 difference is omitted from the current trade-based query, not counted twice.
- **Smallest correction (conditional on chosen contract):** if broker PnL is intended to be balance/cash-movement-derived as the test expects, restore/implement that formula in `broker_pnl` (including the agreed treatment of deposits/withdrawals). If it is intended to represent closed trade PnL, change this test to create a linked closed `REAL_PERSONAL` trade for 500 and retain the no-double-counting balance assertion. Do not choose between these without product clarification.

## Test 2: `test_scenario_no_double_counting`

### Inputs and expected arithmetic

The test creates a USD PTA at 1000 initial / 1200 current, expecting broker PnL of 200. It creates one closed `REAL_PROP` trade with PnL 500 on an active `FUNDED_REAL` stage (80% share) and sets `total_withdrawn=300`. It then posts a `crypto_wallet` account with balance 300. The test expects `total_balance=1200+500=1700`, `net_pnl=200+500=700`, spendable broker assets 1200, wallet assets 300, and remaining withdrawable stage amount `max(500×80%−300,0)=100`.

### Actual calculation and result

The same dashboard path invokes `broker_pnl` and `funded_pnl`. No linked `REAL_PERSONAL` trade was created, so current broker PnL is 0. The `REAL_PROP` trade is closed, on `FUNDED_REAL`, and in the dashboard currency; `funded_pnl` therefore returns 500. Actual dashboard `net_pnl=0+500=500`, failing the assertion expecting 700. `total_balance` uses `broker_balance + funded_pnl` and is 1200+500=1700; that assertion passes. The financial wallet balance and `total_withdrawn` do not feed dashboard `net_pnl` or `total_balance`. `/api/finance/spendable-assets` reports the existing wallet balance separately and computes remaining stage amount by subtracting `total_withdrawn`; the payout is not added again to prop-stage spendable amount. Those are distinct asset/earnings representations, not the cause of this failure.

### Root cause, confidence, smallest correction

- **Confirmed immediate cause:** fixture expects `broker_pnl=200` from PTA balance delta but has no personal trade; current query only reads closed personal trades.
- **Related file/function:** `backend/app/services/finance_metrics.py::broker_pnl`; dashboard consumer in `backend/app/api/analytics.py`. Spendable assets are assembled in `backend/app/api/finance.py::get_spendable_assets` using `finance_metrics.prop_stage_3`.
- **No double counting is demonstrated:** the broker PnL component is omitted (0 rather than 200). Funded trade PnL contributes once to the asserted `total_balance`; wallet balance is a separate asset. `total_withdrawn=300` is deducted only from withdrawable funded proceeds, not from gross `funded_pnl`.
- **Smallest correction (conditional on chosen contract):** same contract decision as test 1. For trade-based broker PnL, add a closed linked `REAL_PERSONAL` trade carrying 200 and keep balance=1200; for balance-based broker PnL, restore that calculation and its movement adjustments. Preserve the funded 500 and payout/wallet assertions unless product defines a different treatment.

## Metric contracts evidenced in code/tests

- **`broker_balance`:** current balances summed by currency (`finance_metrics.py`); the service docstring says this balance includes profit. In the scenario fixture it is 1200.
- **`broker_pnl`:** current working-tree implementation is sum of net PnL (PnL + commission + swap) from closed, currency-matched `REAL_PERSONAL` trades linked to a PTA. This is explicit in the function docstring and filters.
- **`funded_pnl`:** sum of net PnL for closed, currency-matched `REAL_PROP` trades on `FUNDED_REAL` stages. It is gross stage trading PnL, not user share and not reduced by payouts.
- **`total_balance`:** `broker_balance + funded_pnl`; broker PnL is not separately added. The test’s 1500 / 1700 expected balances follow this formula.
- **`spendable_money.net_pnl`:** dashboard currently defines it as `broker_pnl + funded_pnl`.
- **`prop_stage_3`:** remaining withdrawable proceeds, `max(stage closed net PnL × share − total_withdrawn, 0)`. This is not the same metric as funded PnL.
- **Payout/wallet/bank/internal transfer:** neither failing test has a bank transaction or internal transfer. Scenario includes a wallet balance and received-payout marker. Code comments say received prop payouts already exist in destination account balances; the prop-stage remaining amount subtracts withdrawals. Whether `net_pnl` should include received payout as income is not tested here and is not needed to explain these assertions.

### CONTRACT AMBIGUITY

The two failing test comments define `broker_pnl` as `current_balance − initial_balance` (500 / 200). However, current code defines it as closed personal trade PnL. Existing project audit documents also describe the former balance/movement formula (for example `FINANCE_AUDIT_PART2_BROKER_ACCOUNTS.md` and `FINANCE_AUDIT_PART4_PNL_NET_PROFIT.md`), while the current function implementation and docstring describe the latter. The code alone cannot establish whether the expected contract changed intentionally, whether this working-tree edit is incomplete, or whether the tests are stale. A product decision is required before selecting the minimal correction.

## Working-tree diff and attribution

Read-only status showed existing modifications in `backend/app/services/broker_cash_service.py`, `backend/app/services/finance_metrics.py`, `backend/app/services/financial_reporting.py`, `backend/app/services/wallet_service.py`, and `backend/tests/test_broker_cash_movements.py`, plus pre-existing untracked audit files. `git diff --check` passed. `finance_metrics.py` has an existing diff (24 insertions, 13 deletions); the current `broker_pnl` implementation is the trade-based query described above, which directly explains the observed values against these fixtures. This is evidence of a direct mechanism, **not proof that this file alone is the defect**: contract intent is ambiguous and no clean-tree baseline was run. Other working-tree changes do not participate in the observed dashboard query path for these two fixtures, but no attribution beyond the evidence here is claimed.

## Validation performed

Ran only the two requested tests from `backend` with pytest. Both failed as described: test 1 actual `net_pnl=0.0`; test 2 actual `net_pnl=500.0`; scenario `total_balance=1700.0` passed. No other finance failures were investigated or changed.