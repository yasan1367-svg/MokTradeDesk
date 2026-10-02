"""تست‌های فاز ۵۳.۱ — تحلیل کهنه بر پایهٔ آخرین ویرایش معاملات (`updated_at`).

باگ (Audit): گارد تازگی فقط **تعداد** معاملات را مقایسه می‌کرد؛ ویرایش سود یا
زمانِ معامله بدون تغییر تعداد ⇒ تحلیل کهنه همچنان سرو می‌شد.
"""
from datetime import datetime, timezone

from app.models.strategy import (
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

    trade.pnl = 250.0
    db_session.commit()

    flat = _get(client, version.id)
    assert flat.status_code == 404
    assert "کهنه" in flat.json()["detail"]

    scoped = _get_scoped(client, version.id)
    assert scoped.status_code == 404
    assert "کهنه" in scoped.json()["detail"]


def test_stale_after_time_edit(client, db_session):
    """ویرایش زمان بسته‌شدن بدون تغییر تعداد ⇒ تحلیل باید کهنه (۴۰۴) شود."""
    version = _version(db_session)
    trade = _trade(db_session, version.id, close_day=2)
    _analyze(client, version.id)
    assert _get(client, version.id).status_code == 200

    trade.close_time = datetime(2025, 1, 5, 11, 0, tzinfo=timezone.utc)
    db_session.commit()

    flat = _get(client, version.id)
    assert flat.status_code == 404
    assert "کهنه" in flat.json()["detail"]

    scoped = _get_scoped(client, version.id)
    assert scoped.status_code == 404
    assert "کهنه" in scoped.json()["detail"]
