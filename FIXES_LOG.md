# MokTradeDesk — Fixes Log

Track of all fixes applied from DASHBOARD_DATA_CONTRACT_AUDIT.md.

## P1-06 — Dashboard Stale Response Race
- **Date:** 2026-10-08
- **Status:** DONE.
- **Files:** C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx; C:\MokTradeDesk\frontend\src\__tests__\dashboardPage.test.tsx; C:\MokTradeDesk\FIXES_LOG.md.
- **Before:** Main loadDashboard allowed older successes/errors/finalizers to overwrite current data, error and loading state. Backtest already used an effect-local cancellation flag.
- **After:** Independent main/backtest generation counters guard success, error, toast and loading completion paths. Effect cleanup invalidates pending generations on dependency changes and unmount. Backtest's counter advances only for its own lifecycle; main completion does not invalidate it. Empty versions clear backtest loading. The version-list fetch also has an unmount cleanup guard.
- **Tests:** Updated the existing Dashboard fixture/API mocks and outdated layout assertions. Added test_stale_response_is_discarded, stale success/error while a newer main request is pending, stale backtest success/error with independent main loading, and main success/error after unmount (provider remains mounted to detect late toasts).
- **Validation:** npm test -- src/__tests__/dashboardPage.test.tsx: **9 passed**. npm run build: **passed (TypeScript + Vite)**. No full frontend suite or manual browser inspection performed.
- **Scope:** Logical cancellation only; HTTP requests are not aborted. No backend changes. No Git commands or GitHub operations.

## P1-05 — KPI Semantics (R, Breakeven, Loss Label)
- **Date:** 2026-10-08
- **Status:** DONE for the minimal applicable changes.
- **Files:** C:\MokTradeDesk\backend\app\api\analytics.py; C:\MokTradeDesk\backend\app\services\metrics.py; C:\MokTradeDesk\backend\tests\test_analytics.py; C:\MokTradeDesk\backend\tests\test_metrics.py; C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx.
- **Analytics:** Summary adds breakeven_trades, r_sample_count and missing_r_count; AVG and COUNT use the same closed scoped R population, including zero R. No R samples now returns null rather than 0. Today explicitly counts net<0 losses and net=0 breakevens, preserving request-time cap and win-rate denominator.
- **Frontend:** Missing Backtest average R renders an em dash; actual zero remains 0.00. MiniBars gross_loss label changed from بزرگترین ضرر to مجموع زیان.
- **Loss-sign scope:** No avg_loss display exists in the current Dashboard; its loss KPI uses max_dd. No metric substitution or new card added. Analytics avg_loss remains a positive magnitude; shared calculate_basic_metrics signed loss fields remain unchanged (cross-API sign unification is not part of this minimal fix).
- **Streaks:** streaks now resets both current counters on zero, matching win_loss_streaks; historical maxima remain intact.
- **Tests:** Added test_breakeven_not_counted_as_loss (net after commission/swap), test_avg_r_null_when_no_r_samples (empty and missing samples), test_r_sample_count_reported (zero counts, open R excluded), and five cases comparing both streak helpers. Updated an existing exact Today-response assertion for the new breakeven field.
- **Validation:** Requested Analytics + metrics suite: **54 passed, 9 warnings**. Frontend npm run build: **passed (TypeScript + Vite)**. No manual browser inspection or full backend suite run.
- **Local only:** No Git commands or GitHub operations.

