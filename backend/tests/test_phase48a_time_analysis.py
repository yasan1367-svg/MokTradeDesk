"""تست‌های Phase 48a.3 — تحلیل زمانی بر پایهٔ **زمان ورود** (`open_time`).

قبل: session/weekday/hour (و بازه‌های سفارشی) از `close_time` استفاده می‌کردند.
بعد: از `open_time` — چون «زمان ورود» ملاک است.
"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion


def _dt(day: int, hour: int, minute: int = 0) -> str:
    return (
        datetime(2025, 4, day, hour, minute, tzinfo=timezone.utc)
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


def _add_trade(client, version_id, *, open_time: str, close_time: str, pnl: float = 100.0) -> None:
    r = client.post(
        "/api/trades/manual",
        json={
            "symbol": "XAUUSD",
            "direction": "buy",
            "open_time": open_time,
            "close_time": close_time,
            "open_price": 2000.0,
            "close_price": 2010.0,
            "size": 1.0,
            "pnl": pnl,
            "test_type": "backtest",
            "version_id": version_id,
        },
    )
    assert r.status_code == 200, r.text


def _analyze_and_get(client, version_id) -> dict:
    assert client.post(f"/api/analytics/analyze/version/{version_id}?test_type=backtest").status_code == 200
    r = client.get(f"/api/analytics/analysis/version/{version_id}?test_type=BACKTEST")
    assert r.status_code == 200, r.text
    return r.json()


# ═════════════════════════════════════════════
# سشن
# ═════════════════════════════════════════════
def test_session_uses_open_time(client, db_session):
    """ورود ۰۳:۰۰ (Asia) و خروج ۲۰:۰۰ (America) ⇒ باید Asia شمرده شود."""
    v = _make_version(client, db_session, "S-48a-sess")
    _add_trade(client, v, open_time=_dt(7, 3), close_time=_dt(7, 20))
    db_session.commit()

    body = _analyze_and_get(client, v)
    sessions = body["session_analysis"]
    assert "Asia" in sessions           # 03:00 → open_time
    assert "America" not in sessions    # 20:00 → close_time (نباید لحاظ شود)


# ═════════════════════════════════════════════
# روز هفته
# ═════════════════════════════════════════════
def test_weekday_uses_open_time(client, db_session):
    """ورود دوشنبه (2025-04-07) و خروج سه‌شنبه ⇒ باید Monday شمرده شود."""
    v = _make_version(client, db_session, "S-48a-week")
    _add_trade(client, v, open_time=_dt(7, 3), close_time=_dt(8, 20))
    db_session.commit()

    body = _analyze_and_get(client, v)
    weekdays = body["weekday_analysis"]
    assert "Monday" in weekdays
    assert "Tuesday" not in weekdays


# ═════════════════════════════════════════════
# ساعت
# ═════════════════════════════════════════════
def test_hour_uses_open_time(client, db_session):
    """ورود ساعت ۳ و خروج ساعت ۲۰ ⇒ باید کلید «3» باشد نه «20»."""
    v = _make_version(client, db_session, "S-48a-hour")
    _add_trade(client, v, open_time=_dt(7, 3), close_time=_dt(7, 20))
    db_session.commit()

    body = _analyze_and_get(client, v)
    hours = body["hour_analysis"]
    assert "3" in hours
    assert "20" not in hours
