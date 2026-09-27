"""تست‌های فاز ۲۵ (بخش ۲) — نادیده‌گرفتن معاملات Soft-Deleted در پراپ/مالی/تحلیل/گزارش.

سناریوی هر تست: یک معامله‌ی عادی + یک معامله‌ی حذف‌شده؛ انتظار می‌رود فقط
معامله‌ی عادی در خروجی‌ها دیده شود.
"""
from datetime import datetime, timezone

from app.models.strategy import (
    Trade, TradeSource, TestType, Strategy, StrategyVersion,
)
from app.models.prop import PropFirm, PropAccount, PropStage, StageType, StageStatus
from app.models.finance import Account, AccountType, Currency, Transaction
from app.services.analysis_service import AnalysisService
from app.services.prop_rule_engine import PropRuleEngine
from app.services.finance_sync_service import FinanceSyncService


def _trade(
    pnl=100.0,
    *,
    day=1,
    deleted=False,
    prop_stage_id=None,
    finance_account_id=None,
    version_id=None,
    source=TradeSource.MANUAL,
    test_type=TestType.BACKTEST,
):
    return Trade(
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 3, day, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 3, day, 11, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2000.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        source=source,
        test_type=test_type,
        prop_stage_id=prop_stage_id,
        finance_account_id=finance_account_id,
        version_id=version_id,
        is_deleted=deleted,
    )


def _seed_stage(db, stage_type=StageType.STAGE_1):
    firm = PropFirm(name="F")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="A1")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id,
        stage_type=stage_type,
        status=StageStatus.ACTIVE,
        initial_balance=10000.0,
    )
    db.add(stage)
    db.flush()
    return stage


# ═════════════════════════════════════════════
# پراپ (prop.py)
# ═════════════════════════════════════════════
def test_prop_stage_trades_excludes_deleted(client, db_session):
    stage = _seed_stage(db_session)
    db_session.add_all([
        _trade(100.0, prop_stage_id=stage.id),
        _trade(999.0, prop_stage_id=stage.id, deleted=True),
    ])
    db_session.commit()

    rows = client.get(f"/api/prop/stages/{stage.id}/trades").json()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 100.0


def test_prop_rule_engine_excludes_deleted(client, db_session):
    stage = _seed_stage(db_session)
    db_session.add_all([
        _trade(500.0, prop_stage_id=stage.id),
        _trade(-400.0, prop_stage_id=stage.id, deleted=True),
    ])
    db_session.commit()

    r = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert r["total_trades"] == 1
    assert r["current_profit"] == 500.0
    assert r["equity"] == 10500.0     # 10000 + 500 (حذف‌شده نادیده گرفته شد)


# ═════════════════════════════════════════════
# تحلیل (analysis_service.py)
# ═════════════════════════════════════════════
def test_analyze_prop_stage_excludes_deleted(client, db_session):
    stage = _seed_stage(db_session)
    db_session.add_all([
        _trade(100.0, prop_stage_id=stage.id),
        _trade(50.0, prop_stage_id=stage.id, deleted=True),
    ])
    db_session.commit()

    res = AnalysisService(db_session).analyze_prop_stage(stage.id)
    assert res["result"].total_trades == 1
    assert res["result"].net_pnl == 100.0


def test_analyze_broker_excludes_deleted(client, db_session):
    acct = Account(name="B", type=AccountType.BROKER, currency=Currency.USD)
    db_session.add(acct)
    db_session.flush()
    db_session.add_all([
        _trade(200.0, finance_account_id=acct.id),
        _trade(20.0, finance_account_id=acct.id, deleted=True),
    ])
    db_session.commit()

    res = AnalysisService(db_session).analyze_broker(acct.id)
    assert res["result"].total_trades == 1
    assert res["result"].net_pnl == 200.0


