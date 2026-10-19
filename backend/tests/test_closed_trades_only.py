"""Regression tests: closed-trades-only scope.

Verifies that open trades (close_time IS NULL) do NOT affect:
- AnalysisService.analyze_version metrics
- AnalysisService.analyze_prop_stage metrics
- AnalysisService.analyze_personal_account metrics
- pass_stage final_balance
- PropRuleEngine target_reached / trading_days / current_profit
"""
from datetime import datetime, timezone

import pytest

from app.models.prop import (
    PropFirm, PropAccount, PropStage, StageType, StageStatus,
)
from app.models.strategy import (
    Trade, TradeSource, TestType, Strategy, StrategyVersion,
)
from app.services.analysis_service import AnalysisService
from app.services.prop_rule_engine import PropRuleEngine


def _version(db, name="ct"):
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.flush()
    return v


def _closed_trade(pnl, day, *, stage_id=None, version_id=None, personal_account_id=None, test_type=TestType.REAL_PROP):
    t = Trade(
        symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0, close_price=2000.0, size=1.0,
        pnl=pnl, source=TradeSource.MANUAL,
        test_type=test_type,
        prop_stage_id=stage_id, version_id=version_id,
        personal_trading_account_id=personal_account_id,
    )
    return t


def _open_trade(pnl, day, *, stage_id=None, version_id=None, personal_account_id=None, test_type=TestType.REAL_PROP):
    t = Trade(
        symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, day, 9, 0, tzinfo=timezone.utc),
        close_time=None,
        open_price=2000.0, close_price=2000.0, size=1.0,
        pnl=pnl, source=TradeSource.MANUAL,
        test_type=test_type,
        prop_stage_id=stage_id, version_id=version_id,
        personal_trading_account_id=personal_account_id,
    )
    return t


def _make_stage(db, **kw):
    defaults = dict(
        stage_type=StageType.STAGE_1, status=StageStatus.ACTIVE,
        profit_target=1000.0, max_daily_dd=500.0, max_total_dd=1000.0,
        min_trading_days=3, initial=10000.0,
    )
    defaults.update(kw)
    firm = PropFirm(name="CT_FIRM")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="CT_ACC")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id, stage_type=defaults["stage_type"],
        status=defaults["status"], initial_balance=defaults["initial"],
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
# ═════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════

def test_open_trades_excluded_from_analyze_version(db_session):
    """analyze_version must NOT include open trades in metrics."""
    v = _version(db_session)
    # Use FORWARD (version-only, no prop_stage_id or personal_trading_account_id needed)
    db_session.add(_closed_trade(200, 1, version_id=v.id, test_type=TestType.FORWARD))
    db_session.add(_open_trade(9999, 2, version_id=v.id, test_type=TestType.FORWARD))
    db_session.commit()

    svc = AnalysisService(db_session)
    result = svc.analyze_version(v.id, TestType.FORWARD)

    assert result["result"].total_trades == 1, \
        f"Expected 1 closed trade, got {result['result'].total_trades}"
    assert result["result"].net_pnl == 200, \
        f"Expected net_pnl=200 (closed-only), got {result['result'].net_pnl}"


def test_open_trades_excluded_from_analyze_prop_stage(db_session):
    """analyze_prop_stage must NOT include open trades in metrics."""
    v = _version(db_session)
    stage = _make_stage(db_session)
    db_session.add(_closed_trade(200, 1, stage_id=stage.id, version_id=v.id))
    db_session.add(_open_trade(9999, 2, stage_id=stage.id, version_id=v.id))
    db_session.commit()

    svc = AnalysisService(db_session)
    result = svc.analyze_prop_stage(stage.id)

    # analyze_prop_stage returns {"result": AnalysisResult, ...} with top-level keys
    inner = result.get("result", result)
    total = inner.total_trades if hasattr(inner, "total_trades") else result.get("total_trades", 0)
    net = inner.net_pnl if hasattr(inner, "net_pnl") else result.get("net_pnl", 0)
    assert total == 1, \
        f"Expected 1 closed trade, got {total}"
    assert net == 200, \
        f"Expected net_pnl=200, got {net}"


