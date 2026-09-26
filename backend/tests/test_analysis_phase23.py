"""تست‌های فاز ۲۳ — استقلال تحلیل Backtest / Forward / مرحله پراپ / بروکر

باگ‌های رفع‌شده:
۱. `TestType("BACKTEST")` مقدار enum را lowercase فرض می‌کرد ⇒ خطای ۵۰۰.
۲. تحلیل Backtest و Forward یک نسخه هم را بازنویسی می‌کردند (scope_key یکسان).
۳. گارد GET تحلیل نسخه، `test_type` را نادیده می‌گرفت ⇒ ۴۰۴ «کهنه» وقتی هر دو نوع وجود داشت.
"""
from datetime import datetime, timezone

from app.models.finance import Account, AccountType, Currency
from app.models.prop import PropFirm, PropAccount, PropStage, StageType, StageStatus
from app.models.strategy import (
    AnalysisResult, AnalysisScope, Strategy, StrategyVersion, Trade, TestType, TradeSource,
)


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def _make_version(db, name="v1"):
    strategy = Strategy(name=f"S-{name}")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name=name)
    db.add(version)
    db.commit()
    db.refresh(version)
    return strategy, version


def _add_trade(db, *, version_id=None, test_type=None, pnl=100.0,
               prop_stage_id=None, finance_account_id=None):
    trade = Trade(
        version_id=version_id,
        prop_stage_id=prop_stage_id,
        finance_account_id=finance_account_id,
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
        test_type=test_type,
    )
    db.add(trade)
    return trade


def _seed_stage(db, label="A", stage_type=StageType.STAGE_1, finance_account_id=None):
    firm = PropFirm(name=f"Firm-{label}")
    db.add(firm)
    db.flush()
    account = PropAccount(
        prop_firm_id=firm.id, account_label=label, finance_account_id=finance_account_id
    )
    db.add(account)
    db.flush()
    stage = PropStage(
        prop_account_id=account.id, stage_type=stage_type, status=StageStatus.ACTIVE
    )
    db.add(stage)
    db.flush()
    return stage


# ═════════════════════════════════════════════
# ۱. Backtest و Forward مستقل (نسخه)
# ═════════════════════════════════════════════
def test_backtest_and_forward_are_independent(client, db_session):
    _, v = _make_version(db_session)
    for _ in range(3):
        _add_trade(db_session, version_id=v.id, test_type=TestType.BACKTEST, pnl=100)
    for _ in range(5):
        _add_trade(db_session, version_id=v.id, test_type=TestType.FORWARD, pnl=50)
    _add_trade(db_session, version_id=v.id, test_type=TestType.REAL, pnl=-9999)
    db_session.commit()

    # Backtest → فقط ۳ معامله
    assert client.post(f"/api/analytics/analyze/version/{v.id}",
                       params={"test_type": "BACKTEST"}).status_code == 200
    bt = client.get(f"/api/analytics/analysis/version/{v.id}",
                    params={"test_type": "BACKTEST"})
    assert bt.status_code == 200
    assert bt.json()["total_trades"] == 3
    assert bt.json()["net_pnl"] == 300.0

    # Forward → فقط ۵ معامله
    assert client.post(f"/api/analytics/analyze/version/{v.id}",
                       params={"test_type": "FORWARD"}).status_code == 200
    fw = client.get(f"/api/analytics/analysis/version/{v.id}",
                    params={"test_type": "FORWARD"})
    assert fw.status_code == 200
    assert fw.json()["total_trades"] == 5

    # چون Forward اضافه شد، Backtest نباید کهنه شود
    bt2 = client.get(f"/api/analytics/analysis/version/{v.id}",
                     params={"test_type": "BACKTEST"})
    assert bt2.status_code == 200
    assert bt2.json()["total_trades"] == 3

    # دو رکورد مستقل ذخیره شده‌اند
    db_session.expire_all()
    keys = {
        r.scope_key
        for r in db_session.query(AnalysisResult)
        .filter(AnalysisResult.scope == AnalysisScope.VERSION)
        .all()
    }
    assert keys == {f"{v.id}:BACKTEST", f"{v.id}:FORWARD"}


def test_lowercase_test_type_accepted(client, db_session):
    """test_type با حروف کوچک هم پذیرفته می‌شود (باگ TestType('BACKTEST'))."""
    _, v = _make_version(db_session)
    _add_trade(db_session, version_id=v.id, test_type=TestType.BACKTEST, pnl=10)
    db_session.commit()
    r = client.post(f"/api/analytics/analyze/version/{v.id}", params={"test_type": "backtest"})
    assert r.status_code == 200
    assert r.json()["test_type"] == "BACKTEST"


def test_missing_forward_returns_404_message(client, db_session):
    """نسخه‌ی بدون Forward → پیام روشن و ۴۰۴."""
    _, v = _make_version(db_session)
    _add_trade(db_session, version_id=v.id, test_type=TestType.BACKTEST, pnl=10)
    db_session.commit()
    r = client.post(f"/api/analytics/analyze/version/{v.id}", params={"test_type": "FORWARD"})
    assert r.status_code == 404
    assert "فوروارد" in r.json()["detail"]


