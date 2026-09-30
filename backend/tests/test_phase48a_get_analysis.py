"""تست‌های Phase 48a.2 — `GET /api/analytics/{version_id}` با `test_type`.

باگ: `.first()` روی `version_id` وقتی نسخه هم تحلیل Backtest و هم Forward دارد،
نتیجهٔ نامعین می‌داد. اکنون کلید دامنه با `test_type` قطعی می‌شود.
"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion


def _iso(day: int, hour: int = 10) -> str:
    return (
        datetime(2025, 4, day, hour, 0, tzinfo=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _make_version(client, db_session, name: str) -> int:
    r = client.post("/api/strategies/", json={"name": name})
    assert r.status_code == 200, r.text
    strategy_id = db_session.query(Strategy).order_by(Strategy.id.desc()).first().id

    r = client.post(
        f"/api/strategies/{strategy_id}/versions",
        json={"version_name": "v1", "test_type": "backtest"},
    )
    assert r.status_code == 200, r.text
    return db_session.query(StrategyVersion).order_by(StrategyVersion.id.desc()).first().id


def _add_trade(client, version_id, pnl, day, test_type="backtest") -> None:
    r = client.post(
        "/api/trades/manual",
        json={
            "symbol": "XAUUSD",
            "direction": "buy",
            "open_time": _iso(day, 10),
            "close_time": _iso(day, 11),
            "open_price": 2000.0,
            "close_price": 2010.0,
            "size": 1.0,
            "pnl": pnl,
            "test_type": test_type,
            "version_id": version_id,
        },
    )
    assert r.status_code == 200, r.text


def test_get_analytics_with_test_type(client, db_session):
    """GET با test_type باید تحلیل همان نوع را قطعی برگرداند (Backtest ≠ Forward)."""
    v = _make_version(client, db_session, "S-48a-get")
    _add_trade(client, v, 100.0, day=1, test_type="backtest")
    _add_trade(client, v, 50.0, day=2, test_type="backtest")
    _add_trade(client, v, -30.0, day=3, test_type="forward")
    db_session.commit()

    assert client.post(f"/api/analytics/analyze/version/{v}?test_type=backtest").status_code == 200
    assert client.post(f"/api/analytics/analyze/version/{v}?test_type=forward").status_code == 200

    bt = client.get(f"/api/analytics/{v}?test_type=BACKTEST")
    assert bt.status_code == 200, bt.text
    assert bt.json()["total_trades"] == 2
    assert bt.json()["net_pnl"] == 150.0

    fw = client.get(f"/api/analytics/{v}?test_type=FORWARD")
    assert fw.status_code == 200, fw.text
    assert fw.json()["total_trades"] == 1
    assert fw.json()["net_pnl"] == -30.0

    # بدون پارامتر ⇒ پیش‌فرض BACKTEST (قطعی)
    default = client.get(f"/api/analytics/{v}")
    assert default.status_code == 200, default.text
    assert default.json()["total_trades"] == 2


def test_get_analytics_not_found_404(client, db_session):
    """نسخهٔ بدون تحلیل ⇒ ۴۰۴."""
    v = _make_version(client, db_session, "S-48a-get404")
    _add_trade(client, v, 100.0, day=1)
    db_session.commit()

    r = client.get(f"/api/analytics/{v}?test_type=BACKTEST")
    assert r.status_code == 404, r.text
