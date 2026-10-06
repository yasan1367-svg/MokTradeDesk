"""تست‌های Phase 5-PARTIAL-FINAL — قوانین برای مراحل تاریخی (تکمیل‌شده).

پوشش:
- STAGE_STATUS نباید VIOLATION برگرداند برای مراحل PASSED/FAILED/CLOSED
- PROFIT_TARGET و MIN_TRADING_DAYS باید PASS باشند برای مراحل تاریخی
- ready_to_pass باید None باشد برای مراحل تاریخی
- overall_severity بر اساس فقط قوانین DD محاسبه شود (نه STAGE_STATUS)
- is_historical در خروجی وجود داشته باشد
- مرحله فعال هنوز رفتار قبلی دارد
- pass_stage 409 برگرداند برای مراحل غیرفعال
"""
from datetime import datetime, timezone

import pytest

from app.models.prop import (
    PropFirm, PropAccount, PropStage, StageType, StageStatus,
    RuleType, Severity,
)
from app.models.strategy import Trade, TradeSource, TestType, Strategy, StrategyVersion
from app.services.prop_rule_engine import PropRuleEngine


def _version(db, name="hist"):
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


def _make_stage(db, **kw):
    defaults = dict(
        stage_type=StageType.STAGE_1,
        status=StageStatus.ACTIVE,
        profit_target=1000.0,
        max_daily_dd=500.0,
        max_total_dd=1000.0,
        min_trading_days=3,
        initial=10000.0,
    )
    defaults.update(kw)
    firm = PropFirm(name="HIST_FIRM")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="HIST_ACC")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id,
        stage_type=defaults["stage_type"],
        status=defaults["status"],
        initial_balance=defaults["initial"],
        profit_target=defaults["profit_target"],
        max_daily_dd=defaults["max_daily_dd"],
        max_total_dd=defaults["max_total_dd"],
        min_trading_days=defaults["min_trading_days"],
        profit_share_percentage=defaults.get("profit_share", 80.0),
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


def _check_map(evaluation):
    return {c["rule_type"]: c for c in evaluation["rule_checks"]}
# ═════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════

def test_historical_stage_has_no_stage_status_violation(db_session):
    """For a FAILED/PASSED/CLOSED stage, STAGE_STATUS must be PASS, not VIOLATION."""
    for status in (StageStatus.FAILED, StageStatus.PASSED, StageStatus.CLOSED):
        stage = _make_stage(db_session, status=status)
        res = PropRuleEngine.evaluate_stage(db_session, stage.id)
        checks = _check_map(res)
        assert checks[RuleType.STAGE_STATUS]["severity"] == Severity.PASS, \
            f"STAGE_STATUS should be PASS for {status.value}, got {checks[RuleType.STAGE_STATUS]['severity']}"
        assert res["is_historical"] is True, f"is_historical should be True for {status.value}"


def test_historical_stage_profit_target_is_pass(db_session):
    """For a historical stage, PROFIT_TARGET must be PASS even when profit < target."""
    stage = _make_stage(db_session, status=StageStatus.PASSED, profit_target=5000.0)
    v = _version(db_session)
    db_session.add(_trade(100, 1, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)
    assert checks[RuleType.PROFIT_TARGET]["severity"] == Severity.PASS, \
        "PROFIT_TARGET should be PASS for historical stage even if target not met"
    assert checks[RuleType.PROFIT_TARGET]["message"] == "برای مراحل تکمیل‌شده بی‌ربط"


def test_historical_stage_min_days_is_pass(db_session):
    """For a historical stage, MIN_TRADING_DAYS must be PASS even when days < min."""
    stage = _make_stage(db_session, status=StageStatus.FAILED, min_days=10)
    v = _version(db_session)
    db_session.add(_trade(100, 1, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)
    assert checks[RuleType.MIN_TRADING_DAYS]["severity"] == Severity.PASS, \
        "MIN_TRADING_DAYS should be PASS for historical stage even if days < min"
    assert checks[RuleType.MIN_TRADING_DAYS]["message"] == "برای مراحل تکمیل‌شده بی‌ربط"


def test_historical_stage_ready_to_pass_is_none(db_session):
    """For a historical stage, ready_to_pass must be None, not False."""
    stage = _make_stage(db_session, status=StageStatus.PASSED)
    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["ready_to_pass"] is None, \
        f"ready_to_pass should be None for historical stage, got {res['ready_to_pass']}"
    assert res["suggested_status"] == "passed"
    assert res["is_historical"] is True


def test_active_stage_behavior_unchanged(db_session):
    """An ACTIVE stage must still have the original behavior."""
    stage = _make_stage(db_session, status=StageStatus.ACTIVE)
    v = _version(db_session)
    db_session.add(_trade(100, 1, stage.id, v.id))
    db_session.add(_trade(200, 2, stage.id, v.id))
    db_session.add(_trade(-300, 3, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)

    assert checks[RuleType.STAGE_STATUS]["severity"] == Severity.PASS
    # 300 profit < 1000 target → WARNING
    assert checks[RuleType.PROFIT_TARGET]["severity"] == Severity.WARNING
    # 3 days >= 3 min → PASS
    assert checks[RuleType.MIN_TRADING_DAYS]["severity"] == Severity.PASS
    # max_daily_loss = 300, limit = 500 → PASS (< 80%)
    assert checks[RuleType.DAILY_DRAWDOWN]["severity"] == Severity.PASS
    # target not reached → ready_to_pass is False
    assert res["ready_to_pass"] is False
    assert res["is_historical"] is False


def test_pass_stage_on_historical_returns_409(client, db_session):
    """POST /stages/{id}/pass for a non-ACTIVE stage must return 409."""
    stage = _make_stage(db_session, status=StageStatus.PASSED)
    db_session.commit()

    response = client.post(
        f"/api/prop/stages/{stage.id}/pass",
        json={"final_balance": 10000},
    )
    assert response.status_code == 409, \
        f"Expected 409 for passing a historical stage, got {response.status_code}"
    assert "فعال نیست" in response.json()["detail"]