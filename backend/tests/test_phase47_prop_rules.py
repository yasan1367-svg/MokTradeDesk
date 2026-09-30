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

