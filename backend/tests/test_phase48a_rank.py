"""تست‌های Phase 48a.5 — `POST /api/analytics/rank`.

رتبه‌بندی نسخه‌ها بر پایهٔ Score (نزولی) + بهترین نسخه.
"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion


def _iso(day: int, hour: int = 10) -> str:
    return (
        datetime(2025, 5, day, hour, 0, tzinfo=timezone.utc)
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


def _add_trade(client, version_id, pnl, day) -> None:
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
            "test_type": "backtest",
            "version_id": version_id,
        },
    )
    assert r.status_code == 200, r.text


def _seed_version(client, db_session, name, pnls) -> int:
    vid = _make_version(client, db_session, name)
    for i, pnl in enumerate(pnls, start=1):
        _add_trade(client, vid, pnl, day=i)
    r = client.post(f"/api/analytics/analyze/version/{vid}?test_type=backtest")
    assert r.status_code == 200, r.text
    return vid


def test_rank_returns_sorted(client, db_session):
    """رتبه‌بندی باید نزولی بر اساس Score باشد و بهترین، اول بیاید."""
    good = _seed_version(client, db_session, "S-48a-rank-good",
                         [200.0, 200.0, 200.0, 200.0, 200.0])          # WR=100، بدون باخت
    mid = _seed_version(client, db_session, "S-48a-rank-mid",
                        [300.0, 300.0, 300.0, -100.0])                  # WR=75، PF=9
    bad = _seed_version(client, db_session, "S-48a-rank-bad",
                        [50.0, -200.0, -200.0, -200.0])                 # WR=25، زیان‌ده

    # ترتیب ورودی عمداً به‌هم‌ریخته تا مرتب‌سازی اثبات شود
    r = client.post("/api/analytics/rank", json={"version_ids": [bad, good, mid]})
    assert r.status_code == 200, r.text
    body = r.json()

    ranking = body["ranking"]
    assert len(ranking) == 3
    assert [x["version_id"] for x in ranking] == [good, mid, bad]

    scores = [x["score"] for x in ranking]
    assert scores == sorted(scores, reverse=True)

    assert [x["rank"] for x in ranking] == [1, 2, 3]
    assert body["best"]["version_id"] == good
    assert body["best"]["rank"] == 1
