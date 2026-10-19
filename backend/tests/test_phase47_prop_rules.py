"""تست‌های فاز ۴۷ — موتور قوانین پراپ و برداشت."""
from datetime import datetime, timezone

import pytest

from app.models.prop import PropAccount, PropFirm, PropStage, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.services.prop_rule_engine import PropRuleEngine


def _stage(db, **kw):
    """مرحلهٔ پراپ ساده برای تست."""
    firm = PropFirm(name="F47")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="A47")
    db.add(account)
    db.flush()
    stage = PropStage(prop_account_id=account.id, stage_type=StageType.STAGE_1, **kw)
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


def _version(db, name="v47"):
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.flush()
    return v


def _trade(version_id, stage_id, pnl, *, day=None, hour=10, minute=0, close=True):
    """یک معاملهٔ بستهٔ نهایی‌شده روی مرحلهٔ پراپ (فاز ۴۷.۲)."""
    when = day or datetime(2025, 1, 1, hour, minute, tzinfo=timezone.utc)
    return Trade(
        version_id=version_id,
        prop_stage_id=stage_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=when,
        close_time=when if close else None,
        open_price=2000.0,
        close_price=2000.0,
        size=1.0,
        pnl=pnl,
        source=TradeSource.MANUAL,
        test_type=TestType.REAL_PROP,
    )



# ═════════════════════════════════════════════
# ۴۷.۱ — ستون‌های DD روی PropStage
# ═════════════════════════════════════════════
def test_prop_stage_default_dd_mode_static(db_session):
    assert _stage(db_session).dd_mode == "static"


def test_prop_stage_new_drawdown_defaults(db_session):
    stage = _stage(db_session)
    assert stage.dd_basis == "balance"
    assert stage.daily_dd_mode == "static"
    assert stage.total_dd_mode == "static"


def test_prop_stage_default_day_boundary_utc(db_session):
    assert _stage(db_session).day_boundary_utc_offset == 0


# ═════════════════════════════════════════════
# ۴۷a.۱ — Total DD ساده: static + balance
# ═════════════════════════════════════════════
def test_static_dd_simple(db_session):
    """۳ ترید: 10000 → 10500 → 10200 → 10800.

    static DD = افت از موجودی اولیه = max(0, initial − min_equity).
    `min_equity` شامل نقطهٔ شروع است ⇒ min = 10000 (نه 10200) ⇒ **DD = 0**
    (چون هرگز زیر ۱۰۰۰۰ نرفته). کف ثابت = 10000 − 1000 = 9000.
    """
    v = _version(db_session)
    stage = _stage(
        db_session,
        initial_balance=10000.0,
        profit_target=1000.0,
        max_daily_dd=500.0,
        max_total_dd=1000.0,
    )
    db_session.add_all([
        _trade(v.id, stage.id, 500.0, day=datetime(2025, 1, 1, 10, tzinfo=timezone.utc)),
        _trade(v.id, stage.id, -300.0, day=datetime(2025, 1, 2, 10, tzinfo=timezone.utc)),
        _trade(v.id, stage.id, 600.0, day=datetime(2025, 1, 3, 10, tzinfo=timezone.utc)),
    ])
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["equity"] == pytest.approx(10800.0)
    assert res["max_total_dd"] == pytest.approx(0.0)       # هرگز زیر ۱۰۰۰۰ نرفته
    assert res["equity_floor"] == pytest.approx(9000.0)    # 10000 − 1000
    assert res["total_dd_violated"] is False


def test_static_dd_violated(db_session):
    """افت زیر کف ثابت ⇒ نقض Total DD."""
    v = _version(db_session)
    stage = _stage(
        db_session,
        initial_balance=10000.0,
        profit_target=1000.0,
        max_daily_dd=2000.0,   # تا Daily DD نقض نشود (اولویت روزانه)
        max_total_dd=1000.0,
    )
    db_session.add(_trade(
        v.id, stage.id, -1200.0, day=datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    ))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["max_total_dd"] == pytest.approx(1200.0)
    assert res["equity_floor"] == pytest.approx(9000.0)
    assert res["total_dd_violated"] is True
    assert res["suggested_status"] == "failed_total_dd"


def test_static_dd_no_violation(db_session):
    """افت داخل کف ثابت ⇒ بدون نقض."""
    v = _version(db_session)
    stage = _stage(
        db_session,
        initial_balance=10000.0,
        profit_target=1000.0,
        max_daily_dd=1000.0,
        max_total_dd=1000.0,
    )
    db_session.add(_trade(
        v.id, stage.id, -800.0, day=datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    ))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["max_total_dd"] == pytest.approx(800.0)
    assert res["total_dd_violated"] is False


