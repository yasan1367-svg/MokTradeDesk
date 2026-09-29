"""تست‌های فاز ۲۵ (بخش ۲) — نادیده‌گرفتن معاملات Soft-Deleted در پراپ/مالی/تحلیل/گزارش.

سناریوی هر تست: یک معامله‌ی عادی + یک معامله‌ی حذف‌شده؛ انتظار می‌رود فقط
معامله‌ی عادی در خروجی‌ها دیده شود.
"""
from datetime import datetime, timezone

from app.models.strategy import (
    Trade, TradeSource, TestType, Strategy, StrategyVersion,
)
from app.models.prop import PropFirm, PropAccount, PropStage, StageType, StageStatus
from app.models.finance import Currency
from app.models.trading import Broker, PersonalTradingAccount
from app.services.analysis_service import AnalysisService
from app.services.prop_rule_engine import PropRuleEngine
from app.services.finance_sync_service import FinanceSyncService


def _version(db, name="v1"):
    """نسخه‌ی استراتژی مشترک (version_id اکنون اجباری است — فاز ۲۸)"""
    v = db.query(StrategyVersion).first()
    if v:
        return v
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.flush()
    return v


def _pta(db, label="PTA"):
    """حساب معاملاتی شخصی مشترک (فاز ۲۸)"""
    existing = db.query(PersonalTradingAccount).first()
    if existing:
        return existing
    broker = Broker(name=f"Broker-{label}")
    db.add(broker)
    db.flush()
    pta = PersonalTradingAccount(
        broker_id=broker.id, account_number=f"ACC-{label}", account_label=label,
        currency=Currency.USD, initial_balance=10000.0, current_balance=10000.0,
    )
    db.add(pta)
    db.flush()
    return pta


def _trade(
    db,
    pnl=100.0,
    *,
    day=1,
    deleted=False,
    prop_stage_id=None,
    personal_trading_account_id=None,
    version_id=None,
    source=TradeSource.MANUAL,
    test_type=None,
):
    """معامله‌ی تست با test_type استنتاج‌شده از دامنه (فاز ۲۸)"""
    if version_id is None:
        version_id = _version(db).id
    if test_type is None:
        if prop_stage_id is not None:
            test_type = TestType.REAL_PROP
        elif personal_trading_account_id is not None:
            test_type = TestType.REAL_PERSONAL
        else:
            test_type = TestType.BACKTEST
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
        personal_trading_account_id=personal_trading_account_id,
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
        _trade(db_session, 100.0, prop_stage_id=stage.id),
        _trade(db_session, 999.0, prop_stage_id=stage.id, deleted=True),
    ])
    db_session.commit()

    rows = client.get(f"/api/prop/stages/{stage.id}/trades").json()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 100.0


def test_prop_rule_engine_excludes_deleted(client, db_session):
    stage = _seed_stage(db_session)
    db_session.add_all([
        _trade(db_session, 500.0, prop_stage_id=stage.id),
        _trade(db_session, -400.0, prop_stage_id=stage.id, deleted=True),
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
        _trade(db_session, 100.0, prop_stage_id=stage.id),
        _trade(db_session, 50.0, prop_stage_id=stage.id, deleted=True),
    ])
    db_session.commit()

    res = AnalysisService(db_session).analyze_prop_stage(stage.id)
    assert res["result"].total_trades == 1
    assert res["result"].net_pnl == 100.0


def test_analyze_personal_account_excludes_deleted(client, db_session):
    pta = _pta(db_session)
    db_session.flush()
    db_session.add_all([
        _trade(db_session, 200.0, personal_trading_account_id=pta.id),
        _trade(db_session, 20.0, personal_trading_account_id=pta.id, deleted=True),
    ])
    db_session.commit()

    res = AnalysisService(db_session).analyze_personal_account(pta.id)
    assert res["result"].total_trades == 1
    assert res["result"].net_pnl == 200.0


# ═════════════════════════════════════════════
# مالی (finance.py)
# ═════════════════════════════════════════════
def test_finance_real_pnl_excludes_deleted(client, db_session):
    pta = _pta(db_session)
    stage = _seed_stage(db_session, StageType.FUNDED_REAL)
    db_session.flush()

    db_session.add_all([
        _trade(db_session, 100.0, prop_stage_id=stage.id),
        _trade(db_session, 700.0, prop_stage_id=stage.id, deleted=True),
        _trade(db_session, 300.0, personal_trading_account_id=pta.id),
        _trade(db_session, 900.0, personal_trading_account_id=pta.id, deleted=True),
    ])
    db_session.commit()

    body = client.get("/api/finance/real-pnl").json()
    assert body["prop_stage_3"] == {"pnl": 100.0, "trades": 1}
    assert body["broker"] == {"pnl": 300.0, "trades": 1}
    assert body["total"] == {"pnl": 400.0, "trades": 2}


def test_finance_calendar_excludes_deleted(client, db_session):
    db_session.add_all([
        _trade(db_session, 100.0),
        _trade(db_session, 500.0, deleted=True),
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
        _trade(db_session, 100.0),
        _trade(db_session, 500.0, deleted=True),
    ])
    db_session.commit()

    summary = client.get("/api/analytics/dashboard").json()["summary"]
    assert summary["total_trades"] == 1
    assert summary["net_pnl"] == 100.0


def test_analytics_calendar_excludes_deleted(client, db_session):
    db_session.add_all([
        _trade(db_session, 100.0),
        _trade(db_session, 500.0, deleted=True),
    ])
    db_session.commit()

    days = client.get("/api/analytics/calendar").json()
    assert sum(d["trade_count"] for d in days) == 1
    assert sum(d["total_pnl"] for d in days) == 100.0


# ═════════════════════════════════════════════
# همگام‌سازی مالی (finance_sync_service.py)
# ═════════════════════════════════════════════
def test_finance_sync_is_noop_after_bridge_removal(client, db_session):
    """فاز ۲۸: پل Trade→Finance حذف شد؛ sync_closed_trades هیچ FinancialTransaction نمی‌سازد."""
    pta = _pta(db_session)
    db_session.flush()
    db_session.add_all([
        _trade(db_session, 100.0, personal_trading_account_id=pta.id),
        _trade(db_session, 200.0, personal_trading_account_id=pta.id, deleted=True),
    ])
    db_session.commit()

    created = FinanceSyncService(db_session).sync_closed_trades()
    assert created == 0


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
        _trade(db_session, 100.0, version_id=v.id),
        _trade(db_session, 50.0, version_id=v.id, deleted=True),
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
        _trade(db_session, 100.0, version_id=v.id),
        _trade(db_session, 50.0, version_id=v.id, deleted=True),
    ])
    db_session.commit()

    rows = client.get(f"/api/strategies/versions/{v.id}/trades").json()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 100.0