## P1-04 — Equity Baseline and Currency Metadata
- **Date:** 2026-10-08
- **Status:** DONE (minimal metadata/tooltip fix).
- **Files:** C:\MokTradeDesk\backend\app\api\analytics.py; C:\MokTradeDesk\backend\tests\test_analytics.py; C:\MokTradeDesk\frontend\src\components\charts\EquityCurveChart.tsx; C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx.
- **Backend:** Dashboard now returns equity_metadata with currency, numeric baseline, baseline_source (accounts/fallback_10000), closed_only=true and normalized scope; summary also includes currency. Source is recorded at the baseline decision branch, so an actual account sum of 10000 is correctly labeled accounts. The numeric _scope_initial_balance contract remains compatible for other callers.
- **Frontend:** EquityCurveChart accepts optional currency (USDT default preserves the Analysis caller); its tooltip uses that prop. Dashboard passes currency={currency}.
- **Unchanged semantics:** Baseline remains synthetic starting capital based on referenced accounts/stages or fallback 10000, not the actual opening balance of the selected period. Equity values, closed-only filtering and KPI calculations are unchanged.
- **Tests:** test_equity_metadata_includes_baseline_and_currency covers IRR with no accounts, zero balance, account balance exactly 10000 and account balance 250000; checks all metadata, summary currency and curve baseline. Initial test fixture omitted required version_id; corrected before final validation.
- **Validation:** Requested tests/test_analytics.py -v: **25 passed, 9 warnings**. Additional risk/scope/export regression run: **23 cases passed** (100%, no failures). Frontend npm run build: **passed (TypeScript + Vite)**. No manual browser inspection.
- **Local only:** No Git commands or GitHub operations.

---

## P0-01 — Historical Query Closed-Only
- **Date:** 2026-10-08
- **File:** C:\MokTradeDesk\backend\app\api\analytics.py:118
- **Problem:** Open trades leaked into summary when no date
- **Fix:** Always require close_time IS NOT NULL on scoped_q
- **Test:** test_historical_summary_excludes_open_trades ✅
- **Status:** DONE

---

## P0-02 — Filter Consistency
- **Date:** 2026-10-08
- **Status:** DONE for the approved minimal scope; broader audit consistency work remains deferred.
- **Problem:** Real Summary ignored selected dates; Recent Trades ignored Dashboard dates and scope. Existing Trades date filtering used open_time and test_type could not represent real (personal + funded prop).
- **Fix:** Real Summary accepts optional date_from/date_to and filters its shared aggregate/drawdown/sparkline query on close_time. Dashboard forwards selected dates. Recent Trades forwards dates, scope, and explicit date_field=close_time. Trades accepts optional validated scope and date_field; real excludes challenge stages, all adds no type restriction. Existing test_type remains an independent intersecting filter.
- **Compatibility:** Omitted date_field retains open_time for legacy callers, including closed Trades-page requests. Dashboard's closed historical request explicitly selects close_time. No automatic global default switch for status=closed was made, to avoid breaking the existing Trades page.
- **Preserved:** Real cards remain Real-only. Yesterday, Backtest panel, and Open Trades request are unchanged. Existing UTC half-open date helper is reused; Analytics date-boundary differences remain outside this minimal fix. No currency conversion.
- **Files:**
  - C:\MokTradeDesk\backend\app\api\finance.py
  - C:\MokTradeDesk\backend\app\api\trades.py
  - C:\MokTradeDesk\frontend\src\api\client.ts
  - C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx
  - C:\MokTradeDesk\backend\tests\test_finance.py
  - C:\MokTradeDesk\backend\tests\test_trades.py
- **New regression tests:**
  - test_real_summary_filters_on_close_time ✅ — no dates, one-sided and combined ranges, open-trade exclusion, inclusive final microsecond, shared sparkline/DD population.
  - test_recent_trades_close_date_and_legacy_open_date ✅ — close-date selection, legacy open-date behavior, range exclusion, invalid parameters.
  - test_recent_trades_scope_matches_dashboard ✅ — real/backtest/forward/all, funded versus challenge, currency and prop-account join combinations.