# ═════════════════════════════════════════════
# ۴۷.۲ — Daily DD و مرز روز
# ═════════════════════════════════════════════
def test_group_daily_pnl_respects_offset():
    """۲۳:۳۰ و ۰۰:۳۰ UTC با offset=+120 دقیقه در یک روز ادغام می‌شوند."""
    a = _trade(1, 1, -300.0, day=datetime(2025, 1, 1, 23, 30, tzinfo=timezone.utc))
    b = _trade(1, 1, -200.0, day=datetime(2025, 1, 2, 0, 30, tzinfo=timezone.utc))

    assert PropRuleEngine._group_daily_pnl([a, b], 0) == {
        "2025-01-01": -300.0,
        "2025-01-02": -200.0,
    }
    assert PropRuleEngine._group_daily_pnl([a, b], 120) == {"2025-01-02": -500.0}


def test_daily_dd_uses_day_boundary(db_session):
    """مرز روز (day_boundary_utc_offset) روی max_daily_loss اثر می‌گذارد."""
    v = _version(db_session)

    def _eval(offset):
        stage = _stage(
            db_session,
            initial_balance=10000.0,
            profit_target=1000.0,
            max_daily_dd=400.0,
            max_total_dd=5000.0,
            day_boundary_utc_offset=offset,
        )
        db_session.add_all([
            _trade(v.id, stage.id, -300.0, day=datetime(2025, 1, 1, 23, 30, tzinfo=timezone.utc)),
            _trade(v.id, stage.id, -200.0, day=datetime(2025, 1, 2, 0, 30, tzinfo=timezone.utc)),
        ])
        db_session.commit()
        return PropRuleEngine.evaluate_stage(db_session, stage.id)

    midnight = _eval(0)
    assert midnight["max_daily_loss"] == pytest.approx(300.0)
    assert midnight["trading_days"] == 2
    assert midnight["daily_dd_violated"] is False  # 300 ≤ 400

    shifted = _eval(120)
    assert shifted["max_daily_loss"] == pytest.approx(500.0)
    assert shifted["trading_days"] == 1
    assert shifted["daily_dd_violated"] is True   # 500 > 400


# ═════════════════════════════════════════════
# ۴۷a.۲ — Fail-closed: نبودِ حد = unconfigured
# ═════════════════════════════════════════════
def test_unconfigured_stage_not_ready_to_pass(db_session):
    """مرحلهٔ بدون هیچ حدی نباید «آمادهٔ پاس» شود (fail-closed)."""
    stage = _stage(db_session, initial_balance=10000.0)  # بدون هدف/حد
    v = _version(db_session)
    # حتی با سود بزرگ در ۵ روز معاملاتی
    for d in range(1, 6):
        db_session.add(_trade(
            v.id, stage.id, 500.0, day=datetime(2025, 1, d, 10, tzinfo=timezone.utc)
        ))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["unconfigured"] is True
    assert res["ready_to_pass"] is False
    assert res["suggested_status"] == "unconfigured"


def test_stage_with_no_limits_warns(db_session):
    """نبودِ هر حد یک پیام هشدار در violations می‌گذارد."""
    stage = _stage(db_session, initial_balance=10000.0)
    res = PropRuleEngine.evaluate_stage(db_session, stage.id)

    assert res["unconfigured"] is True
    assert any("Daily DD" in m for m in res["violations"])
    assert any("Max DD" in m for m in res["violations"])
    assert any("هدف سود" in m for m in res["violations"])


def test_equity_basis_includes_floating_loss_and_blocks_pass(db_session):
    from app.models.prop import RuleType, Severity

    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=100, max_daily_dd=500,
        max_total_dd=1000, min_trading_days=0, dd_basis="equity",
    )
    db_session.add(_trade(version.id, stage.id, -1200, close=False))
    db_session.commit()
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    equity_check = next(c for c in result["rule_checks"] if c["rule_type"] == RuleType.EQUITY_BALANCE)
    floating_check = next(c for c in result["rule_checks"] if c["rule_type"] == RuleType.FLOATING_PNL)
    assert result["equity"] == pytest.approx(8800)
    assert equity_check["severity"] == Severity.VIOLATION
    assert floating_check["severity"] == Severity.VIOLATION
    assert result["ready_to_pass"] is False


