"""تست‌های Phase 48a — مقایسه و رتبه‌بندی نسخه‌ها (`POST /api/analytics/compare`).

قرارداد جدید: `{comparison, test_type, filters, best}`؛ هر item دارای
`metrics` / `score` / `rank` / `reasons` است.
"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion
from app.services.version_score import calculate_version_score


def _iso(month: int, day: int, hour: int = 10) -> str:
    return (
        datetime(2025, month, day, hour, 0, tzinfo=timezone.utc)
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


def _add_trade(client, version_id, pnl, *, month=3, day=1, symbol="XAUUSD") -> None:
    r = client.post(
        "/api/trades/manual",
        json={
            "symbol": symbol,
            "direction": "buy",
            "open_time": _iso(month, day, 10),
            "close_time": _iso(month, day, 11),
            "open_price": 2000.0,
            "close_price": 2010.0,
            "size": 1.0,
            "pnl": pnl,
            "test_type": "backtest",
            "version_id": version_id,
        },
    )
    assert r.status_code == 200, r.text


def _analyze(client, version_id) -> None:
    r = client.post(f"/api/analytics/analyze/version/{version_id}?test_type=backtest")
    assert r.status_code == 200, r.text


def _cmp(client, version_ids, **kw):
    r = client.post("/api/analytics/compare", json={"version_ids": version_ids, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def _item(body, vid):
    return next(i for i in body["comparison"] if i["version_id"] == vid)


# ═════════════════════════════════════════════
# مقایسهٔ پایه
# ═════════════════════════════════════════════
def test_compare_two_versions(client, db_session):
    v1 = _make_version(client, db_session, "S-48a-1")
    _add_trade(client, v1, 200.0, day=1)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-2")
    _add_trade(client, v2, -50.0, day=2)
    _analyze(client, v2)

    body = _cmp(client, [v1, v2])
    assert body["test_type"] == "BACKTEST"
    assert {i["version_id"] for i in body["comparison"]} == {v1, v2}
    assert all("metrics" in i for i in body["comparison"])
    assert all("score" in i for i in body["comparison"])
    assert sorted(i["rank"] for i in body["comparison"]) == [1, 2]
    assert body["filters"] == {"symbol": None, "date_from": None, "date_to": None}


def test_compare_ranking(client, db_session):
    """نسخهٔ با عملکرد بهتر باید rank 1 بگیرد (حتی اگر بعداً در لیست بیاید)."""
    best = _make_version(client, db_session, "S-48a-best")
    for d, p in [(1, 300.0), (2, 300.0)]:
        _add_trade(client, best, p, day=d)
    _analyze(client, best)

    worst = _make_version(client, db_session, "S-48a-worst")
    _add_trade(client, worst, -100.0, day=3)
    _analyze(client, worst)

    body = _cmp(client, [worst, best])  # ترتیب ورودی عمداً برعکس
    assert body["comparison"][0]["version_id"] == best
    assert body["comparison"][0]["rank"] == 1
    assert body["best"]["version_id"] == best


def test_compare_score_calculation(client, db_session):
    """Score هر item باید برابر تابع `calculate_version_score` باشد."""
    v1 = _make_version(client, db_session, "S-48a-sc1")
    _add_trade(client, v1, 150.0, day=1)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-sc2")
    _add_trade(client, v2, 100.0, day=2)
    _analyze(client, v2)

    body = _cmp(client, [v1, v2])
    item = _item(body, v1)
    assert item["score"] == calculate_version_score(item["metrics"])["score"]
    assert "sample_status" in item
    assert "warnings" in item
    assert "components" in item


def test_compare_reasons(client, db_session):
    """بهترین نسخه باید دلیل «بهترین نسخه» را داشته باشد."""
    v1 = _make_version(client, db_session, "S-48a-r1")
    _add_trade(client, v1, 500.0, day=1)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-r2")
    _add_trade(client, v2, -100.0, day=2)
    _analyze(client, v2)

    body = _cmp(client, [v1, v2])
    best_item = _item(body, v1)
    assert best_item["reasons"]
    assert any("بهترین" in r["text"] for r in best_item["reasons"])


# ═════════════════════════════════════════════
# فیلترها
# ═════════════════════════════════════════════
def test_compare_with_symbol_filter(client, db_session):
    v1 = _make_version(client, db_session, "S-48a-sym1")
    _add_trade(client, v1, 1000.0, day=1, symbol="XAUUSD")
    _add_trade(client, v1, -800.0, day=2, symbol="EURUSD")
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-sym2")
    _add_trade(client, v2, 100.0, day=3)
    _analyze(client, v2)

    unfiltered = _item(_cmp(client, [v1, v2]), v1)["metrics"]["net_pnl"]
    assert unfiltered == 200.0  # 1000 - 800

    filtered = _item(_cmp(client, [v1, v2], symbol="XAUUSD"), v1)["metrics"]["net_pnl"]
    assert filtered == 1000.0


def test_compare_with_date_filter(client, db_session):
    v1 = _make_version(client, db_session, "S-48a-date1")
    _add_trade(client, v1, 1000.0, month=3, day=1)
    _add_trade(client, v1, -800.0, month=3, day=20)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-date2")
    _add_trade(client, v2, 100.0, month=3, day=25)
    _analyze(client, v2)

    unfiltered = _item(_cmp(client, [v1, v2]), v1)["metrics"]["net_pnl"]
    assert unfiltered == 200.0

    filtered = _item(
        _cmp(client, [v1, v2], date_from="2025-03-01", date_to="2025-03-05"), v1
    )["metrics"]["net_pnl"]
    assert filtered == 1000.0
