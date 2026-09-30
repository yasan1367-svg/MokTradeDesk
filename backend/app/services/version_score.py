"""فاز 48a — Score ساده برای رتبه‌بندی Versionها.

فاکتورها:
- Win Rate       (۳۵٪)
- Profit Factor  (۳۵٪)
- Net PnL        (۳۰٪)
- Max DD         (جریمه ۲۰٪)

خروجی: عددی بین ۰ تا ۱۰۰ (بالاتر = بهتر).
"""
from __future__ import annotations

from typing import Any, Mapping


def calculate_version_score(metrics: Mapping[str, Any]) -> float:
    """امتیاز سادهٔ یک نسخه از روی متریک‌هایش (۰..۱۰۰).

    ورودی یک دیکشنری متریک است (معمولاً خروجی `_extract_metrics`):
        win_rate, profit_factor, net_pnl, max_dd
    """
    win = metrics.get("win_rate", 0) or 0
    pf = metrics.get("profit_factor", 0) or 0
    pnl = metrics.get("net_pnl", 0) or 0
    dd = metrics.get("max_dd", 0) or 0

    win_score = min(win, 100)
    pf_score = min(pf * 20, 100)
    pnl_score = min(max(pnl / 10, 0), 100)
    dd_penalty = min(dd / 10, 50)

    score = (
        win_score * 0.35
        + pf_score * 0.35
        + pnl_score * 0.30
    ) - (dd_penalty * 0.20)

    return max(0, round(min(score, 100), 2))