def test_invalid_and_real_test_type_rejected(client, db_session):
    _, v = _make_version(db_session)
    _add_trade(db_session, version_id=v.id, test_type=TestType.BACKTEST, pnl=10)
    db_session.commit()
    assert client.post(f"/api/analytics/analyze/version/{v.id}",
                       params={"test_type": "xyz"}).status_code == 400
    assert client.post(f"/api/analytics/analyze/version/{v.id}",
                       params={"test_type": "REAL"}).status_code == 400


def test_version_trades_endpoint_filters_by_test_type(client, db_session):
    """لیست معاملات نسخه به تفکیک test_type (برای جدول معاملات)."""
    _, v = _make_version(db_session)
    _add_trade(db_session, version_id=v.id, test_type=TestType.BACKTEST, pnl=100)
    _add_trade(db_session, version_id=v.id, test_type=TestType.FORWARD, pnl=50)
    db_session.commit()
    bt = client.get("/api/trades/", params={"version_id": v.id, "test_type": "BACKTEST"}).json()
    fw = client.get("/api/trades/", params={"version_id": v.id, "test_type": "FORWARD"}).json()
    assert bt["total"] == 1
    assert fw["total"] == 1
    assert bt["trades"][0]["test_type"] == "backtest"
    assert fw["trades"][0]["test_type"] == "forward"


# ═════════════════════════════════════════════
# ۲. مراحل پراپ — مستقل
# ═════════════════════════════════════════════
def test_prop_stages_are_independent(client, db_session):
    s1 = _seed_stage(db_session, label="A", stage_type=StageType.STAGE_1)
    s2 = _seed_stage(db_session, label="B", stage_type=StageType.STAGE_2)
    for _ in range(4):
        _add_trade(db_session, prop_stage_id=s1.id, test_type=TestType.REAL, pnl=100)
    for _ in range(2):
        _add_trade(db_session, prop_stage_id=s2.id, test_type=TestType.REAL, pnl=50)
    db_session.commit()

    assert client.post(f"/api/analytics/analyze/prop/{s1.id}").status_code == 200
    assert client.post(f"/api/analytics/analyze/prop/{s2.id}").status_code == 200

    r1 = client.get(f"/api/analytics/analysis/prop/{s1.id}").json()
    r2 = client.get(f"/api/analytics/analysis/prop/{s2.id}").json()
    assert r1["total_trades"] == 4
    assert r2["total_trades"] == 2
    assert r1["prop_stage_id"] == s1.id
    assert r2["prop_stage_id"] == s2.id


def test_prop_stage_trades_endpoint(client, db_session):
    """جدول معاملات مرحله با prop_stage_id فیلتر می‌شود."""
    s1 = _seed_stage(db_session, label="A", stage_type=StageType.STAGE_1)
    s2 = _seed_stage(db_session, label="B", stage_type=StageType.STAGE_2)
    _add_trade(db_session, prop_stage_id=s1.id, test_type=TestType.REAL, pnl=100)
    _add_trade(db_session, prop_stage_id=s2.id, test_type=TestType.REAL, pnl=50)
    db_session.commit()
    r = client.get("/api/trades/", params={"prop_stage_id": s1.id}).json()
    assert r["total"] == 1


# ═════════════════════════════════════════════
# ۳. بروکر — فقط معاملات همان حساب
# ═════════════════════════════════════════════
def test_broker_analysis_uses_only_its_trades(client, db_session):
    b1 = Account(name="B1", type=AccountType.BROKER, currency=Currency.USD)
    b2 = Account(name="B2", type=AccountType.BROKER, currency=Currency.USD)
    db_session.add_all([b1, b2])
    db_session.commit()
    db_session.refresh(b1)
    db_session.refresh(b2)

    for _ in range(3):
        _add_trade(db_session, finance_account_id=b1.id, test_type=TestType.REAL, pnl=100)
    _add_trade(db_session, finance_account_id=b2.id, test_type=TestType.REAL, pnl=999)
    db_session.commit()

    assert client.post(f"/api/analytics/analyze/broker/{b1.id}").status_code == 200
    r = client.get(f"/api/analytics/analysis/broker/{b1.id}").json()
    assert r["total_trades"] == 3
    assert r["net_pnl"] == 300.0


def test_broker_trades_endpoint(client, db_session):
    """جدول معاملات بروکر با finance_account_id فیلتر می‌شود."""
    b1 = Account(name="B1", type=AccountType.BROKER, currency=Currency.USD)
    db_session.add(b1)
    db_session.commit()
    db_session.refresh(b1)
    _add_trade(db_session, finance_account_id=b1.id, test_type=TestType.REAL, pnl=100)
    db_session.commit()
    r = client.get("/api/trades/", params={"finance_account_id": b1.id}).json()
    assert r["total"] == 1
