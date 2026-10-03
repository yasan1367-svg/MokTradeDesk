"""تست‌های فاز ۵۳.۲ — Sharpe/Sortino (بدون سالانه‌سازی) + مبنای سرمایهٔ scope.

باگ #۴: Sharpe/Sortino روی سود دلاری هر معامله با ضریب √252 محاسبه می‌شد
(ضریب دادهٔ روزانه) ⇒ نسبت گمراه‌کننده.
باگ #۵: `avg_b` از همهٔ حساب‌ها گرفته می‌شد، بی‌توجه به scope.

هر دو endpoint (`/risk-metrics` و `/risk-advanced`) پوشش داده شده‌اند.
"""
from datetime import datetime, timezone

from app.models.finance import Currency
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.models.trading import Broker, PersonalTradingAccount


def _version(db):
    s = Strategy(name="S53r")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name="v53r")
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _pta(db, label="R53", balance=10000.0):
    b = Broker(name=f"B-{label}")
    db.add(b)
    db.flush()
    a = PersonalTradingAccount(
        broker_id=b.id, account_number=f"ACC-{label}", account_label=label,
        currency=Currency.USDT, initial_balance=balance, current_balance=balance,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _trade(db, version_id, pnl, *, day, pta_id=None, test_type=TestType.REAL_PERSONAL):
    t = Trade(
        version_id=version_id,
        personal_trading_account_id=pta_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 7, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 7, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=test_type,
    )
    db.add(t)
    return t


def _seed_daily(db):
    """۳ معامله در ۳ روزِ متفاوت با pnlهای 100 / -100 / 300 (بازده روزانه)."""
    v = _version(db)
    pta = _pta(db)
    for day, pnl in [(1, 100.0), (2, -100.0), (3, 300.0)]:
        _trade(db, v.id, pnl, day=day, pta_id=pta.id)
    db.commit()
    return v, pta


# مقادیر مرجع دستی برای سری روزانهٔ [100, -100, 300]
_DAILY = [100.0, -100.0, 300.0]
_MEAN = sum(_DAILY) / len(_DAILY)                                 # 100.0
_STD = (sum((x - _MEAN) ** 2 for x in _DAILY) / len(_DAILY)) ** 0.5
_DDEV = (sum(x ** 2 for x in _DAILY if x < 0) / len(_DAILY)) ** 0.5


def test_sharpe_no_annualization(client, db_session):
    """Sharpe = mean/std بازده روزانه، **بدون** √252 — در هر دو endpoint."""
    _seed_daily(db_session)
    expected = round(_MEAN / _STD, 2)

    rm = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    sharpe_rm = rm["performance_ratios"]["sharpe_ratio"]
    assert abs(sharpe_rm - expected) < 0.011
    assert sharpe_rm < 5   # اگر سالانه‌سازی می‌بود ≈ mean/std*√252 ≈ 9.7

    ra = client.get(
        "/api/analytics/risk-advanced", params={"scope": "real", "currency": "USDT"}
    ).json()
    assert abs(ra["sharpe_ratio"] - round(_MEAN / _STD, 3)) < 0.011
    assert ra["sharpe_ratio"] < 5


def test_sortino_no_annualization(client, db_session):
    """Sortino = mean/downside-deviation بازده روزانه، **بدون** √252 — هر دو endpoint."""
    _seed_daily(db_session)
    expected = round(_MEAN / _DDEV, 2)

    rm = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    sortino_rm = rm["performance_ratios"]["sortino_ratio"]
    assert abs(sortino_rm - expected) < 0.011
    assert sortino_rm < 5   # با √252 می‌شد ≈ 27.5

    ra = client.get(
        "/api/analytics/risk-advanced", params={"scope": "real", "currency": "USDT"}
    ).json()
    assert abs(ra["sortino_ratio"] - round(_MEAN / _DDEV, 3)) < 0.011
    assert ra["sortino_ratio"] < 5


def test_risk_metrics_uses_scope(client, db_session):
    """scope=real ⇒ فقط حساب‌های ارجاع‌شده در سرمایه (نه همهٔ حساب‌ها)."""
    v = _version(db_session)
    used = _pta(db_session, label="used", balance=20000.0)
    _pta(db_session, label="unused", balance=1000.0)   # بدون معامله ⇒ نباید شمرده شود
    for day, pnl in [(1, 100.0), (2, -100.0), (3, 300.0)]:
        _trade(db_session, v.id, pnl, day=day, pta_id=used.id)
    db_session.commit()

    body = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    # توازن scope همچنان در محاسبات ریسک استفاده می‌شود، اما دیگر به‌عنوان sizing افشا نمی‌شود.
    assert "position_sizing" not in body
    assert "suggested_lots" not in str(body)
    assert "risk_of_ruin" in body["risk_metrics"]
    assert "open_risk_percent" in body["risk_metrics"]


def test_risk_metrics_backtest_assumed_balance(client, db_session):
    """scope=backtest/forward ⇒ سرمایهٔ فرضی ۱۰۰۰۰ (حساب واقعی ندارد)."""
    v = _version(db_session)
    _pta(db_session, label="exists", balance=20000.0)   # حساب موجود ولی نامرتبط
    for day, pnl in [(1, 100.0), (2, -100.0), (3, 300.0)]:
        _trade(db_session, v.id, pnl, day=day, pta_id=None, test_type=TestType.BACKTEST)
    db_session.commit()

    body = client.get("/api/analytics/risk-metrics", params={"scope": "backtest"}).json()
    assert "position_sizing" not in body
    assert "suggested_lots" not in str(body)
    assert "risk_of_ruin" in body["risk_metrics"]
