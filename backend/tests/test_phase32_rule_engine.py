"""تست‌های Phase 32 — Prop Rule Engine (RuleViolation / Rule Evaluation).

پوشش:
- تولید `rule_checks` برای هر ۷ RuleType
- نگاشت Severity (PASS / WARNING / VIOLATION)
- ثبت در `rule_violations` و تاریخچه
- endpointهای `/evaluate` و `/violations`
"""
from datetime import datetime, timezone


from app.models.prop import (
    PropFirm, PropAccount, PropStage, StageType, StageStatus,
    RuleType, Severity, RuleViolation,
)
from app.models.strategy import Trade, TradeSource, TestType, Strategy, StrategyVersion
from app.services.prop_rule_engine import PropRuleEngine


def _version(db, name="v1"):
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.flush()
    return v


def _trade(pnl, close_day, stage_id=None, version_id=None, close_time=True):
    return Trade(
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, close_day, 9, 0, tzinfo=timezone.utc),
        close_time=(
            datetime(2025, 1, close_day, 10, 0, tzinfo=timezone.utc)
            if close_time
            else None
        ),
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
    status=StageStatus.ACTIVE,
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
        status=status,
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


def _check_map(evaluation):
    return {c["rule_type"]: c for c in evaluation["rule_checks"]}


# ═════════════════════════════════════════════
# rule_checks
# ═════════════════════════════════════════════
def test_rule_checks_cover_all_rule_types(db_session):
    stage = _make_stage(db_session)
    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    kinds = {c["rule_type"] for c in res["rule_checks"]}
    assert kinds == set(RuleType)
    assert len(res["rule_checks"]) == len(list(RuleType))


def test_rule_checks_healthy_stage_all_pass(db_session):
    stage = _make_stage(db_session, profit_target=1000.0, min_days=3)
    v = _version(db_session)
    for d, p in [(1, 600), (2, 500), (3, 100)]:
        db_session.add(_trade(p, d, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["ready_to_pass"] is True
    assert res["overall_severity"] == Severity.PASS.value
    for c in res["rule_checks"]:
        assert c["severity"] == Severity.PASS, c


def test_daily_drawdown_violation(db_session):
    stage = _make_stage(db_session, max_daily_dd=500.0)
    v = _version(db_session)
    db_session.add(_trade(-700, 1, stage.id, v.id))
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)
    assert checks[RuleType.DAILY_DRAWDOWN]["severity"] == Severity.VIOLATION
    assert res["overall_severity"] == Severity.VIOLATION.value


def test_daily_drawdown_warning_near_limit(db_session):
    stage = _make_stage(db_session, max_daily_dd=500.0)
    v = _version(db_session)
    db_session.add(_trade(-420, 1, stage.id, v.id))  # 84% از حد
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)
    assert checks[RuleType.DAILY_DRAWDOWN]["severity"] == Severity.WARNING
    assert res["overall_severity"] == Severity.WARNING.value


def test_profit_target_and_min_days_warning(db_session):
    stage = _make_stage(db_session, profit_target=1000.0, min_days=3)
    v = _version(db_session)
    db_session.add(_trade(950, 1, stage.id, v.id))  # 95% هدف، ۱ روز < ۳
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)
    assert checks[RuleType.PROFIT_TARGET]["severity"] == Severity.WARNING
    assert checks[RuleType.MIN_TRADING_DAYS]["severity"] == Severity.WARNING
    assert res["overall_severity"] == Severity.WARNING.value


def test_stage_status_rule_violation_on_terminal(db_session):
    stage = _make_stage(db_session, status=StageStatus.FAILED)
    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)
    assert checks[RuleType.STAGE_STATUS]["severity"] == Severity.VIOLATION
    assert checks[RuleType.STAGE_STATUS]["actual_value"] == 0.0


def test_floating_pnl_uses_open_trades(db_session):
    stage = _make_stage(db_session, max_daily_dd=500.0)
    v = _version(db_session)
    db_session.add(_trade(-300, 1, stage.id, v.id, close_time=False))  # باز
    db_session.commit()

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    checks = _check_map(res)
    assert checks[RuleType.FLOATING_PNL]["actual_value"] == 300.0
    assert res["floating_pnl"] == -300.0