def test_balance_basis_ignores_floating_for_drawdown_and_pass(db_session):
    from app.models.prop import RuleType, Severity

    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=100, max_daily_dd=500,
        max_total_dd=1000, min_trading_days=0, dd_basis="balance",
    )
    db_session.add(_trade(version.id, stage.id, -1200, close=False))
    db_session.commit()
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = {c["rule_type"]: c for c in result["rule_checks"]}
    assert result["equity"] == pytest.approx(8800)
    assert result["balance"] == pytest.approx(10000)
    assert checks[RuleType.FLOATING_PNL]["severity"] == Severity.PASS
    assert result["max_total_dd"] == pytest.approx(0)
    assert result["ready_to_pass"] is False  # Profit target has not been reached.


@pytest.mark.parametrize("mode,expected", [("static", 0), ("trailing", 300)])
def test_daily_drawdown_modes(mode, expected, db_session):
    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=1000, max_daily_dd=1000,
        max_total_dd=5000, min_trading_days=0, daily_dd_mode=mode, dd_basis="equity",
    )
    db_session.add_all([
        _trade(version.id, stage.id, 500, day=datetime(2025, 1, 1, 9, tzinfo=timezone.utc)),
        _trade(version.id, stage.id, -300, day=datetime(2025, 1, 1, 10, tzinfo=timezone.utc)),
    ])
    db_session.commit()
    assert PropRuleEngine.evaluate_stage(db_session, stage.id)["max_daily_loss"] == pytest.approx(expected)


@pytest.mark.parametrize("mode,expected", [("static", 0), ("trailing", 300)])
def test_total_drawdown_modes(mode, expected, db_session):
    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=1000, max_daily_dd=5000,
        max_total_dd=1000, min_trading_days=0, total_dd_mode=mode,
    )
    db_session.add_all([
        _trade(version.id, stage.id, 500, day=datetime(2025, 1, 1, 9, tzinfo=timezone.utc)),
        _trade(version.id, stage.id, -300, day=datetime(2025, 1, 2, 9, tzinfo=timezone.utc)),
    ])
    db_session.commit()
    assert PropRuleEngine.evaluate_stage(db_session, stage.id)["max_total_dd"] == pytest.approx(expected)


def test_ready_to_pass_requires_target_days_and_no_violations(db_session):
    from app.models.prop import StageStatus

    stage = _stage(
        db_session, initial_balance=10000, profit_target=100, max_daily_dd=500,
        max_total_dd=1000, min_trading_days=0,
    )
    stage.status = StageStatus.FAILED
    db_session.commit()
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    # Historical stage: ready_to_pass is None, not False
    assert result["ready_to_pass"] is None
    # No DD violations, so overall_severity should be "pass"
    assert result["overall_severity"] == "pass"
    assert result["is_historical"] is True


def test_invalid_mode_fails_closed(db_session):
    stage = _stage(
        db_session, initial_balance=10000, profit_target=100, max_daily_dd=500,
        max_total_dd=1000, daily_dd_mode="unsupported",
    )
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert result["unconfigured"] is True
    assert result["ready_to_pass"] is False


def test_ready_to_pass_is_false_until_profit_target_reached(db_session):
    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=500, max_daily_dd=1000,
        max_total_dd=2000, min_trading_days=0,
    )
    db_session.add(_trade(version.id, stage.id, 499))
    db_session.commit()
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert result["target_reached"] is False
    assert result["ready_to_pass"] is False


def test_ready_to_pass_is_false_until_minimum_days_reached(db_session):
    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=100, max_daily_dd=500,
        max_total_dd=1000, min_trading_days=2,
    )
    db_session.add(_trade(version.id, stage.id, 500))
    db_session.commit()
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert result["target_reached"] is True
    assert result["days_met"] is False
    assert result["ready_to_pass"] is False


def test_equity_basis_open_floating_drawdown_fails_total_rule(db_session):
    from app.models.prop import RuleType, Severity

    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=500, max_daily_dd=2000,
        max_total_dd=1000, min_trading_days=0, dd_basis="equity",
    )
    db_session.add(_trade(version.id, stage.id, -1200, close=False))
    db_session.commit()
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = {check["rule_type"]: check for check in result["rule_checks"]}
    assert result["max_total_dd"] == pytest.approx(1200)
    assert result["total_dd_violated"] is True
    assert checks[RuleType.MAX_DRAWDOWN]["severity"] == Severity.VIOLATION


def test_equity_basis_open_floating_loss_counts_daily_dd(db_session):
    version = _version(db_session)
    stage = _stage(
        db_session, initial_balance=10000, profit_target=500, max_daily_dd=500,
        max_total_dd=2000, min_trading_days=0, dd_basis="equity",
    )
    db_session.add(_trade(version.id, stage.id, -700, close=False))
    db_session.commit()
    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert result["max_daily_loss"] == pytest.approx(700)
    assert result["daily_dd_violated"] is True

