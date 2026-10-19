"""تست‌های فاز ۵۳.۴.۱ — مقایسهٔ نسخه‌ها برای معاملات REAL.

باگ: `compare_versions` همیشه `analysis_trades_filter()` (غیر-REAL) می‌زد و تحلیل
ذخیره‌شده طلب می‌کرد؛ پس REAL_PERSONAL/REAL_PROP هرگز قابل مقایسه نبودند.
"""
from datetime import datetime, timezone

from app.models.finance import Currency
from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.models.trading import Broker, PersonalTradingAccount


def _strategy(db):
    s = Strategy(name="S53rc")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _version(db, strategy, name):
    v = StrategyVersion(strategy_id=strategy.id, version_name=name)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _pta(db):
    b = Broker(name="B-rc")
    db.add(b)
    db.flush()
    a = PersonalTradingAccount(
        broker_id=b.id, account_number="ACC-rc", account_label="rc",
        currency=Currency.USDT, initial_balance=10000.0, current_balance=10000.0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _stage(db):
    firm = PropFirm(name="F-rc")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="rc")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id, stage_type=StageType.FUNDED_REAL,
        status=StageStatus.ACTIVE, initial_balance=10000.0,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


def _trade(db, version_id, pnl, *, open_day, close_day, test_type, pta_id=None, stage_id=None):
    db.add(Trade(
        version_id=version_id,
        personal_trading_account_id=pta_id,
        prop_stage_id=stage_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 9, open_day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 9, close_day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=test_type,
    ))


def _compare(client, ids, test_type):
    r = client.post("/api/analytics/compare", json={"version_ids": ids, "test_type": test_type})
    assert r.status_code == 200, r.text
    return r.json()


def _item(body, vid):
    return next(i for i in body["comparison"] if i["version_id"] == vid)


def test_compare_real_personal(client, db_session):
    s = _strategy(db_session)
    v1 = _version(db_session, s, "p1")
    v2 = _version(db_session, s, "p2")
    pta = _pta(db_session)
    _trade(db_session, v1.id, 100.0, open_day=1, close_day=1,
           test_type=TestType.REAL_PERSONAL, pta_id=pta.id)
    _trade(db_session, v1.id, 200.0, open_day=2, close_day=2,
           test_type=TestType.REAL_PERSONAL, pta_id=pta.id)
    _trade(db_session, v2.id, -50.0, open_day=3, close_day=3,
           test_type=TestType.REAL_PERSONAL, pta_id=pta.id)
    db_session.commit()

    body = _compare(client, [v1.id, v2.id], "REAL_PERSONAL")
    assert _item(body, v1.id)["metrics"]["net_pnl"] == 300.0
    assert _item(body, v1.id)["metrics"]["total_trades"] == 2
    assert _item(body, v2.id)["metrics"]["net_pnl"] == -50.0
    assert "error" not in _item(body, v1.id)


def test_compare_real_prop(client, db_session):
    s = _strategy(db_session)
    v1 = _version(db_session, s, "r1")
    v2 = _version(db_session, s, "r2")
    stage = _stage(db_session)
    _trade(db_session, v1.id, 100.0, open_day=1, close_day=1,
           test_type=TestType.REAL_PROP, stage_id=stage.id)
    _trade(db_session, v1.id, 200.0, open_day=2, close_day=2,
           test_type=TestType.REAL_PROP, stage_id=stage.id)
    _trade(db_session, v2.id, -50.0, open_day=3, close_day=3,
           test_type=TestType.REAL_PROP, stage_id=stage.id)
    db_session.commit()

    body = _compare(client, [v1.id, v2.id], "REAL_PROP")
    assert _item(body, v1.id)["metrics"]["net_pnl"] == 300.0
    assert _item(body, v2.id)["metrics"]["net_pnl"] == -50.0


def test_compare_real_by_close_time(client, db_session):
    """فیلتر تاریخ باید بر پایهٔ close_time باشد (نه open_time)."""
    s = _strategy(db_session)
    v1 = _version(db_session, s, "c1")
    v2 = _version(db_session, s, "c2")
    pta = _pta(db_session)
    # هر دو open در 09-01؛ close یکی 09-10 و دیگری 09-20
    _trade(db_session, v1.id, 1000.0, open_day=1, close_day=10,
           test_type=TestType.REAL_PERSONAL, pta_id=pta.id)
    _trade(db_session, v1.id, -800.0, open_day=1, close_day=20,
           test_type=TestType.REAL_PERSONAL, pta_id=pta.id)
    _trade(db_session, v2.id, 50.0, open_day=1, close_day=10,
           test_type=TestType.REAL_PERSONAL, pta_id=pta.id)
    db_session.commit()

    # بدون فیلتر ⇒ جمع هر دو
    plain = _item(_compare(client, [v1.id, v2.id], "REAL_PERSONAL"), v1.id)
    assert plain["metrics"]["net_pnl"] == 200.0

    # با فیلتر 09-01 .. 09-15 ⇒ فقط close_time=09-10
    r = client.post("/api/analytics/compare", json={
        "version_ids": [v1.id, v2.id], "test_type": "REAL_PERSONAL",
        "date_from": "2025-09-01", "date_to": "2025-09-15",
    })
    assert r.status_code == 200, r.text
    filtered = _item(r.json(), v1.id)
    assert filtered["metrics"]["net_pnl"] == 1000.0   # نه 200 (اگر open_time مبنا بود)
