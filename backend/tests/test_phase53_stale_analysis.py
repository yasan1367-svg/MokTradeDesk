"""تست‌های فاز ۵۳.۱ — تحلیل کهنه بر پایهٔ آخرین ویرایش معاملات (`updated_at`).

باگ (Audit): گارد تازگی فقط **تعداد** معاملات را مقایسه می‌کرد؛ ویرایش سود یا
زمانِ معامله بدون تغییر تعداد ⇒ تحلیل کهنه همچنان سرو می‌شد.
"""
from datetime import datetime, timezone
import pytest

from app.models.strategy import (
    AnalysisResult,
    Strategy,
    StrategyVersion,
    TestType,
    Trade,
    TradeSource,
)


def _version(db):
    strategy = Strategy(name="S53-stale")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def _trade(db, version_id, *, pnl=100.0, close_day=2):
    trade = Trade(
        version_id=version_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, close_day, 11, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        entry_sequence=1,
        source=TradeSource.MANUAL,
        test_type=TestType.BACKTEST,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def _analyze(client, version_id):
    r = client.post(f"/api/analytics/analyze/version/{version_id}?test_type=backtest")
    assert r.status_code == 200, r.text


def _get(client, version_id):
    """endpoint تخت `GET /api/analytics/{id}` (مصرف `getAnalysis`/`getVersionAnalysis`)."""
    return client.get(f"/api/analytics/{version_id}?test_type=BACKTEST")


def _get_scoped(client, version_id):
    """endpoint اسکوپ‌دار `GET /api/analytics/analysis/version/{id}` (`_guard_analyzable`)."""
    return client.get(f"/api/analytics/analysis/version/{version_id}?test_type=BACKTEST")


@pytest.mark.parametrize("endpoint, items_key", [("compare", "comparison"), ("rank", "ranking")])
@pytest.mark.parametrize("change", ["edit", "add", "delete"])
def test_compare_marks_stale_analysis_as_error(client, db_session, endpoint, items_key, change):
    stale_version = _version(db_session)
    trade = _trade(db_session, stale_version.id, pnl=1000.0)
    _analyze(client, stale_version.id)
    fresh_version = _version(db_session)
    _trade(db_session, fresh_version.id, pnl=10.0)
    _analyze(client, fresh_version.id)

    if change == "edit":
        trade.pnl = 2000.0
        db_session.commit()
    elif change == "add":
        _trade(db_session, stale_version.id)
    else:
        db_session.delete(trade)
        db_session.commit()

    for getter in (_get, _get_scoped):
        assert getter(client, stale_version.id).status_code == 404
    response = client.post(f"/api/analytics/{endpoint}", json={
        "version_ids": [stale_version.id, fresh_version.id], "test_type": "BACKTEST",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    stale = next(item for item in body[items_key] if item["version_id"] == stale_version.id)
    assert stale["stale"] is True
    assert "کهنه" in stale["error"]
    assert all(key not in stale for key in ("metrics", "score", "rank"))
    assert body["best"]["version_id"] == fresh_version.id
    assert body["best"]["rank"] == 1

    _trade(db_session, fresh_version.id)
    only_stale = client.post(f"/api/analytics/{endpoint}", json={
        "version_ids": [stale_version.id, fresh_version.id], "test_type": "BACKTEST",
    })
    assert only_stale.status_code == 200, only_stale.text
    assert only_stale.json()["best"] is None


@pytest.mark.parametrize("change", ["edit", "add", "delete"])
def test_filtered_compare_rejects_stale_analysis(client, db_session, change):
    version = _version(db_session)
    trade = _trade(db_session, version.id)
    _analyze(client, version.id)

    if change == "edit":
        trade.pnl = 250.0
        db_session.commit()
    elif change == "add":
        _trade(db_session, version.id)
    else:
        db_session.delete(trade)
        db_session.commit()

    response = client.post("/api/analytics/compare", json={
        "version_ids": [version.id, _version(db_session).id],
        "test_type": "BACKTEST", "symbol": "XAUUSD",
    })
    assert response.status_code == 200, response.text
    stale = next(i for i in response.json()["comparison"] if i["version_id"] == version.id)
    assert stale.get("stale") is True
    assert "metrics" not in stale


def test_get_scoped_analysis_does_not_fallback_to_other_test_type(client, db_session):
    version = _version(db_session)
    forward = _trade(db_session, version.id)
    forward.test_type = TestType.FORWARD
    db_session.commit()
    legacy = client.post(f"/api/analytics/analyze/version/{version.id}")
    assert legacy.status_code == 200, legacy.text

    response = client.get(f"/api/analytics/{version.id}?test_type=BACKTEST")
    assert response.status_code == 404


def test_strategy_stats_and_version_trade_list_exclude_open_trades(client, db_session):
    version = _version(db_session)
    _trade(db_session, version.id)
    opened = _trade(db_session, version.id)
    opened.close_time = None
    db_session.commit()

    strategy_id = db_session.get(Strategy, version.strategy_id).id
    stats = client.get(f"/api/strategies/{strategy_id}/stats")
    trades = client.get(f"/api/strategies/versions/{version.id}/trades")
    assert stats.status_code == 200, stats.text
    assert stats.json()["total_trades"] == 1
    assert len(trades.json()) == 1


def test_compare_legacy_fallback_checks_snapshot_scope(client, db_session):
    version = _version(db_session)
    _trade(db_session, version.id)
    forward = _trade(db_session, version.id)
    forward.test_type = TestType.FORWARD
    db_session.commit()
    response = client.post(f"/api/analytics/analyze/version/{version.id}")
    assert response.status_code == 200, response.text
    other = _version(db_session)
    _trade(db_session, other.id)
    _analyze(client, other.id)
    payload = {"version_ids": [version.id, other.id], "test_type": "BACKTEST"}
    response = client.post("/api/analytics/compare", json=payload)
    assert response.status_code == 200, response.text
    item = next(i for i in response.json()["comparison"] if i["version_id"] == version.id)
    assert item["status"] == "missing_analysis"
    assert "metrics" not in item

    forward.pnl = 500.0
    db_session.commit()
    response = client.post("/api/analytics/compare", json=payload)
    assert response.status_code == 200, response.text
    item = next(i for i in response.json()["comparison"] if i["version_id"] == version.id)
    assert item["status"] == "missing_analysis"


def test_compare_with_specific_test_type_does_not_use_legacy_fallback(client, db_session):
    """نوع تست مشخص باید تحلیل legacy را رد کند، حتی اگر legacy موجود باشد."""
    version = _version(db_session)
    _trade(db_session, version.id)
    forward = _trade(db_session, version.id)
    forward.test_type = TestType.FORWARD
    db_session.commit()

    legacy = client.post(f"/api/analytics/analyze/version/{version.id}")
    assert legacy.status_code == 200, legacy.text
    other = _version(db_session)
    _trade(db_session, other.id)
    _analyze(client, other.id)
    response = client.post("/api/analytics/compare", json={
        "version_ids": [version.id, other.id], "test_type": "BACKTEST",
    })
    assert response.status_code == 200, response.text
    item = next(i for i in response.json()["comparison"] if i["version_id"] == version.id)
    assert item["status"] == "missing_analysis"
    assert "تحلیل مجدد" in item["error"]
    assert "metrics" not in item


def test_compare_zero_trades_is_not_best(client, db_session):
    """نسخه‌ای که فیلتر مقایسه برایش صفر معامله دارد، best نمی‌شود."""
    matching = _version(db_session)
    _trade(db_session, matching.id)
    _analyze(client, matching.id)

    no_matching_trades = _version(db_session)
    trade = _trade(db_session, no_matching_trades.id)
    trade.symbol = "EURUSD"
    db_session.commit()
    _analyze(client, no_matching_trades.id)

    response = client.post("/api/analytics/compare", json={
        "version_ids": [no_matching_trades.id, matching.id],
        "test_type": "BACKTEST",
        "symbol": "XAUUSD",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["best"]["version_id"] == matching.id
    no_data = next(i for i in body["comparison"] if i["version_id"] == no_matching_trades.id)
    assert no_data["status"] == "no_data"
    assert no_data["metrics"]["total_trades"] == 0
    assert no_data["score"] == 0
    assert no_data["rank"] is None


def test_not_stale_if_no_changes(client, db_session):
    """بدون تغییر ⇒ تحلیل در هر دو endpoint تازه است (۲۰۰)."""
    version = _version(db_session)
    _trade(db_session, version.id)
    _analyze(client, version.id)

    for getter in (_get, _get_scoped):
        r = getter(client, version.id)
        assert r.status_code == 200, r.text
        assert r.json()["total_trades"] == 1
def test_stale_after_pnl_edit(client, db_session):
    """ویرایش سود بدون تغییر تعداد ⇒ تحلیل باید کهنه (۴۰۴) شود."""
    version = _version(db_session)
    trade = _trade(db_session, version.id, pnl=100.0)
    _analyze(client, version.id)
    assert _get(client, version.id).status_code == 200
    analysis_created_at = db_session.query(AnalysisResult.created_at).filter(
        AnalysisResult.version_id == version.id
    ).scalar()

    trade.pnl = 250.0
    # Force equality with the pre-edit timestamp to model a coarse DB clock.
    db_session.flush()
    trade.updated_at = analysis_created_at
    db_session.commit()

    flat = _get(client, version.id)
    assert flat.status_code == 404
    assert "کهنه" in flat.json()["detail"]

    scoped = _get_scoped(client, version.id)
    assert scoped.status_code == 404
    assert "کهنه" in scoped.json()["detail"]

    peer = _version(db_session)
    _trade(db_session, peer.id)
    _analyze(client, peer.id)
    for symbol in (None, "XAUUSD"):
        body = {"version_ids": [version.id, peer.id], "test_type": "BACKTEST"}
        if symbol:
            body["symbol"] = symbol
        response = client.post("/api/analytics/compare", json=body)
        assert response.status_code == 200, response.text
        item = next(
            item for item in response.json()["comparison"]
            if item["version_id"] == version.id
        )
        assert item["stale"] is True


def test_stale_after_time_edit(client, db_session):
    """ویرایش زمان بسته‌شدن بدون تغییر تعداد ⇒ تحلیل باید کهنه (۴۰۴) شود."""
    version = _version(db_session)
    trade = _trade(db_session, version.id, close_day=2)
    _analyze(client, version.id)
    assert _get(client, version.id).status_code == 200
    analysis_created_at = db_session.query(AnalysisResult.created_at).filter(
        AnalysisResult.version_id == version.id
    ).scalar()

    trade.close_time = datetime(2025, 1, 5, 11, 0, tzinfo=timezone.utc)
    db_session.flush()
    trade.updated_at = analysis_created_at
    db_session.commit()

    flat = _get(client, version.id)
    assert flat.status_code == 404
    assert "کهنه" in flat.json()["detail"]

    scoped = _get_scoped(client, version.id)
    assert scoped.status_code == 404
    assert "کهنه" in scoped.json()["detail"]

    peer = _version(db_session)
    _trade(db_session, peer.id)
    _analyze(client, peer.id)
    for symbol in (None, "XAUUSD"):
        body = {"version_ids": [version.id, peer.id], "test_type": "BACKTEST"}
        if symbol:
            body["symbol"] = symbol
        response = client.post("/api/analytics/compare", json=body)
        assert response.status_code == 200, response.text
        item = next(
            item for item in response.json()["comparison"]
            if item["version_id"] == version.id
        )
        assert item["stale"] is True