# ═════════════════════════════════════════════
# persistence
# ═════════════════════════════════════════════
def test_record_violations_persists_rows(db_session):
    stage = _make_stage(db_session)
    rows = PropRuleEngine.record_violations(db_session, stage.id)

    assert len(rows) == len(list(RuleType))
    assert db_session.query(RuleViolation).filter(
        RuleViolation.prop_stage_id == stage.id
    ).count() == len(list(RuleType))
    assert rows[0].occurred_at is not None


def test_get_violations_filter_by_severity(db_session):
    stage = _make_stage(db_session, max_daily_dd=500.0)
    v = _version(db_session)
    db_session.add(_trade(-700, 1, stage.id, v.id))
    db_session.commit()
    PropRuleEngine.record_violations(db_session, stage.id)

    only_violation = PropRuleEngine.get_violations(
        db_session, stage.id, severity=Severity.VIOLATION
    )
    assert len(only_violation) >= 1
    assert all(r.severity == Severity.VIOLATION for r in only_violation)


def test_record_violations_missing_stage_returns_empty(db_session):
    assert PropRuleEngine.record_violations(db_session, 99999) == []


# ═════════════════════════════════════════════
# endpoints
# ═════════════════════════════════════════════
def test_evaluate_and_list_violations_endpoint(client, db_session):
    stage = _make_stage(db_session, max_daily_dd=500.0)
    v = _version(db_session)
    db_session.add(_trade(-700, 1, stage.id, v.id))
    db_session.commit()

    r = client.post(f"/api/prop/stages/{stage.id}/evaluate")
    assert r.status_code == 200
    body = r.json()
    assert body["recorded"] == len(list(RuleType))
    assert body["overall_severity"] == Severity.VIOLATION.value
    assert any(
        c["rule_type"] == RuleType.DAILY_DRAWDOWN.value for c in body["rule_checks"]
    )

    r2 = client.get(f"/api/prop/stages/{stage.id}/violations")
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == len(list(RuleType))
    assert {row["rule_type"] for row in rows} == {rt.value for rt in RuleType}

    r3 = client.get(
        f"/api/prop/stages/{stage.id}/violations", params={"severity": "violation"}
    )
    assert r3.status_code == 200
    assert all(row["severity"] == "violation" for row in r3.json())

    r4 = client.get(
        f"/api/prop/stages/{stage.id}/violations", params={"severity": "bogus"}
    )
    assert r4.status_code == 400


def test_evaluate_endpoint_missing_stage(client, db_session):
    r = client.post("/api/prop/stages/99999/evaluate")
    assert r.status_code == 404


def test_stage_rules_endpoint_updates_modes_and_rejects_invalid_mode(client, db_session):
    stage = _make_stage(db_session)
    response = client.patch(
        f"/api/prop/stages/{stage.id}/rules",
        json={"dd_basis": "equity", "daily_dd_mode": "trailing", "total_dd_mode": "static"},
    )
    assert response.status_code == 200
    db_session.refresh(stage)
    assert stage.dd_basis == "equity"
    assert stage.daily_dd_mode == "trailing"
    assert stage.total_dd_mode == "static"

    invalid = client.patch(
        f"/api/prop/stages/{stage.id}/rules", json={"daily_dd_mode": "invalid"}
    )
    assert invalid.status_code == 422


def test_account_detail_exposes_drawdown_modes(client, db_session):
    stage = _make_stage(db_session)
    stage.dd_basis = "equity"
    stage.daily_dd_mode = "trailing"
    db_session.commit()
    account_id = stage.prop_account_id
    response = client.get(f"/api/prop/accounts/{account_id}")
    assert response.status_code == 200
    stage_data = response.json()["stages"][0]
    assert stage_data["dd_basis"] == "equity"
    assert stage_data["daily_dd_mode"] == "trailing"
    assert stage_data["total_dd_mode"] == "static"


