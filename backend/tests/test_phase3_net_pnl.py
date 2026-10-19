"""فاز ۳ — تست‌های net_pnl (Trade model properties + aggregation)."""
from datetime import datetime, timezone
import pytest
from app.models.strategy import Trade, TradeSource, TestType
from app.services import metrics


def _mk_trade(db_session, *, pnl=0.0, commission=0.0, swap=0.0,
              version_id=None, close_time=None):
    """ساخت سریع یک Trade برای تست (فقط فیلدهای مالی)."""
    if version_id is None:
        from tests.test_import_engine import _version
        version_id = _version(db_session).id
    t = Trade(
        version_id=version_id,
        symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, 1, 10, tzinfo=timezone.utc),
        close_time=close_time or datetime(2025, 1, 1, 12, tzinfo=timezone.utc),
        open_price=2000, close_price=2010, size=1,
        pnl=pnl, commission=commission, swap=swap,
        source=TradeSource.MANUAL, test_type=TestType.BACKTEST,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


# ═════════════════════════════════════════════
# فرمول پایه
# ═════════════════════════════════════════════
def test_net_pnl_formula():
    """net_pnl == pnl + commission + swap دقیقا."""
    t = Trade(pnl=10.0, commission=-2.0, swap=-0.5)
    assert t.net_pnl == 10.0 + (-2.0) + (-0.5) == 7.5


def test_net_pnl_none_coalesces_to_zero():
    """اگه pnl/commission/swap None باشه، صفر فرض می‌شه."""
    t = Trade(pnl=None, commission=None, swap=None)
    assert t.net_pnl == 0.0

    t2 = Trade(pnl=5.0, commission=None, swap=None)
    assert t2.net_pnl == 5.0


# ═════════════════════════════════════════════
# is_win / is_loss / is_breakeven
# ═════════════════════════════════════════════
def test_is_win_gross_profit_minus_commission_still_loses():
    """Trade با pnl=+0.5, commission=-2, swap=0 ⇒ is_win == False (چون net منفی است)."""
    t = Trade(pnl=0.5, commission=-2.0, swap=0.0)
    assert not t.is_win
    assert t.is_loss
    assert not t.is_breakeven


def test_is_win_gross_loss_plus_commission_still_wins():
    """Trade با pnl=-1, commission=+3, swap=0 ⇒ is_win == True (چون net مثبت است)."""
    t = Trade(pnl=-1.0, commission=3.0, swap=0.0)
    assert t.is_win
    assert not t.is_loss
    assert not t.is_breakeven


def test_is_breakeven_exact_zero():
    """Trade با pnl=+1, commission=-1, swap=0 ⇒ is_breakeven == True (چون net=0)."""
    t = Trade(pnl=1.0, commission=-1.0, swap=0.0)
    assert t.is_breakeven
    assert not t.is_win
    assert not t.is_loss


def test_is_win_true_when_commission_adds():
    """Trade با pnl=0, commission=+0.5, swap=0 ⇒ is_win == True."""
    t = Trade(pnl=0.0, commission=0.5, swap=0.0)
    assert t.is_win
    assert not t.is_loss
    assert not t.is_breakeven


def test_is_loss_true_when_commission_dominates():
    """Trade با pnl=0, commission=-0.5, swap=0 ⇒ is_loss == True."""
    t = Trade(pnl=0.0, commission=-0.5, swap=0.0)
    assert t.is_loss
    assert not t.is_win
    assert not t.is_breakeven


# ═════════════════════════════════════════════
# Aggregation via metrics.net_pnl
# ═════════════════════════════════════════════
def test_metrics_net_pnl_matches_model_property(db_session):
    """metrics.net_pnl(t) == t.net_pnl (هر دو از یک فرمول)."""
    t = _mk_trade(db_session, pnl=10.0, commission=-2.5, swap=-0.5)
    assert metrics.net_pnl(t) == t.net_pnl == 7.0


def test_net_pnl_not_raw_pnl(db_session):
    """مجموع net_pnl != مجموع pnl خام وقتی commission/swap غیرصفر است."""
    t1 = _mk_trade(db_session, pnl=10.0, commission=-2.0, swap=0.0)
    t2 = _mk_trade(db_session, pnl=-5.0, commission=-1.0, swap=-0.5,
                   version_id=t1.version_id)
    all_trades = [t1, t2]
    raw_sum = sum(t.pnl for t in all_trades)
    net_sum = sum(metrics.net_pnl(t) for t in all_trades)
    assert raw_sum == 5.0            # 10 + (-5)
    assert net_sum == 1.5            # 8 + (-6.5) = 1.5
    assert net_sum != raw_sum        # این اصل تست است


def test_calculate_basic_metrics_uses_net_pnl(db_session):
    """metrics.calculate_basic_metrics از net_pnl استفاده می‌کند."""
    t1 = _mk_trade(db_session, pnl=10.0, commission=-2.0, swap=0.0)    # net = 8
    t2 = _mk_trade(db_session, pnl=-5.0, commission=-1.0, swap=-0.5,   # net = -6.5
                   version_id=t1.version_id)
    result = metrics.calculate_basic_metrics([t1, t2])
    assert result["net_pnl"] == 1.5       # 8 + (-6.5)
    assert result["wins"] == 1
    assert result["losses"] == 1