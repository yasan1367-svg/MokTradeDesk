"""Regression coverage for Phase 57 analytics metric corrections."""

from datetime import datetime, timezone

import pytest

from app.api.analytics import calculate_risk_of_ruin
from app.domain.risk.r_engine import calculate_expectancy_r
from app.domain.risk.risk_engine import RiskEngine
from app.models.finance import Currency
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.models.trading import Broker, PersonalTradingAccount


def _setup_account(db):
    strategy = Strategy(name="Phase57")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v57")
    broker = Broker(name="Phase57Broker")
    db.add_all([version, broker])
    db.flush()
    version.strategy_id = strategy.id
    account = PersonalTradingAccount(
        broker_id=broker.id,
        account_number="P57-1",
        account_label="Phase57",
        currency=Currency.USDT,
        initial_balance=10000.0,
        current_balance=10000.0,
    )
    db.add(account)
    db.flush()
    return version, account


def _add_trade(db, version, account, *, day, pnl, r_multiple, commission=0.0):
    db.add(Trade(
        version_id=version.id,
        personal_trading_account_id=account.id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 7, day, 9, tzinfo=timezone.utc),
        close_time=datetime(2025, 7, day, 10, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        sl=1990.0,
        pnl=pnl,
        r_multiple=r_multiple,
        commission=commission,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=TestType.REAL_PERSONAL,
    ))


def test_expectancy_r_includes_zero_r_values():
    assert calculate_expectancy_r([2.0, 0.0, -1.0, None]) == pytest.approx(1 / 3)


def test_risk_of_ruin_returns_none_without_meaningful_r_data(client, db_session):
    assert calculate_risk_of_ruin(0.0, 0.0, 0.0, 0.01) is None
    assert calculate_risk_of_ruin(0.5, 0.0, 0.0, 0.01) is None

    version, account = _setup_account(db_session)
    _add_trade(db_session, version, account, day=1, pnl=100.0, r_multiple=None)
    _add_trade(db_session, version, account, day=2, pnl=-50.0, r_multiple=None)
    db_session.commit()
    advanced = client.get(
        "/api/analytics/risk-advanced", params={"scope": "real", "currency": "USDT"}
    ).json()
    risk = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    assert advanced["risk_of_ruin"] is None
    assert risk["risk_metrics"]["risk_of_ruin"] is None

    version, account = _setup_account(db_session)
    _add_trade(db_session, version, account, day=1, pnl=100.0, r_multiple=1.0)
    _add_trade(db_session, version, account, day=2, pnl=-50.0, r_multiple=None)
    db_session.commit()
    advanced = client.get(
        "/api/analytics/risk-advanced", params={"scope": "real", "currency": "USDT"}
    ).json()
    assert advanced["risk_of_ruin"] is None


def test_risk_of_ruin_uses_r_edge_and_validates_bounds():
    assert calculate_risk_of_ruin(0.4, 1.0, 1.0, 0.01) == 1.0
    estimate = calculate_risk_of_ruin(0.6, 2.0, 1.0, 0.01)
    assert estimate is not None and 0.0 < estimate < 1.0
    assert calculate_risk_of_ruin(0.6, 2.0, 1.0, 1.0) is None


def test_risk_engine_daily_returns_group_by_day_and_opening_equity():
    trades = [
        {"close_time": datetime(2025, 1, 1, 9, tzinfo=timezone.utc), "net": 100.0},
        {"close_time": datetime(2025, 1, 1, 10, tzinfo=timezone.utc), "net": 100.0},
        {"close_time": datetime(2025, 1, 2, 9, tzinfo=timezone.utc), "net": -100.0},
    ]
    assert RiskEngine._daily_returns_from_trades(trades, 10000.0) == pytest.approx(
        [0.02, -100.0 / 10200.0]
    )


def test_risk_metrics_expectancy_is_trade_r_average_and_keeps_zero(client, db_session):
    version, account = _setup_account(db_session)
    for day, pnl, r in [(1, 100.0, 2.0), (2, 0.0, 0.0), (3, -50.0, -1.0)]:
        _add_trade(db_session, version, account, day=day, pnl=pnl, r_multiple=r)
    db_session.commit()

    metrics = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    advanced = client.get(
        "/api/analytics/risk-advanced", params={"scope": "real", "currency": "USDT"}
    ).json()
    assert metrics["performance_ratios"]["expectancy_r"] == pytest.approx(0.33)
    assert advanced["expectancy_r"] == pytest.approx(0.333)
    assert advanced["avg_r_multiple"] == pytest.approx(0.333)
    assert advanced["r_multiple_distribution"][3]["count"] == 1


def test_risk_metrics_sharpe_sortino_use_daily_percentage_returns(client, db_session):
    version, account = _setup_account(db_session)
    for day, pnl in [(1, 100.0), (2, -100.0), (3, 300.0)]:
        _add_trade(db_session, version, account, day=day, pnl=pnl, r_multiple=1.0)
    db_session.commit()

    daily = [0.01, -100.0 / 10100.0, 300.0 / 10000.0]
    mean = sum(daily) / len(daily)
    std = (sum((value - mean) ** 2 for value in daily) / len(daily)) ** 0.5
    downside = (sum(value**2 for value in daily if value < 0) / len(daily)) ** 0.5
    result = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    ratios = result["performance_ratios"]
    assert ratios["sharpe_ratio"] == pytest.approx(round(mean / std, 2))
    assert ratios["sortino_ratio"] == pytest.approx(round(mean / downside, 2))


def test_risk_advanced_sharpe_sortino_use_return_series(client, db_session):
    version, account = _setup_account(db_session)
    for day, pnl in [(1, 100.0), (2, -100.0), (3, 300.0)]:
        _add_trade(db_session, version, account, day=day, pnl=pnl, r_multiple=1.0)
    db_session.commit()

    daily = [0.01, -100.0 / 10100.0, 300.0 / 10000.0]
    mean = sum(daily) / len(daily)
    std = (sum((value - mean) ** 2 for value in daily) / len(daily)) ** 0.5
    downside = (sum(value**2 for value in daily if value < 0) / len(daily)) ** 0.5
    result = client.get(
        "/api/analytics/risk-advanced", params={"scope": "real", "currency": "USDT"}
    ).json()
    assert result["sharpe_ratio"] == pytest.approx(round(mean / std, 3))
    assert result["sortino_ratio"] == pytest.approx(round(mean / downside, 3))


def test_var_cvar_are_nonnegative_dollars_and_initial_balance_percent(client, db_session):
    version, account = _setup_account(db_session)
    for day, pnl, r in [(1, 100.0, 1.0), (2, -100.0, -1.0), (3, -500.0, -1.0), (4, 300.0, 1.0)]:
        _add_trade(db_session, version, account, day=day, pnl=pnl, r_multiple=r)
    db_session.commit()

    advanced = client.get(
        "/api/analytics/risk-advanced", params={"scope": "real", "currency": "USDT"}
    ).json()
    metrics = client.get("/api/analytics/risk-metrics", params={"scope": "real"}).json()
    for result in (advanced, metrics["risk_metrics"]):
        assert result["var_95"] >= 0
        assert result["cvar_95"] >= result["var_95"]
        assert result["var_95_percent"] == pytest.approx(result["var_95"] / 10000 * 100)
        assert result["cvar_95_percent"] == pytest.approx(result["cvar_95"] / 10000 * 100)
    assert advanced["risk_of_ruin"] is not None

