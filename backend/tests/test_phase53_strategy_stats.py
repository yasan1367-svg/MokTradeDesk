"""تست‌های فاز ۵۳.۳.۲ — آمار استراتژی مادر: تجمیعی (برچسب‌دار) + per-version.

باگ: `GET /api/strategies/{id}/stats` معاملات همهٔ نسخه‌ها را با هم جمع می‌کرد
بدون اینکه مشخص کند «تجمیعی» است یا آمار هر نسخه را جدا بدهد.
"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource


def _version(db, strategy, name):
    v = StrategyVersion(strategy_id=strategy.id, version_name=name)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _trade(db, version_id, pnl, day):
    db.add(Trade(
        version_id=version_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 8, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 8, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=TestType.BACKTEST,
    ))


def _seed(db):
    """استراتژی با ۲ نسخه: v1 = +100,+200 ; v2 = −50."""
    s = Strategy(name="S53-stats")
    db.add(s)
    db.commit()
    db.refresh(s)
    v1 = _version(db, s, "v1")
    v2 = _version(db, s, "v2")
    _trade(db, v1.id, 100.0, 1)
    _trade(db, v1.id, 200.0, 2)
    _trade(db, v2.id, -50.0, 3)
    db.commit()
    return s, v1, v2


def test_strategy_stats_aggregate_labeled(client, db_session):
    """آمار سطح-بالا باید تجمیعی و برچسب‌دار (scope=aggregate) باشد."""
    s, _v1, _v2 = _seed(db_session)

    body = client.get(f"/api/strategies/{s.id}/stats").json()
    assert body["scope"] == "aggregate_historical_summary"
    assert body["performance_scope"].endswith("not_portfolio")
    assert body["aggregate_label"]
    assert body["total_trades"] == 3
    assert body["summary"]["net_pnl"] == 250.0          # 100 + 200 - 50
    assert body["trade_counts"]["winning"] == 2
    assert body["trade_counts"]["losing"] == 1


def test_strategy_stats_per_version(client, db_session):
    """آمار هر نسخه باید جداگانه و درست باشد."""
    s, v1, v2 = _seed(db_session)

    body = client.get(f"/api/strategies/{s.id}/stats").json()
    per = {item["version_id"]: item for item in body["per_version"]}
    assert set(per) == {v1.id, v2.id}

    assert per[v1.id]["version_name"] == "v1"
    assert per[v1.id]["total_trades"] == 2
    assert per[v1.id]["summary"]["net_pnl"] == 300.0
    assert per[v1.id]["trade_counts"]["winning"] == 2

    assert per[v2.id]["version_name"] == "v2"
    assert per[v2.id]["total_trades"] == 1
    assert per[v2.id]["summary"]["net_pnl"] == -50.0
    assert per[v2.id]["trade_counts"]["losing"] == 1


def test_stats_break_down_each_version_by_test_type(client, db_session):
    s, v1, _ = _seed(db_session)
    _trade(db_session, v1.id, 40.0, 4)
    forward = db_session.query(Trade).filter(Trade.version_id == v1.id).order_by(Trade.id.desc()).first()
    forward.test_type = TestType.FORWARD
    db_session.commit()
    body = client.get(f"/api/strategies/{s.id}/stats").json()
    first = next(row for row in body["per_version"] if row["version_id"] == v1.id)
    assert set(first["by_test_type"]) == {"backtest", "forward"}
    assert first["by_test_type"]["backtest"]["total_trades"] == 2
    assert first["by_test_type"]["forward"]["total_trades"] == 1
    assert set(body["available_test_types"]) == {"backtest", "forward"}