- **Requested test run:** From C:\MokTradeDesk\backend, `venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_finance.py tests/test_trades.py -v`: **61 passed, 1 failed, 9 deprecation warnings**. Existing test_profit_factor_edge_cases expects AnalysisService._profit_factor(100, 0) == 100; unchanged service/helper returns 999. PF behavior/test was not changed as part of P0-02 (audit P1-02).
- **Build:** `npm run build` from C:\MokTradeDesk\frontend succeeded (TypeScript + Vite); generated production artifacts locally.
- **Focused verification:** The three new tests plus C:\MokTradeDesk\backend\tests\test_phase44_scope.py passed: **12 passed**, including the P0-01 regression.
- **Local only:** No Git commands, GitHub operations, commits, or pushes.

---

## P0-03 — Finance Closed Eligibility
- **Date:** 2026-10-08
- **File:** C:\MokTradeDesk\backend\app\api\finance.py, C:\MokTradeDesk\backend\app\services\finance_metrics.py
- **Problem:** pnl IS NOT NULL was used instead of close_time IS NOT NULL in _compute_real_pnl; funded_pnl lacked closed eligibility.
- **Fix:** Use close_time IS NOT NULL everywhere in the requested realized paths: both _compute_real_pnl branches and funded_pnl. Preserve account/stage/currency filters and net_pnl_sql (COALESCE(pnl, 0) + commission + swap).
- **Scope:** Only the requested eligibility predicates changed; _stage_net_pnl and other calculations remain unchanged.
- **Test:** test_finance_excludes_open_trades_with_pnl, test_finance_includes_closed_with_null_pnl in C:\MokTradeDesk\backend\tests\test_finance.py. Six parameterized cases cover broker and funded prop, open +500 versus closed +100, fees-only -1, and additional swap -2; funded cases also assert funded_pnl directly.
- **Verification:** All six new cases failed before the fix and passed afterward. From C:\MokTradeDesk\backend: `venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_finance.py -v` returned **29 passed, 1 failed, 9 warnings**. The existing test_profit_factor_edge_cases expects 100 but receives 999; PF remains unchanged and outside this fix.
- **Status:** DONE
- **Local only:** No Git commands or GitHub operations.

---

## P1-02 — Profit Factor Contract Unification
- **Date:** 2026-10-08
- **Status:** DONE for the requested minimal scope.
- **Files:** C:\MokTradeDesk\backend\app\api\finance.py, C:\MokTradeDesk\backend\app\services\metrics.py, C:\MokTradeDesk\backend\tests\test_finance.py, C:\MokTradeDesk\backend\tests\test_metrics.py
- **Problem:** Finance Real Summary returned 100 for profit without losses, whereas the shared metrics helper and AnalysisService returned 999; the Finance edge-case test expected the obsolete 100.
- **Chosen contract:** Existing numeric callers retain profit_factor_from_sums: positive gross loss gives profit/loss, profit without losses gives 999.0, and both zero gives 0.0. Finite ratios are not capped (1000 remains 1000). No response schema change.
- **Fix:** Finance Real Summary now calls round(metrics.profit_factor_from_sums(gross_profit, gross_loss), 2). AnalysisService._profit_factor already delegated to that helper, and both basic-metrics paths already used it; no production change was needed there. Updated test_profit_factor_edge_cases to expect 999.0.
- **New helper:** profit_factor_status returns {value: None, status: undefined} for both zero, {value: None, status: no_losses} for profit without losses, and {value: profit/abs(loss), status: finite} otherwise. Added for future callers only; existing APIs were not migrated.
- **Tests:** Added six cross-path cases covering Finance Real Summary, metrics.calculate_basic_metrics and AnalysisService, plus seven status-helper cases including signed losses and finite 999/1000.
- **Verification:** From C:\MokTradeDesk\backend, `venv\Scripts\python.exe -m pytest tests/test_finance.py tests/test_metrics.py tests/test_phase43_unified_metrics.py -v`: **61 passed, 0 failed, 9 deprecation warnings**. The previously failing PF test now passes.
- **Deferred:** Frontend >=999 infinity rendering is unchanged as requested. Other inline 100 sentinels discovered in C:\MokTradeDesk\backend\app\api\strategies.py remain outside the minimal scope; this is not repository-wide unification. Finance's existing gross-sum rounding is unchanged.
- **Local only:** No Git commands or GitHub operations.

