"""Facade coordinating the risk-domain calculations for a trade scope."""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from ...models.strategy import TestType, Trade
from .drawdown_engine import (
    calculate_drawdown_duration,
    calculate_peak_to_trough_dd,
    calculate_static_dd,
)
from .equity_engine import calculate_equity_curve
from .instrument_spec import InstrumentSpec
from .position_sizing import calculate_position_size
from .r_engine import calculate_expectancy_r, calculate_r_distribution


class RiskEngine:
    """Single entry point for scope-aware risk calculations."""

    DEFAULT_INITIAL_BALANCE = 10000.0
    VALID_SCOPES = {"real", "backtest", "forward", "all"}

    @staticmethod
    def calculate_risk_metrics(
        db: Session,
        scope: str,
        initial_balance: float | None = None,
        symbol: str | None = None,
        risk_percent: float = 1.0,
    ) -> dict:
        """Load scoped trades and return position sizing and portfolio risk metrics."""
        normalized_scope = (scope or "").strip().lower()
        if normalized_scope not in RiskEngine.VALID_SCOPES:
            raise ValueError(f"Invalid scope: {scope!r}")

        trades = RiskEngine._load_trades(db, normalized_scope, symbol)
        spec = RiskEngine._get_instrument_spec(db, symbol) if symbol else None
        if initial_balance is None:
            initial_balance = RiskEngine.DEFAULT_INITIAL_BALANCE

        equity_curve = calculate_equity_curve(initial_balance, trades)
        static_dd = calculate_static_dd(initial_balance, equity_curve)
        peak_to_trough_dd = calculate_peak_to_trough_dd(equity_curve)
        drawdown_duration = calculate_drawdown_duration(equity_curve)

        closed_trades = [trade for trade in trades if trade.close_time is not None]
        r_multiples = [trade.r_multiple for trade in closed_trades]
        expectancy_r = calculate_expectancy_r(r_multiples)
        r_distribution = calculate_r_distribution(r_multiples)

        position_sizing = None
        if spec is not None:
            sizing_trade = next(
                (
                    trade
                    for trade in reversed(trades)
                    if trade.sl is not None and trade.open_price is not None
                ),
                None,
            )
            if sizing_trade is not None:
                sl_distance = float(
                    abs(Decimal(str(sizing_trade.open_price)) - Decimal(str(sizing_trade.sl)))
                )
                if spec.tick_size > 0:
                    value_per_price_unit = spec.tick_value / spec.tick_size
                    position_sizing = calculate_position_size(
                        account_equity=initial_balance,
                        risk_percent=risk_percent,
                        sl_distance=sl_distance,
                        value_per_price_unit=value_per_price_unit,
                        commission_one_side=spec.commission_one_side,
                        min_lot=spec.min_lot,
                        max_lot=spec.max_lot,
                        lot_step=spec.lot_step,
                    )

        daily_returns = RiskEngine._daily_returns(equity_curve, initial_balance)
        return {
            "position_sizing": position_sizing,
            "expectancy_r": expectancy_r,
            "r_distribution": r_distribution,
            "equity_curve": equity_curve,
            "static_dd": static_dd,
            "peak_to_trough_dd": peak_to_trough_dd,
            "drawdown_duration": drawdown_duration,
            "sharpe": RiskEngine._sharpe(daily_returns),
            "sortino": RiskEngine._sortino(daily_returns),
            "initial_balance": initial_balance,
        }

    @staticmethod
    def _load_trades(db: Session, scope: str, symbol: str | None) -> list[Trade]:
        query = db.query(Trade).filter(Trade.is_deleted.is_(False))
        if scope == "real":
            query = query.filter(Trade.test_type.in_([TestType.REAL_PERSONAL, TestType.REAL_PROP]))
        elif scope == "backtest":
            query = query.filter(Trade.test_type == TestType.BACKTEST)
        elif scope == "forward":
            query = query.filter(Trade.test_type == TestType.FORWARD)

        if symbol:
            query = query.filter(Trade.symbol == symbol.strip().upper())

        return query.order_by(Trade.open_time.asc(), Trade.id.asc()).all()

    @staticmethod
    def _get_instrument_spec(db: Session, symbol: str) -> InstrumentSpec | None:
        return (
            db.query(InstrumentSpec)
            .filter(InstrumentSpec.canonical_symbol == symbol.strip().upper())
            .first()
        )

    @staticmethod
    def _daily_returns(equity_curve: list[dict], initial: float) -> list[float]:
        """Aggregate closed-trade net PnL by date and divide by that day's opening equity."""
        daily_pnl = defaultdict(float)
        for point in equity_curve:
            date = point.get("date")
            if date is not None:
                daily_pnl[date.date()] += float(point.get("pnl", 0.0) or 0.0)

        balance = initial
        returns = []
        for day in sorted(daily_pnl):
            net = daily_pnl[day]
            returns.append(net / balance if balance else 0.0)
            balance += net
        return returns

    @staticmethod
    def _daily_returns_from_trades(trades: list, initial_balance: float) -> list[float]:
        """Aggregate trade net PnL by close date and return each day's opening-equity return.

        Accepts either trade ORM/data objects (``close_time`` and ``pnl`` fields) or
        analytics projections (``close_time`` and ``net`` mapping keys).
        """
        daily_pnl = defaultdict(float)
        for trade in trades:
            close_time = (
                trade.get("close_time") if isinstance(trade, dict)
                else getattr(trade, "close_time", None)
            )
            if close_time is None:
                continue
            net = (
                trade.get("net", trade.get("pnl", 0.0)) if isinstance(trade, dict)
                else getattr(trade, "net", getattr(trade, "pnl", 0.0))
            )
            daily_pnl[close_time.date()] += float(net or 0.0)

        balance = float(initial_balance)
        daily_returns = []
        for day in sorted(daily_pnl):
            net = daily_pnl[day]
            daily_returns.append(net / balance if balance else 0.0)
            balance += net
        return daily_returns

    @staticmethod
    def _sharpe(returns: list[float]) -> float:
        """Population Sharpe ratio over daily returns, without annualization."""
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((value - mean) ** 2 for value in returns) / len(returns)
        std_dev = variance**0.5
        return mean / std_dev if std_dev else 0.0

    @staticmethod
    def _sortino(returns: list[float]) -> float:
        """Sortino ratio over daily returns, without annualization."""
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        negative_returns = [value for value in returns if value < 0]
        if not negative_returns:
            return 0.0
        downside_deviation = (
            sum(value**2 for value in negative_returns) / len(returns)
        ) ** 0.5
        return mean / downside_deviation if downside_deviation else 0.0