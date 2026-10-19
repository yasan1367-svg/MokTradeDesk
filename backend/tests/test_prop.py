"""تست‌های PropRuleEngine و endpointهای پراپ (فاز ۱۲)"""
from datetime import datetime, timezone

import pytest

from app.models.prop import (
    PropFirm, PropAccount, PropStage, StageType, StageStatus,
)
from app.models.strategy import Trade, TradeSource, TestType, Strategy, StrategyVersion
from app.services.prop_rule_engine import PropRuleEngine


def _version(db, name="v1"):
    """نسخه‌ی استراتژی (version_id اکنون اجباری است — فاز ۲۸)"""
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.flush()
    return v


def _trade(pnl, close_day, stage_id=None, version_id=None):
    return Trade(
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, close_day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, close_day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2000.0,
        size=1.0,
        pnl=pnl,
        source=TradeSource.MANUAL,
        test_type=TestType.REAL_PROP,
        prop_stage_id=stage_id,
        version_id=version_id,
    )


def _make_stage(
    db,
    *,
    stage_type=StageType.STAGE_1,
    profit_target=1000.0,
    max_daily_dd=500.0,
    max_total_dd=1000.0,
    min_days=3,
    initial=10000.0,
    profit_share=80.0,
    total_withdrawn=0.0,
):
    firm = PropFirm(name="FTMO")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="A1")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id,
        stage_type=stage_type,
        status=StageStatus.ACTIVE,
        initial_balance=initial,
        profit_target=profit_target,
        max_daily_dd=max_daily_dd,
        max_total_dd=max_total_dd,
        min_trading_days=min_days,
        profit_share_percentage=profit_share,
        total_withdrawn=total_withdrawn,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


# ═════════════════════════════════════════════
# کمک‌تابع‌های داخلی
# ═════════════════════════════════════════════
def test_group_daily_pnl():
    trades = [_trade(100, 1), _trade(50, 1), _trade(-30, 2)]
    daily = PropRuleEngine._group_daily_pnl(trades)
    assert daily["2025-01-01"] == 150
    assert daily["2025-01-02"] == -30


def test_calculate_max_drawdown():
    trades = [_trade(500, 1), _trade(-800, 2), _trade(200, 3)]
    assert PropRuleEngine._calculate_max_drawdown(trades, 10000) == 800.0


# ═════════════════════════════════════════════
# evaluate_stage
# ═════════════════════════════════════════════
def test_evaluate_stage_no_trades(db_session):
    stage = _make_stage(db_session)
    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["ready_to_pass"] is False
    assert res["trading_days"] == 0
    assert res["suggested_status"] == "in_progress"


def test_evaluate_stage_ready_to_pass(db_session):
    stage = _make_stage(db_session, profit_target=1000.0, min_days=2)
    v = _version(db_session)
    for d, p in [(1, 600), (2, 500), (3, 400)]:
        db_session.add(_trade(p, d, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["ready_to_pass"] is True
    assert res["suggested_status"] == "ready_to_pass"
    assert res["current_profit"] == 1500.0


def test_evaluate_stage_daily_dd_violation(db_session):
    stage = _make_stage(db_session, max_daily_dd=500.0)
    v = _version(db_session)
    db_session.add(_trade(-700, 1, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["daily_dd_violated"] is True
    assert res["suggested_status"] == "failed_daily_dd"


def test_evaluate_stage_missing(db_session):
    res = PropRuleEngine.evaluate_stage(db_session, 99999)
    assert "error" in res
    assert res["ready_to_pass"] is False


# ═════════════════════════════════════════════
# validate_withdrawal
# ═════════════════════════════════════════════
def test_validate_withdrawal_not_funded(db_session):
    stage = _make_stage(db_session, stage_type=StageType.STAGE_1)
    ok, msg = PropRuleEngine.validate_withdrawal(db_session, stage.id, 100)
    assert ok is False
    assert "رییل" in msg


def test_validate_withdrawal_positive_amount(db_session):
    ok, msg = PropRuleEngine.validate_withdrawal(db_session, 1, -5)
    assert ok is False


def test_funded_withdrawable_profit(db_session):
    stage = _make_stage(
        db_session, stage_type=StageType.FUNDED_REAL,
        profit_share=80.0, total_withdrawn=100.0,
    )
    v = _version(db_session)
    for d, p in [(1, 1000), (2, 500)]:
        db_session.add(_trade(p, d, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["is_funded"] is True
    assert res["ready_to_pass"] is False
    # user_share = 1500 * 0.8 = 1200 ; minus withdrawn 100 = 1100
    assert res["withdrawable_profit"] == pytest.approx(1100.0)

    assert PropRuleEngine.validate_withdrawal(db_session, stage.id, 1000)[0] is True
    assert PropRuleEngine.validate_withdrawal(db_session, stage.id, 2000)[0] is False


# ═════════════════════════════════════════════
# Endpointها
# ═════════════════════════════════════════════
def test_prop_firm_and_account_endpoints(client):
    r = client.post("/api/prop/firms", json={"name": "FTMO"})
    assert r.status_code == 200

    firms = client.get("/api/prop/firms").json()
    assert len(firms) == 1
    assert firms[0]["name"] == "FTMO"

    acc = client.post("/api/prop/accounts", json={
        "prop_firm_id": firms[0]["id"],
        "account_label": "A1",
        "initial_balance": 10000,
    })
    assert acc.status_code == 200

    accounts = client.get("/api/prop/accounts").json()
    assert len(accounts) == 1
    assert accounts[0]["account_label"] == "A1"