---

## P1-01 — Date / Timezone Contract
- **Date:** 2026-10-08
- **Status:** DONE for approved A/B/C scope; full-suite failures and cross-API timezone gap documented below.
- **Files:** C:\MokTradeDesk\backend\app\api\analytics.py; C:\MokTradeDesk\backend\tests\test_analytics.py (new).
- **A — Half-open dates:** Replace UTC 23:59:59 inclusive end with Tehran calendar-day boundaries from tehran_day_bounds and close_time < end_utc. Date-only inputs (stripped length 10) use [Tehran midnight, next Tehran midnight), expressed in UTC. Explicit ISO timestamps remain exact instants, normalized to UTC; naive explicit timestamps remain UTC. Empty/invalid inputs return None. Shared Dashboard/risk filtering uses this contract.
- **B — Request-time cap:** Capture now once before Dashboard database queries; add close_time <= now to the shared Today/period aggregate. This covers Today PnL/count/win-rate and month/quarter/year. There is no separate Today aggregate to cap. Exactly-now trades remain eligible. Today still intersects selected dates; period starts retain their existing definitions.
- **C — Yesterday label:** Convert y_start with to_tehran before Jalali conversion and weekday lookup. Preserve existing half-open eligibility and independence from Dashboard selected dates; correct endpoint docstring.
- **Deferred:** C:\MokTradeDesk\backend\app\utils\date_range.py remains unchanged and UTC-based for Finance/Trades. Analytics now uses Tehran dates; cross-API timezone unification remains deferred. Month/quarter/year starts remain UTC; historical summary is not globally capped at now.
- **Tests added:** 21 cases in test_analytics.py: date-only/explicit timestamp parsing, empty/invalid inputs, inclusive start/final microsecond/exclusive end, future-close exclusion and exactly-now inclusion for Today and periods, Today selected-range intersection, Yesterday Tehran Jalali date/weekday and boundaries.
- **Focused run:** From C:\MokTradeDesk\backend, `venv\Scripts\python.exe -m pytest tests/test_analytics.py tests/test_phase53_risk_metrics.py tests/test_phase44_scope.py -v`: **38 passed, 9 warnings**.
- **Full backend run (once):** `venv\Scripts\python.exe -m pytest -v`: **625 passed, 5 failed, 1 xfailed, 9 warnings**. Complete output saved locally to C:\MokTradeDesk\backend\p1_01_full_suite.log; final summary independently read after terminal closure warning.
- **Full-suite failures:** test_phase36_indexes_exist expects missing ix_trades_is_deleted; three test_phase4_initial_sl cases (test_patch_sl_does_not_change_r_when_initial_sl_exists, test_patch_open_price_without_initial_sl_warns, test_patch_open_price_with_initial_sl_no_warn) raise KeyError: id; test_phase58_migration_adds_modes_and_preserves_legacy_total_mode raises NoSuchTableError: trades. These areas were not changed; no pre-change full-suite baseline was run, so failures are not asserted to be pre-existing.
- **Local only:** No Git commands or GitHub operations.

---

