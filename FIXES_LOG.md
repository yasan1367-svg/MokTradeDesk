# MokTradeDesk — Fixes Log

Track of all fixes applied from DASHBOARD_DATA_CONTRACT_AUDIT.md.

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