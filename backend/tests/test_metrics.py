"""تست‌های مستقل فاز ۴۳ — سرویس متریک واحد (`app.services.metrics`)."""
from types import SimpleNamespace

import pytest

from app.services import metrics


def _t(pnl=None, commission=None, swap=None):
    return SimpleNamespace(pnl=pnl, commission=commission, swap=swap)


# ═════════════════════════════════════════════
# net_pnl
# ═════════════════════════════════════════════
def test_net_pnl_basic():
    assert metrics.net_pnl(_t(pnl=100, commission=-10, swap=-5)) == 85.0


def test_net_pnl_none_values():
    assert metrics.net_pnl(_t()) == 0.0
    assert metrics.net_pnl(_t(pnl=50)) == 50.0
    assert metrics.net_pnl(_t(commission=-3)) == -3.0


def test_net_pnl_sql_matches_python():
    """عبارت SQL باید همان net_pnl پایتون را بسازد (روی DB درون‌حافظه)."""
    from datetime import datetime, timezone

    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base
    from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource

    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        strategy = Strategy(name="S")
        db.add(strategy)
        db.flush()
        version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
        db.add(version)
        db.flush()
        db.add(Trade(
            version_id=version.id,
            symbol="XAUUSD",
            direction="buy",
            open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            open_price=2000.0,
            size=1.0,
            pnl=100.0,
            commission=-10.0,
            swap=-5.0,
            source=TradeSource.MANUAL,
            test_type=TestType.BACKTEST,
        ))
        db.commit()

        sql_val = float(
            db.execute(select(func.coalesce(func.sum(metrics.net_pnl_sql()), 0.0))).scalar()
        )
        assert sql_val == pytest.approx(85.0)
    finally:
        db.close()



# ═════════════════════════════════════════════
# equity / drawdown
# ═════════════════════════════════════════════
def test_equity_curve():
    assert metrics.equity_curve([100, -50, 30], initial=0) == [0, 100, 50, 80]
    assert metrics.equity_curve([10], initial=1000) == [1000, 1010]


def test_max_drawdown():
    # peak 100 → trough 50 ⇒ dd = 50
    assert metrics.max_drawdown([0, 100, 50, 80]) == 50.0
    assert metrics.max_drawdown([]) == 0.0
    assert metrics.max_drawdown([1, 2, 3]) == 0.0


# ═════════════════════════════════════════════
# streaks / profit factor
# ═════════════════════════════════════════════
def test_streaks():
    res = metrics.streaks([10, 20, -5, -5, -5, 3])
    assert res["max_wins"] == 2
    assert res["max_losses"] == 3
    assert res["current_win_streak"] == 1
    assert res["current_loss_streak"] == 0


def test_streaks_empty():
    assert metrics.streaks([]) == {
        "max_wins": 0, "max_losses": 0,
        "current_win_streak": 0, "current_loss_streak": 0,
    }


@pytest.mark.parametrize("nets,expected", [
    ([1, 0, 1], (1, 0, 1, 0)),
    ([-1, 0, -1], (0, 1, 0, 1)),
    ([1, 1, 0], (2, 0, 0, 0)),
    ([-1, -1, 0], (0, 2, 0, 0)),
    ([0, 0], (0, 0, 0, 0)),
])
def test_both_streak_helpers_reset_on_breakeven(nets, expected):
    wins, losses, current_wins, current_losses = expected
    assert metrics.streaks(nets) == {
        "max_wins": wins, "max_losses": losses,
        "current_win_streak": current_wins, "current_loss_streak": current_losses,
    }
    assert metrics.win_loss_streaks(nets) == (wins, losses)


def test_profit_factor():
    assert metrics.profit_factor([100, -50, 50]) == pytest.approx(3.0)


@pytest.mark.parametrize("profit, loss, value, status", [
    (0, 0, None, "undefined"),
    (100, 0, None, "no_losses"),
    (0, 50, 0.0, "finite"),
    (150, 50, 3.0, "finite"),
    (150, -50, 3.0, "finite"),
    (1000, 1, 1000.0, "finite"),
    (999, 1, 999.0, "finite"),
])
def test_profit_factor_status(profit, loss, value, status):
    assert metrics.profit_factor_status(profit, loss) == {"value": value, "status": status}


def test_profit_factor_no_loss():
    assert metrics.profit_factor([10, 20]) == 999.0
    assert metrics.profit_factor([-10]) == 0.0


# ═════════════════════════════════════════════
# aggregate helpers
# ═════════════════════════════════════════════
def test_calculate_basic_metrics():
    trades = [_t(pnl=100), _t(pnl=-50), _t(pnl=50)]
    m = metrics.calculate_basic_metrics(trades)
    assert m["total_trades"] == 3
    assert m["wins"] == 2
    assert m["losses"] == 1
    assert m["win_rate"] == pytest.approx(66.67, abs=0.01)
    assert m["net_pnl"] == pytest.approx(100.0)
    assert m["profit_factor"] == pytest.approx(3.0)
    assert m["largest_win"] == pytest.approx(100.0)
    # طبق قرارداد این تابع (مطابق پلن فاز ۴۳) largest_loss مقدار min خام/منفی است.
    assert m["largest_loss"] == pytest.approx(-50.0)


def test_calculate_basic_metrics_uses_commission():
    m = metrics.calculate_basic_metrics([_t(pnl=100, commission=-10, swap=-5)])
    assert m["net_pnl"] == pytest.approx(85.0)


def test_calculate_max_drawdown():
    trades = [_t(pnl=500), _t(pnl=-800), _t(pnl=200)]
    assert metrics.calculate_max_drawdown(trades, initial=10000) == pytest.approx(800.0)


def test_empty_trades():
    m = metrics.calculate_basic_metrics([])
    assert m["total_trades"] == 0
    assert m["net_pnl"] == 0
    assert m["win_rate"] == 0
    assert metrics.calculate_max_drawdown([]) == 0.0
