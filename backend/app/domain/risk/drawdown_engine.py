"""Static, peak-to-trough, and elapsed-time drawdown calculations."""


def calculate_drawdown_curve(equity_curve: list[dict]) -> list[dict]:
    """Return point-wise peak-to-trough drawdown values for an equity curve."""
    peak = equity_curve[0]["equity"] if equity_curve else 0.0
    result = []
    for point in equity_curve:
        equity = point["equity"]
        if equity > peak:
            peak = equity
        drawdown = max(0.0, peak - equity)
        result.append(
            {
                "date": point.get("date"),
                "drawdown": drawdown,
                "drawdown_pct": (drawdown / peak * 100) if peak else 0.0,
            }
        )
    return result


def calculate_static_dd(
    initial_balance: float,
    equity_curve: list[dict],
) -> dict:
    """Calculate maximum drawdown from initial balance, not from a running peak."""
    equities = [point["equity"] for point in equity_curve]
    min_equity = min(equities) if equities else initial_balance
    dd = max(0.0, initial_balance - min_equity)
    dd_percent = (dd / initial_balance * 100) if initial_balance else 0.0
    return {"dd": dd, "dd_percent": dd_percent, "min_equity": min_equity}


def calculate_peak_to_trough_dd(equity_curve: list[dict]) -> dict:
    """Calculate the deepest drawdown from any preceding equity peak."""
    if not equity_curve:
        return {"dd": 0.0, "dd_percent": 0.0, "peak": 0.0}

    peak = equity_curve[0]["equity"]
    max_dd = 0.0
    max_dd_percent = 0.0
    for point in equity_curve:
        equity = point["equity"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        dd_percent = (dd / peak * 100) if peak else 0.0
        if dd > max_dd:
            max_dd = dd
            max_dd_percent = dd_percent
    return {"dd": max_dd, "dd_percent": max_dd_percent, "peak": peak}


def calculate_drawdown_duration(equity_curve: list[dict]) -> dict:
    """Return the longest drawdown period as elapsed 24-hour days.

    A period starts at the first dated point below its preceding peak and ends
    when equity recovers to or above that peak. An unrecovered period ends at
    the final dated point. The initial equity point may have ``date=None``; in
    that case duration starts at the first dated point below the initial peak.
    """
    if not equity_curve:
        return {"duration_days": 0.0, "start_date": None, "end_date": None}

    peak = equity_curve[0]["equity"]
    underwater_start = None
    longest_days = 0.0
    longest_start = None
    longest_end = None

    for point in equity_curve:
        equity = point["equity"]
        date = point.get("date")
        if equity > peak:
            peak = equity

        if equity < peak:
            if underwater_start is None and date is not None:
                underwater_start = date
            continue

        if underwater_start is not None and date is not None:
            duration_days = max(0.0, (date - underwater_start).total_seconds() / 86400)
            if duration_days > longest_days:
                longest_days = duration_days
                longest_start = underwater_start
                longest_end = date
        underwater_start = None

    if underwater_start is not None:
        last_date = next(
            (point.get("date") for point in reversed(equity_curve) if point.get("date") is not None),
            None,
        )
        if last_date is not None:
            duration_days = max(0.0, (last_date - underwater_start).total_seconds() / 86400)
            if duration_days > longest_days:
                longest_days = duration_days
                longest_start = underwater_start
                longest_end = last_date

    return {
        "duration_days": longest_days,
        "start_date": longest_start,
        "end_date": longest_end,
    }