## P1-03 — Export PDF Dashboard Filters
- **Date:** 2026-10-08
- **Status:** DONE for filter forwarding and PDF metadata.
- **Files:** C:\MokTradeDesk\backend\app\api\export.py; C:\MokTradeDesk\frontend\src\api\client.ts; C:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx; C:\MokTradeDesk\backend\tests\test_export.py (new).
- **A — Backend:** export_dashboard_pdf accepts date_from/date_to/scope/currency/version_id and explicitly forwards all five to get_dashboard_data. Omitted filters retain Dashboard defaults (real/USDT/all versions); supplied values are no longer overridden.
- **B — Client:** exportDashboardPdf accepts typed optional filter parameters and sends them as the request query string while retaining blob response handling.
- **C — Dashboard:** Export computes the current selected date range and forwards scope/currency. The selected Backtest version is included only when scope=backtest, avoiding accidental restriction of Real exports by the independent Backtest selector.
- **PDF:** Header prints date bounds, scope, currency, version (All when absent), and generated_at in UTC. User-provided strings are XML-escaped for ReportLab. Monetary labels now use the selected currency rather than hardcoded USDT.
- **Scope limitation:** PDF remains one Analytics summary, not a snapshot of every independently filtered Dashboard panel. In backtest scope the export applies both global dates/currency and the selected version; the independent on-screen Backtest panel retains its existing request. Existing Analytics filtering semantics for individual response sections are unchanged.
- **Tests:** test_export_dashboard_pdf_respects_filters generates a real PDF and spies on the real Analytics call: only two selected-version Backtest trades inside Tehran date boundaries contribute (net=30), excluding out-of-range, other-type, other-version and open trades. Also verifies header flowables, defaults, non-USDT forwarding and invalid filter validation.
- **Verification:** From C:\MokTradeDesk\backend, `venv\Scripts\python.exe -m pytest tests/test_export.py -v`: **6 passed, 9 warnings**. From C:\MokTradeDesk\frontend, `npm run build`: **passed (TypeScript + Vite)**. No manual PDF visual inspection performed.
- **Local only:** No Git commands or GitHub operations.
## P1-FIN-01 — Convert + Paired Accounts
- **Date:** 2026-10-08
- **Status:** Implementation and automated validation complete; working database deployment BLOCKED by revision/schema mismatch.
- **Feature:** CONVERT debits source amount and credits destination amount with account-derived currencies; supports update/delete/reconciliation and account-specific ledger amounts. Positive finite conversion amounts, distinct accounts/currencies, overdraft allowed; destination fields rejected for other transaction types.
- **Paired accounts:** Two ordinary rows, trimmed name with _IRR/_USDT suffixes, atomic opening ADJUSTMENT transactions for nonzero balances, no opening transactions for zero. Scalar balance applies to both and is documented in UI. Duplicate either name (including archived) returns 409. Digital wallets remain USDT-only.
- **Files:** C:\MokTradeDesk\backend\app\models\finance.py; C:\MokTradeDesk\backend\app\services\wallet_service.py; C:\MokTradeDesk\backend\app\api\finance.py; C:\MokTradeDesk\backend\tests\test_finance.py; C:\MokTradeDesk\backend\migrations\versions\cb282f44503c_add_convert_transaction_fields.py; C:\MokTradeDesk\frontend\src\components\AccountForm.tsx; C:\MokTradeDesk\frontend\src\components\TransactionForm.tsx; C:\MokTradeDesk\frontend\src\pages\FinancePage.tsx; C:\MokTradeDesk\frontend\src\api\client.ts; C:\MokTradeDesk\FIXES_LOG.md.
- **Seven tests:** test_create_pair_creates_two_accounts (zero/nonzero); test_convert_debits_and_credits (also update/delete/reconcile/ledger); test_convert_rejects_same_currency; test_convert_rejects_same_account; test_convert_requires_to_amount; test_convert_currency_derived_from_accounts (also mismatch); test_transfer_still_works_for_same_currency.
- **Validation:** requested finance pytest run: 44 passed, 9 deprecation warnings. Frontend TypeScript/Vite production build passed. Corrected migration passed full upgrade, downgrade to parent, and re-upgrade against a temporary SQLite database. No manual browser validation.
- **Migration warning:** working DB initially reported 5691cf13a881, later cb282f44503c (head), but read-only PRAGMA inspection found neither to_amount nor to_currency in transactions. No explicit working-DB upgrade was executed by this task. Cause of revision change is unconfirmed (application has startup auto-upgrade). Working database requires separately approved repair; upgrade head alone will not resolve a database already stamped at head. No rollback/stamp/schema repair attempted.
- **Local only:** No Git commands or GitHub operations.
