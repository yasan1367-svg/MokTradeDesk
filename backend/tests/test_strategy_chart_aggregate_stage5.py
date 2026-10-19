from datetime import datetime, timezone

import pytest

from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource


def _trade(db, version_id, *, pnl, commission=0, swap=0, day=1, test_type=TestType.BACKTEST, closed=True, symbol="XAUUSD", r=0.5):
    trade = Trade(
        version_id=version_id, symbol=symbol, direction="buy",
        open_time=datetime(2025, 1, day, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, day, 12, tzinfo=timezone.utc) if closed else None,
        open_price=10, close_price=11 if closed else None, size=1,
        pnl=pnl, commission=commission, swap=swap, r_multiple=r,
        source=TradeSource.MANUAL, test_type=test_type,
    )
    db.add(trade)
    db.commit()
    return trade


def test_chart_aggregate_matches_closed_scope_summary_and_shared_net_metric(client, db_session):
    strategy = Strategy(name="chart aggregate")
    db_session.add(strategy)
    db_session.commit()
    v1 = StrategyVersion(strategy_id=strategy.id, version_name="same")
    v2 = StrategyVersion(strategy_id=strategy.id, version_name="same")
    db_session.add_all([v1, v2])
    db_session.commit()

    _trade(db_session, v1.id, pnl=100, commission=-2, swap=-1, day=1, r=0.5)
    _trade(db_session, v1.id, pnl=-30, commission=-2, day=3, r=-1.5)
    _trade(db_session, v2.id, pnl=500, day=2, test_type=TestType.FORWARD)
    _trade(db_session, v2.id, pnl=999, day=4, closed=False)

    response = client.get(f"/api/strategies/{strategy.id}/chart-aggregate", params={"test_type": "backtest"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_trades"] == 2
    assert body["net_pnl"] == 65.0
    assert body["by_version"][str(v1.id)] == {"trade_count": 2, "net_pnl": 65.0}
    assert body["equity_curve"] == [
        {"period": "2025-01", "cumulative_pnl": 65.0},
    ]
    assert sum(item["net_pnl"] for item in body["by_version"].values()) == body["net_pnl"]
    assert body["equity_curve"][-1]["cumulative_pnl"] == body["net_pnl"]
    assert sum(item["count"] for item in body["r_histogram"]) == 2


def test_chart_aggregate_respects_symbol_date_and_rejects_real_scope(client, db_session):
    strategy = Strategy(name="filtered chart")
    db_session.add(strategy)
    db_session.commit()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v")
    db_session.add(version)
    db_session.commit()
    _trade(db_session, version.id, pnl=10, day=1, symbol="XAUUSD")
    _trade(db_session, version.id, pnl=20, day=2, symbol="BTCUSDT")
    result = client.get(f"/api/strategies/{strategy.id}/chart-aggregate", params={
        "test_type": "backtest", "symbol": "XAUUSD", "date_from": "2025-01-01", "date_to": "2025-01-01",
    })
    assert result.status_code == 200
    assert result.json()["total_trades"] == 1
    assert result.json()["net_pnl"] == 10
    assert client.get(f"/api/strategies/{strategy.id}/chart-aggregate", params={"test_type": "real_personal"}).status_code == 422


def test_strategy_chart_date_only_uses_tehran_inclusive_day_edges(client, db_session):
    strategy = Strategy(name="Tehran day filter")
    db_session.add(strategy)
    db_session.commit()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v")
    db_session.add(version)
    db_session.commit()
    for instant, pnl in (("2024-12-31T20:29:59.999999", 100), ("2024-12-31T20:30:00", 1), ("2025-01-01T20:29:59.999999", 2)):
        close = datetime.fromisoformat(instant).replace(tzinfo=timezone.utc)
        trade = Trade(
            version_id=version.id, symbol="XAUUSD", direction="buy", open_time=close,
            close_time=close, open_price=1, close_price=2, size=1, pnl=pnl,
            commission=0, swap=0, source=TradeSource.MANUAL, test_type=TestType.BACKTEST,
        )
        db_session.add(trade)
    db_session.commit()
    response = client.get(f"/api/strategies/{strategy.id}/chart-aggregate", params={
        "date_from": "2025-01-01", "date_to": "2025-01-01",
    })
    assert response.status_code == 200, response.text
    assert response.json()["total_trades"] == 2
    assert response.json()["net_pnl"] == 3


def test_chart_aggregate_preserves_version_precision_and_rounds_raw_total(client, db_session):
    strategy = Strategy(name="fractional aggregate")
    db_session.add(strategy)
    db_session.commit()
    versions = [StrategyVersion(strategy_id=strategy.id, version_name=f"v{i}") for i in range(2)]
    db_session.add_all(versions)
    db_session.commit()
    for version in versions:
        _trade(db_session, version.id, pnl=0.004)

    response = client.get(f"/api/strategies/{strategy.id}/chart-aggregate", params={"test_type": "backtest"})
    assert response.status_code == 200, response.text
    body = response.json()
    # Per-version amounts retain sub-cent precision; their sum is the raw
    # aggregate before the overall two-decimal presentation rounding.
    version_sum = sum(body["by_version"][str(version.id)]["net_pnl"] for version in versions)
    assert version_sum == pytest.approx(0.008, abs=1e-12)
    assert body["by_version"][str(versions[0].id)]["net_pnl"] == pytest.approx(0.004, abs=1e-12)
    assert body["by_version"][str(versions[1].id)]["net_pnl"] == pytest.approx(0.004, abs=1e-12)
    assert body["net_pnl"] == 0.01
    assert body["net_pnl"] == round(version_sum, 2)
    assert body["equity_curve"][-1]["cumulative_pnl"] == body["net_pnl"]