def test_open_trades_excluded_from_analyze_personal_account(db_session):
    """analyze_personal_account must NOT include open trades."""
    from app.models.trading import PersonalTradingAccount, Broker
    from app.models.finance import Currency

    v = _version(db_session)
    broker = Broker(name="CT_BROKER")
    db_session.add(broker)
    db_session.flush()
    pa = PersonalTradingAccount(
        broker_id=broker.id, account_label="CT_PERS",
        account_number="CT-001",
        currency=Currency.USDT,
    )
    db_session.add(pa)
    db_session.flush()

    # REAL_PERSONAL: personal_trading_account_id NOT NULL, prop_stage_id NULL
    c = _closed_trade(200, 1, version_id=v.id, personal_account_id=pa.id,
                      test_type=TestType.REAL_PERSONAL)
    o = _open_trade(9999, 2, version_id=v.id, personal_account_id=pa.id,
                    test_type=TestType.REAL_PERSONAL)
    db_session.add_all([c, o])
    db_session.commit()

    svc = AnalysisService(db_session)
    result = svc.analyze_personal_account(pa.id)

    assert result["result"].total_trades == 1, \
        f"Expected 1 closed trade, got {result['result'].total_trades}"
    assert result["result"].net_pnl == 200, \
        f"Expected net_pnl=200, got {result['result'].net_pnl}"


def test_open_trades_not_in_pass_stage_final_balance(client, db_session):
    """pass_stage must use ONLY closed trades for final_balance."""
    v = _version(db_session)
    stage = _make_stage(db_session, profit_target=199, min_trading_days=0,
                        max_daily_dd=9999, max_total_dd=9999)
    db_session.add(_closed_trade(200, 1, stage_id=stage.id, version_id=v.id))
    db_session.add(_open_trade(9999, 2, stage_id=stage.id, version_id=v.id))
    db_session.commit()

    response = client.post(
        f"/api/prop/stages/{stage.id}/pass",
        json={"final_balance": None},
    )
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    # initial(10000) + closed_pnl(200) = 10200, NOT 20199
    expected = 10000 + 200
    assert abs(data.get("final_balance", 0) - expected) < 0.01, \
        f"Expected final_balance ~{expected}, got {data.get('final_balance')}"


def test_open_profit_cannot_satisfy_profit_target(db_session):
    """Open-trade floating profit must NOT satisfy Profit Target."""
    v = _version(db_session)
    stage = _make_stage(db_session, profit_target=1000, min_trading_days=0)
    db_session.add(_closed_trade(200, 1, stage_id=stage.id, version_id=v.id))
    db_session.add(_open_trade(9999, 2, stage_id=stage.id, version_id=v.id))
    db_session.commit()

    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert result["target_reached"] is False, \
        "target_reached should be False (200 < 1000)"
    assert result["current_profit"] == 200, \
        f"current_profit should be 200 (closed-only), got {result['current_profit']}"
    assert "floating_pnl" in result, "floating_pnl field missing"
    assert result["floating_pnl"] == 9999, \
        f"floating_pnl should be 9999, got {result['floating_pnl']}"


def test_open_trades_cannot_add_trading_day(db_session):
    """Open trades must NOT add a synthetic trading day."""
    v = _version(db_session)
    stage = _make_stage(db_session, profit_target=0, min_trading_days=2)
    db_session.add(_closed_trade(200, 1, stage_id=stage.id, version_id=v.id))
    db_session.add(_open_trade(100, 2, stage_id=stage.id, version_id=v.id))
    db_session.commit()

    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert result["trading_days"] == 1, \
        f"trading_days should be 1 (only closed day), got {result['trading_days']}"
    assert result["days_met"] is False, "days_met should be False (1 < 2)"

    # Now add a closed trade on day 2
    db_session.add(_closed_trade(300, 2, stage_id=stage.id, version_id=v.id))
    db_session.commit()
    result2 = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert result2["trading_days"] == 2, \
        f"trading_days should be 2 now, got {result2['trading_days']}"
    assert result2["days_met"] is True
def test_withdrawable_profit_uses_closed_pnl_only(db_session):
    """FUNDED_REAL withdrawable_profit must be based on closed PnL only, not floating."""
    v = _version(db_session)
    stage = _make_stage(db_session, stage_type=StageType.FUNDED_REAL,
                        profit_target=0, min_trading_days=0,
                        max_daily_dd=9999, max_total_dd=9999,
                        profit_share=80.0, initial=10000)
    # $500 closed profit, $300 floating profit
    db_session.add(_closed_trade(500, 1, stage_id=stage.id, version_id=v.id))
    db_session.add(_open_trade(300, 2, stage_id=stage.id, version_id=v.id))
    db_session.commit()

    result = PropRuleEngine.evaluate_stage(db_session, stage.id)
    # withdrawable_profit should be based on $500 closed only (80% share = $400)
    expected = 500 * 0.80  # $400
    assert abs(result["withdrawable_profit"] - expected) < 0.01, \
        f"withdrawable_profit should be {expected} (closed-only), got {result['withdrawable_profit']}"
    assert result["floating_pnl"] == 300, \
        f"floating_pnl should still be 300, got {result['floating_pnl']}"