"""تست‌های فاز ۵۳.۱ — گارد حذف استراتژی (جلوگیری از cascade و از دست رفتن داده).

باگ (Audit): `DELETE /api/strategies/{id}` بدون هیچ گاردی کل نسخه‌ها، معاملات،
تحلیل‌ها و وابستگی‌هایشان را به‌صورت سخت پاک می‌کرد.
"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource


def _strategy(db, name="S53-del"):
    s = Strategy(name=name)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _version(db, strategy_id):
    v = StrategyVersion(strategy_id=strategy_id, version_name="v1")
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _trade(db, version_id, pnl=100.0):
    t = Trade(
        version_id=version_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 2, 11, 0, tzinfo=timezone.utc),
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
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_delete_empty_strategy_ok(client, db_session):
    """استراتژی بدون معامله/تحلیل ⇒ حذف موفق (۲۰۰)."""
    s = _strategy(db_session)
    _version(db_session, s.id)

    r = client.delete(f"/api/strategies/{s.id}")
    assert r.status_code == 200, r.text

    db_session.expire_all()
    assert db_session.query(Strategy).filter(Strategy.id == s.id).first() is None


def test_delete_strategy_with_trades_409(client, db_session):
    """استراتژی با معامله ⇒ ۴۰۹ و داده دست‌نخورده می‌ماند."""
    s = _strategy(db_session)
    v = _version(db_session, s.id)
    _trade(db_session, v.id)

    r = client.delete(f"/api/strategies/{s.id}")
    assert r.status_code == 409
    assert "معامله" in r.json()["detail"]

    # cascade اجرا نشده ⇒ معامله و نسخه هنوز هستند
    db_session.expire_all()
    assert db_session.query(Trade).count() == 1
    assert db_session.query(StrategyVersion).filter(StrategyVersion.id == v.id).first() is not None


def test_delete_strategy_with_analysis_409(client, db_session):
    """استراتژی با تحلیل ذخیره‌شده (حتی بدون معاملهٔ فعال) ⇒ ۴۰۹."""
    s = _strategy(db_session)
    v = _version(db_session, s.id)
    t = _trade(db_session, v.id)

    assert client.post(
        f"/api/analytics/analyze/version/{v.id}?test_type=backtest"
    ).status_code == 200

    # حذف نرم معامله ⇒ trade_count=0 ولی analysis_count=1
    assert client.delete(f"/api/trades/{t.id}").status_code == 200

    r = client.delete(f"/api/strategies/{s.id}")
    assert r.status_code == 409
    assert "تحلیل" in r.json()["detail"]