# ═════════════════════════════════════════════
# مالی (finance.py)
# ═════════════════════════════════════════════
def test_finance_real_pnl_excludes_deleted(client, db_session):
    broker_id = client.post("/api/finance/accounts", json={
        "name": "B", "type": "broker", "currency": "USD",
    }).json()["id"]
    stage = _seed_stage(db_session, StageType.FUNDED_REAL)

    db_session.add_all([
        _trade(100.0, prop_stage_id=stage.id),
        _trade(700.0, prop_stage_id=stage.id, deleted=True),
        _trade(300.0, finance_account_id=broker_id),
        _trade(900.0, finance_account_id=broker_id, deleted=True),
    ])
    db_session.commit()

    body = client.get("/api/finance/real-pnl").json()
    assert body["prop_stage_3"] == {"pnl": 100.0, "trades": 1}
    assert body["broker"] == {"pnl": 300.0, "trades": 1}
    assert body["total"] == {"pnl": 400.0, "trades": 2}


def test_finance_calendar_excludes_deleted(client, db_session):
    db_session.add_all([
        _trade(100.0),
        _trade(500.0, deleted=True),
    ])
    db_session.commit()

    days = client.get("/api/finance/financial-calendar").json()["days"]
    assert sum(d["trades"] for d in days) == 1
    assert sum(d["pnl"] for d in days) == 100.0


# ═════════════════════════════════════════════
# داشبورد/تقویم (analytics.py)
# ═════════════════════════════════════════════
def test_analytics_dashboard_excludes_deleted(client, db_session):
    db_session.add_all([
        _trade(100.0),
        _trade(500.0, deleted=True),
    ])
    db_session.commit()

    summary = client.get("/api/analytics/dashboard").json()["summary"]
    assert summary["total_trades"] == 1
    assert summary["net_pnl"] == 100.0


def test_analytics_calendar_excludes_deleted(client, db_session):
    db_session.add_all([
        _trade(100.0),
        _trade(500.0, deleted=True),
    ])
    db_session.commit()

    days = client.get("/api/analytics/calendar").json()
    assert sum(d["trade_count"] for d in days) == 1
    assert sum(d["total_pnl"] for d in days) == 100.0


# ═════════════════════════════════════════════
# همگام‌سازی مالی (finance_sync_service.py)
# ═════════════════════════════════════════════
def test_finance_sync_skips_deleted(client, db_session):
    broker_id = client.post("/api/finance/accounts", json={
        "name": "B", "type": "broker", "currency": "USD",
    }).json()["id"]

    db_session.add_all([
        _trade(100.0, finance_account_id=broker_id),
        _trade(200.0, finance_account_id=broker_id, deleted=True),
    ])
    db_session.commit()

    created = FinanceSyncService(db_session).sync_closed_trades()
    assert created == 1
    txs = db_session.query(Transaction).filter(
        Transaction.related_trade_id.isnot(None)
    ).all()
    assert len(txs) == 1
    assert txs[0].amount == 100.0


# ═════════════════════════════════════════════
# استراتژی (strategies.py) — شمارش/لیست معاملات نسخه
# ═════════════════════════════════════════════
def test_strategies_trades_count_excludes_deleted(client, db_session):
    s = Strategy(name="S1")
    db_session.add(s)
    db_session.flush()
    v = StrategyVersion(strategy_id=s.id, version_name="v1")
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)

    db_session.add_all([
        _trade(100.0, version_id=v.id),
        _trade(50.0, version_id=v.id, deleted=True),
    ])
    db_session.commit()

    versions = client.get("/api/strategies/versions/all").json()
    row = next(x for x in versions if x["id"] == v.id)
    assert row["trades_count"] == 1


def test_version_trades_excludes_deleted(client, db_session):
    s = Strategy(name="S2")
    db_session.add(s)
    db_session.flush()
    v = StrategyVersion(strategy_id=s.id, version_name="v1")
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)

    db_session.add_all([
        _trade(100.0, version_id=v.id),
        _trade(50.0, version_id=v.id, deleted=True),
    ])
    db_session.commit()

    rows = client.get(f"/api/strategies/versions/{v.id}/trades").json()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 100.0
