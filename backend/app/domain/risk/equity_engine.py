"""Balance and equity-curve calculations from realized and floating trade PnL."""

from ...services.metrics import net_pnl


def calculate_equity_curve(
    initial_balance: float,
    trades: list,
) -> list[dict]:
    """Build a realized balance/equity curve from closed trades."""
    balance = initial_balance
    curve = [{"date": None, "balance": balance, "equity": balance, "pnl": 0}]

    closed_trades = (
        trade
        for trade in trades
        if getattr(trade, "close_time", None) is not None
    )
    for trade in sorted(closed_trades, key=lambda item: item.close_time):
        net = net_pnl(trade)
        balance += net
        curve.append(
            {
                "date": trade.close_time,
                "balance": balance,
                "equity": balance,
                "pnl": net,
            }
        )

    return curve


def calculate_equity_with_floating(
    initial_balance: float,
    closed_trades: list,
    open_trades: list,
) -> list[dict]:
    """Return the realized curve with current open-trade PnL on final equity.

    Balance remains realized (initial balance plus closed-trade net PnL). The last
    curve point's equity includes the aggregate floating net PnL of open trades;
    ``floating_pnl`` is included there for clarity.
    """
    curve = calculate_equity_curve(initial_balance, closed_trades)
    floating_pnl = sum(net_pnl(trade) for trade in open_trades)
    curve[-1] = {
        **curve[-1],
        "equity": curve[-1]["balance"] + floating_pnl,
        "floating_pnl": floating_pnl,
    }
    return curve