"""فاز ۴۳ — یک تعریف واحد برای متریک‌ها.

قرارداد:
- net_pnl = pnl + commission + swap (همه‌جا)
- equity_curve با initial
- max_drawdown از equity
- streaks از net
- profit_factor از gross_profit/gross_loss

⚠️ هیچ‌جای دیگری نباید «pnl + commission + swap» را دوباره پیاده کند؛
همهٔ سرویس‌ها (PropRuleEngine / AnalysisService / analytics / finance / export /
chart_helpers) باید از همین ماژول استفاده کنند.
"""

from typing import Any, Dict, List

from sqlalchemy import func

from ..models.strategy import Trade


def net_pnl(trade) -> float:
    """PnL خالص: pnl + commission + swap"""
    return (trade.pnl or 0) + (trade.commission or 0) + (trade.swap or 0)


def net_pnl_sql():
    """net_pnl برای کوئری SQL (برای aggregation در DB)."""
    return (
        func.coalesce(Trade.pnl, 0)
        + func.coalesce(Trade.commission, 0)
        + func.coalesce(Trade.swap, 0)
    )


def equity_curve(nets: List[float], initial: float = 0) -> List[float]:
    """منحنی Equity از لیست net_pnl"""
    result = [initial]
    for n in nets:
        result.append(result[-1] + n)
    return result


def max_drawdown(equity: List[float]) -> float:
    """حداکثر افت از peak"""
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for value in equity:
        if value > peak:
            peak = value
        dd = peak - value
        if dd > max_dd:
            max_dd = dd
    return max_dd


def streaks(nets: List[float]) -> Dict[str, Any]:
    """بردها و باخت‌های متوالی"""
    if not nets:
        return {"max_wins": 0, "max_losses": 0, "current_win_streak": 0, "current_loss_streak": 0}

    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0

    for n in nets:
        if n > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif n < 0:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)

    return {
        "max_wins": max_wins,
        "max_losses": max_losses,
        "current_win_streak": current_wins,
        "current_loss_streak": current_losses,
    }


def profit_factor(nets: List[float]) -> float:
    """PF = gross_profit / gross_loss"""
    gross_profit = sum(n for n in nets if n > 0)
    gross_loss = abs(sum(n for n in nets if n < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def calculate_basic_metrics(trades: List) -> Dict[str, Any]:
    """متریک‌های پایه از لیست Trade"""
    nets = [net_pnl(t) for t in trades]
    wins = [n for n in nets if n > 0]
    losses = [n for n in nets if n < 0]

    total = len(nets)
    win_rate = (len(wins) / total * 100) if total > 0 else 0

    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 2),
        "net_pnl": round(sum(nets), 2),
        "gross_profit": round(sum(wins), 2),
        "gross_loss": round(abs(sum(losses)), 2),
        "profit_factor": round(profit_factor(nets), 2),
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
        "largest_win": round(max(wins), 2) if wins else 0,
        "largest_loss": round(min(losses), 2) if losses else 0,
    }


def calculate_max_drawdown(trades: List, initial: float = 0) -> float:
    """حداکثر افت از لیست Trade"""
    nets = [net_pnl(t) for t in trades]
    equity = equity_curve(nets, initial)
    return max_drawdown(equity)
