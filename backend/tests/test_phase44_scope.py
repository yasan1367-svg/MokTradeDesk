"""تست‌های فاز ۴۴.۱ — دامنهٔ معاملات (scope) روی داشبورد/ریسک/تقویم/دیروز.

پیش‌فرض `scope=real` است (REAL_PERSONAL + REAL_PROP) تا بک‌تست با نتایج واقعی
قاطی نشود.
"""
from datetime import datetime, timezone

from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource


def _trade(version_id, pnl, *, day, test_type, prop_stage_id=None):
    return Trade(
        version_id=version_id,
        prop_stage_id=prop_stage_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 6, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 6, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2000.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=test_type,
    )


def _seed(db):
    """۳ معاملهٔ BACKTEST (مجموع ۶۰۰) + ۲ معاملهٔ REAL_PROP (مجموع ۱۵۰۰)."""
    strategy = Strategy(name="S44")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v44")
    db.add(version)
    db.flush()

    firm = PropFirm(name="F44")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="A44")
    db.add(account)
    db.flush()
    stage = PropStage(
        prop_account_id=account.id,
        stage_type=StageType.FUNDED_REAL,
        status=StageStatus.ACTIVE,
        initial_balance=10000.0,
    )
    db.add(stage)
    db.flush()

    for i, pnl in enumerate([100.0, 200.0, 300.0], start=1):
        db.add(_trade(version.id, pnl, day=i, test_type=TestType.BACKTEST))
    for i, pnl in enumerate([1000.0, 500.0], start=11):
        db.add(_trade(version.id, pnl, day=i, test_type=TestType.REAL_PROP, prop_stage_id=stage.id))
    db.commit()
    return version, stage


def test_dashboard_real_scope_excludes_backtest(client, db_session):
    _seed(db_session)
    body = client.get("/api/analytics/dashboard", params={"scope": "real"}).json()
    # فقط ۲ معاملهٔ واقعی — ۳ بک‌تست نادیده
    assert body["summary"]["total_trades"] == 2
    assert body["summary"]["net_pnl"] == 1500.0


def test_dashboard_default_is_real(client, db_session):
    _seed(db_session)
    body = client.get("/api/analytics/dashboard").json()
    assert body["summary"]["total_trades"] == 2
    assert body["summary"]["net_pnl"] == 1500.0


def test_dashboard_backtest_scope(client, db_session):
    _seed(db_session)
    body = client.get("/api/analytics/dashboard", params={"scope": "backtest"}).json()
    assert body["summary"]["total_trades"] == 3
    assert body["summary"]["net_pnl"] == 600.0


def test_historical_summary_excludes_open_trades(client, db_session):
    strategy = Strategy(name="HistoricalClosedOnly")
    db_session.add(strategy)
    db_session.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db_session.add(version)
    db_session.flush()

    closed_trade = _trade(version.id, 100.0, day=10, test_type=TestType.BACKTEST)
    open_trade = _trade(version.id, 1000.0, day=10, test_type=TestType.BACKTEST)
    open_trade.close_time = None
    open_trade.close_price = None
    db_session.add_all([closed_trade, open_trade])
    db_session.commit()

    # No date must still exclude stored open PnL from historical aggregates.
    for bounds, expected_net, expected_count in [
        ({}, 100.0, 1),
        ({"date_from": "2025-06-10"}, 100.0, 1),
        ({"date_to": "2025-06-10"}, 100.0, 1),
        ({"date_from": "2025-06-11"}, 0.0, 0),
        ({"date_to": "2025-06-09"}, 0.0, 0),
    ]:
        response = client.get(
            "/api/analytics/dashboard", params={"scope": "backtest", **bounds}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        summary = body["summary"]
        assert summary["net_pnl"] == expected_net, bounds
        assert summary["total_trades"] == expected_count, bounds
        assert summary["closed_trades"] == expected_count, bounds
        assert summary["open_trades"] == 1, bounds
        curve = body["equity_curve"]
        assert curve[-1]["equity"] - curve[0]["equity"] == expected_net, bounds


def test_dashboard_all_scope(client, db_session):
    _seed(db_session)
    body = client.get("/api/analytics/dashboard", params={"scope": "all"}).json()
    assert body["summary"]["total_trades"] == 5
    assert body["summary"]["net_pnl"] == 2100.0


def test_risk_metrics_with_scope(client, db_session):
    _seed(db_session)
    real = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    back = client.get("/api/analytics/risk-metrics", params={"scope": "backtest"}).json()
    alll = client.get("/api/analytics/risk-metrics", params={"scope": "all"}).json()
    assert real["risk_metrics"]["total_trades"] == 2
    assert back["risk_metrics"]["total_trades"] == 3
    assert alll["risk_metrics"]["total_trades"] == 5


def test_calendar_scope(client, db_session):
    _seed(db_session)
    real = client.get("/api/analytics/calendar", params={"scope": "real"}).json()
    assert sum(d["trade_count"] for d in real) == 2
    alll = client.get("/api/analytics/calendar", params={"scope": "all"}).json()
    assert sum(d["trade_count"] for d in alll) == 5


def test_yesterday_scope_accepts_param(client, db_session):
    _seed(db_session)
    r = client.get("/api/analytics/yesterday", params={"scope": "backtest"})
    assert r.status_code == 200


def test_invalid_scope_rejected(client, db_session):
    assert client.get("/api/analytics/dashboard", params={"scope": "nonsense"}).status_code == 400
