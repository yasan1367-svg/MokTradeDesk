"""تست‌های Phase 41.3 — رفع باگ `POST /api/analytics/compare`.

باگ‌ها:
- کد مرده: `raise HTTPException(404, ...)` بعد از `return` (unreachable + NameError).
- `service = AnalysisService(db)` دو بار تکرار شده بود.
- `except ValueError` حذف شده بود ⇒ نبود نسخهٔ قابل‌مقایسه **۵۰۰** برمی‌گرداند نه **۴۰۴**.
"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion


def _iso(day: int, hour: int = 10) -> str:
    return datetime(2025, 2, day, hour, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


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


def _add_trade(client, version_id: int, pnl: float, day: int) -> None:
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


# ═════════════════════════════════════════════
# ۴۰۴ به‌جای ۵۰۰
# ═════════════════════════════════════════════
def test_compare_unanalyzed_version_returns_404(client, db_session):
    """نسخه‌ی تحلیل‌نشده ⇒ ۴۰۴ (قبلاً ۵۰۰)."""
    version_id = _make_version(client, db_session, "S-unanalyzed")

    r = client.post("/api/analytics/compare", json={"version_ids": [version_id]})
    assert r.status_code == 404, r.text
    assert r.json()["detail"]


def test_compare_invalid_input_returns_404(client, db_session):
    """ورودی نامعتبر (نسخه‌ی ناموجود / لیست خالی) ⇒ ۴۰۴ نه ۵۰۰."""
    missing = client.post("/api/analytics/compare", json={"version_ids": [999999]})
    assert missing.status_code == 404, missing.text

    empty = client.post("/api/analytics/compare", json={"version_ids": []})
    assert empty.status_code == 404, empty.text


# ═════════════════════════════════════════════
# مسیر موفق
# ═════════════════════════════════════════════
def test_compare_two_analyzed_versions_works(client, db_session):
    """دو نسخه‌ی تحلیل‌شده ⇒ ۲۰۰ با items و پیشنهاد بهترین."""
    v1 = _make_version(client, db_session, "S-best")
    _add_trade(client, v1, 100.0, 1)
    assert client.post(f"/api/analytics/analyze/{v1}").status_code == 200

    v2 = _make_version(client, db_session, "S-worse")
    _add_trade(client, v2, -40.0, 2)
    _add_trade(client, v2, 60.0, 3)
    assert client.post(f"/api/analytics/analyze/{v2}").status_code == 200

    r = client.post("/api/analytics/compare", json={"version_ids": [v1, v2]})
    assert r.status_code == 200, r.text
    body = r.json()

    assert {item["version_id"] for item in body["items"]} == {v1, v2}
    assert body["best_version_id"] in (v1, v2)
    assert body["recommendation"]
