from datetime import datetime, timezone

import pytest

from app.domain.risk.instrument_spec import InstrumentSpec
from app.domain.risk.risk_engine import RiskEngine
from app.models.finance import Currency
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.models.trading import Broker, PersonalTradingAccount


def _version(db):
    strategy = Strategy(name="RiskFacade")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db.add(version)
    db.flush()
    return version


def _trade(db, version, *, day, pnl, test_type, symbol="EURUSD", account_id=None, **kwargs):
    trade = Trade(
        version_id=version.id,
        personal_trading_account_id=account_id,
        symbol=symbol,
        direction="buy",
        open_time=datetime(2026, 1, day, 9, tzinfo=timezone.utc),
        close_time=datetime(2026, 1, day, 10, tzinfo=timezone.utc),
        open_price=1.1000,
        close_price=1.1010,
        size=0.1,
        sl=1.0950,
        pnl=pnl,
        r_multiple=kwargs.pop("r_multiple", 1.0),
        commission=kwargs.pop("commission", 0.0),
        swap=kwargs.pop("swap", 0.0),
        source=TradeSource.MANUAL,
        test_type=test_type,
        **kwargs,
    )
    db.add(trade)
    return trade


def _personal_account(db):
    broker = Broker(name="RiskFacadeBroker")
    db.add(broker)
    db.flush()
    account = PersonalTradingAccount(
        broker_id=broker.id,
        account_number="RF-1",
        currency=Currency.USDT,
        initial_balance=10000.0,
        current_balance=10000.0,
    )
    db.add(account)
    db.flush()
    return account


def _instrument_spec(db, symbol="EURUSD"):
    spec = InstrumentSpec(
        canonical_symbol=symbol,
        contract_size=100000.0,
        tick_size=0.0001,
        tick_value=10.0,
        min_lot=0.01,
        max_lot=100.0,
        lot_step=0.01,
        commission_one_side=0.0,
        currency=Currency.USDT,
    )
    db.add(spec)
    db.flush()
    return spec


def test_risk_engine_facade(db_session):
    version = _version(db_session)
    account = _personal_account(db_session)
    _trade(db_session, version, day=1, pnl=100.0, test_type=TestType.REAL_PERSONAL, account_id=account.id)
    _trade(db_session, version, day=2, pnl=-50.0, test_type=TestType.REAL_PERSONAL, account_id=account.id)
    db_session.commit()

    result = RiskEngine.calculate_risk_metrics(db_session, scope="real", initial_balance=10000.0)

    assert result["initial_balance"] == 10000.0
    assert result["position_sizing"] is None
    assert result["expectancy_r"] == pytest.approx(1.0)
    assert len(result["equity_curve"]) == 3
    assert result["static_dd"]["dd"] == pytest.approx(0.0)
    assert result["peak_to_trough_dd"]["dd"] == pytest.approx(50.0)
    assert result["sharpe"] != 0.0
    assert result["sortino"] > 0.0


def test_risk_engine_with_symbol(db_session):
    version = _version(db_session)
    account = _personal_account(db_session)
    _instrument_spec(db_session)
    _trade(db_session, version, day=1, pnl=100.0, test_type=TestType.REAL_PERSONAL, account_id=account.id)
    _trade(db_session, version, day=2, pnl=25.0, test_type=TestType.REAL_PERSONAL, symbol="GBPUSD", account_id=account.id)
    db_session.commit()

    result = RiskEngine.calculate_risk_metrics(
        db_session, scope="real", symbol="eurusd", initial_balance=10000.0
    )

    assert result["expectancy_r"] == pytest.approx(1.0)
    assert len(result["equity_curve"]) == 2
    assert result["position_sizing"]["volume"] == pytest.approx(0.2)


def test_risk_engine_backtest_scope(db_session):
    version = _version(db_session)
    account = _personal_account(db_session)
    _trade(db_session, version, day=1, pnl=100.0, test_type=TestType.BACKTEST)
    _trade(
        db_session,
        version,
        day=2,
        pnl=200.0,
        test_type=TestType.REAL_PERSONAL,
        account_id=account.id,
    )
    db_session.commit()

    result = RiskEngine.calculate_risk_metrics(db_session, scope="backtest")

    assert result["initial_balance"] == 10000.0
    assert len(result["equity_curve"]) == 2
    assert result["equity_curve"][-1]["pnl"] == pytest.approx(100.0)


def test_risk_engine_real_scope(db_session):
    version = _version(db_session)
    account = _personal_account(db_session)
    _trade(db_session, version, day=1, pnl=100.0, test_type=TestType.REAL_PERSONAL, account_id=account.id)
    _trade(db_session, version, day=2, pnl=500.0, test_type=TestType.BACKTEST)
    db_session.commit()

    result = RiskEngine.calculate_risk_metrics(db_session, scope="real")

    assert len(result["equity_curve"]) == 2
    assert result["equity_curve"][-1]["pnl"] == pytest.approx(100.0)


def test_risk_engine_empty_trades(db_session):
    result = RiskEngine.calculate_risk_metrics(db_session, scope="all")

    assert result["initial_balance"] == 10000.0
    assert result["position_sizing"] is None
    assert result["expectancy_r"] == 0.0
    assert result["r_distribution"] == [
        {"range": label, "count": 0}
        for label in ["< -2R", "-2..-1R", "-1..0R", "0..1R", "1..2R", "2..3R", "> 3R"]
    ]
    assert len(result["equity_curve"]) == 1
    assert result["sharpe"] == 0.0
    assert result["sortino"] == 0.0