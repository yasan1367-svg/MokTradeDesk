"""فاز ۴۳ — تست «یک عدد»: همهٔ سرویس‌ها باید یک net_pnl واحد بدهند.

سناریو: یک مرحلهٔ پراپ با چند معامله و کمیسیون/swap.
قرارداد: net_pnl = pnl + commission + swap.

    PropRuleEngine.current_profit == AnalysisService.net_pnl
    == dashboard(prop scope).current_profit == finance.real-pnl.prop_stage_3.pnl
"""
from datetime import datetime, timezone

import pytest

from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.services import metrics
from app.services.analysis_service import AnalysisService
from app.services.prop_rule_engine import PropRuleEngine

# معاملات: (pnl, commission, swap) → net هر کدام ۹۴۰ / ۴۶۵ / ‎-۲۱۰ ⇒ مجموع ۱۱۹۵
# مجموع pnl خام = ۱۳۰۰ (تا اثبات شود کمیسیون روی تصمیم اثر دارد)
TRADES = [
    (1000.0, -50.0, -10.0),
    (500.0, -30.0, -5.0),
    (-200.0, -10.0, 0.0),
]
EXPECTED_NET = 1195.0
RAW_SUM = 1300.0


def _seed(db, *, stage_type=StageType.FUNDED_REAL, profit_target=1000.0):
    firm = PropFirm(name="FTMO")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="A1")
    db.add(account)
    db.flush()
    stage = PropStage(
        prop_account_id=account.id,
        stage_type=stage_type,
        status=StageStatus.ACTIVE,
        initial_balance=10000.0,
        profit_target=profit_target,
        max_daily_dd=5000.0,
        max_total_dd=1000.0,
        min_trading_days=1,
        profit_share_percentage=80.0,
        total_withdrawn=0.0,
    )
    db.add(stage)
    db.flush()

    strategy = Strategy(name="S")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db.add(version)
    db.flush()

    for i, (pnl, commission, swap) in enumerate(TRADES, start=1):
        db.add(Trade(
            version_id=version.id,
            prop_stage_id=stage.id,
            symbol="XAUUSD",
            direction="buy",
            open_time=datetime(2025, 1, i, 9, 0, tzinfo=timezone.utc),
            close_time=datetime(2025, 1, i, 10, 0, tzinfo=timezone.utc),
            open_price=2000.0,
            close_price=2000.0,
            size=1.0,
            pnl=pnl,
            commission=commission,
            swap=swap,
            source=TradeSource.MANUAL,
            test_type=TestType.REAL_PROP,
        ))
    db.commit()
    return stage, version


def _stage_trades(db, stage_id):
    return (
        db.query(Trade)
        .filter(Trade.prop_stage_id == stage_id)
        .order_by(Trade.close_time)
        .all()
    )


# ═════════════════════════════════════════════
# PropRuleEngine روی net_pnl
# ═════════════════════════════════════════════
def test_prop_engine_uses_net_pnl(db_session):
    stage, _ = _seed(db_session)
    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["current_profit"] == pytest.approx(EXPECTED_NET)
    assert res["equity"] == pytest.approx(10000.0 + EXPECTED_NET)
    # و نه مجموع pnl خام
    assert res["current_profit"] != pytest.approx(RAW_SUM)


# ═════════════════════════════════════════════
# همهٔ سرویس‌ها → یک عدد
# ═════════════════════════════════════════════
def test_all_services_return_same_net_pnl(client, db_session):
    stage, _ = _seed(db_session)

    engine_profit = PropRuleEngine.evaluate_stage(db_session, stage.id)["current_profit"]

    analysis = AnalysisService(db_session).analyze_prop_stage(stage.id)
    analysis_profit = round(float(analysis["result"].net_pnl), 2)

    dashboard = client.get("/api/analytics/dashboard").json()
    stage_row = next(s for s in dashboard["prop_progress"] if s["stage_id"] == stage.id)
    dashboard_profit = stage_row["current_profit"]

    finance = client.get("/api/finance/real-pnl").json()
    finance_profit = finance["prop_stage_3"]["pnl"]

    assert engine_profit == pytest.approx(EXPECTED_NET)
    assert analysis_profit == pytest.approx(EXPECTED_NET)
    assert dashboard_profit == pytest.approx(EXPECTED_NET)
    assert finance_profit == pytest.approx(EXPECTED_NET)

    # هر چهار عدد دقیقاً برابرند
    assert len({round(engine_profit, 2), analysis_profit, dashboard_profit, finance_profit}) == 1


# ═════════════════════════════════════════════
# ⭐ کمیسیون روی تصمیم پاس/هدف اثر دارد
# ═════════════════════════════════════════════
def test_commission_affects_prop_decision(db_session):
    # هدف ۱۲۰۰: با pnl خام (۱۳۰۰) پاس می‌شد، با net (۱۱۹۵) نه!
    stage, _ = _seed(db_session, stage_type=StageType.STAGE_1, profit_target=1200.0)

    raw = sum(t.pnl or 0 for t in _stage_trades(db_session, stage.id))
    assert raw == pytest.approx(RAW_SUM)
    assert raw >= 1200.0  # اگر pnl خام ملاک بود، هدف محقق می‌شد

    res = PropRuleEngine.evaluate_stage(db_session, stage.id)
    assert res["current_profit"] == pytest.approx(EXPECTED_NET)
    assert res["target_reached"] is False
    assert res["ready_to_pass"] is False


# ═════════════════════════════════════════════
# سازگاری max_drawdown
# ═════════════════════════════════════════════
def test_max_drawdown_consistent(db_session):
    stage, _ = _seed(db_session, stage_type=StageType.STAGE_1)
    trades = _stage_trades(db_session, stage.id)

    engine_dd = PropRuleEngine.evaluate_stage(db_session, stage.id)["max_total_dd"]
    expected_engine_dd = metrics.calculate_max_drawdown(trades, initial=stage.initial_balance)
    assert engine_dd == pytest.approx(expected_engine_dd, abs=0.01)

    analysis_dd = AnalysisService(db_session).analyze_prop_stage(stage.id)["result"].max_dd
    expected_analysis_dd = metrics.calculate_max_drawdown(trades)
    assert analysis_dd == pytest.approx(expected_analysis_dd, abs=0.01)
