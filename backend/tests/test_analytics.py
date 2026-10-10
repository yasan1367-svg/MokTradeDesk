"""P1-01: Tehran date boundaries, request-time periods, and Yesterday labels."""
from datetime import datetime, timedelta, timezone

import pytest

from app.api import analytics
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.utils import time_helpers
from app.models.finance import Currency
from app.models.trading import Broker, PersonalTradingAccount


@pytest.mark.parametrize("balance,source", [
    (None, "fallback_10000"), (0.0, "fallback_10000"),
    (10000.0, "accounts"), (250000.0, "accounts"),
])
def test_equity_metadata_includes_baseline_and_currency(client, db_session, balance, source):
    if balance is not None:
        strategy = Strategy(name="Equity metadata")
        db_session.add(strategy)
        db_session.flush()
        version = StrategyVersion(strategy_id=strategy.id, version_name="IRR")
        db_session.add(version)
        db_session.flush()
        broker = Broker(name="IRR equity metadata")
        db_session.add(broker)
        db_session.flush()
        account = PersonalTradingAccount(
            broker_id=broker.id, account_number="metadata",
            currency=Currency.IRR, initial_balance=balance,
        )
        db_session.add(account)
        db_session.flush()
        db_session.add(Trade(
            version_id=version.id,
            personal_trading_account_id=account.id,
            symbol="TEST", direction="buy", size=1, open_price=100,
            open_time=datetime(2026, 10, 1, tzinfo=timezone.utc),
            close_time=datetime(2026, 10, 2, tzinfo=timezone.utc),
            close_price=110, pnl=10, commission=0, swap=0,
            source=TradeSource.MANUAL, test_type=TestType.REAL_PERSONAL,
        ))
        db_session.commit()

    response = client.get("/api/analytics/dashboard", params={"currency": "IRR"})
    assert response.status_code == 200, response.text
    body = response.json()
    baseline = balance if balance and balance > 0 else 10000.0
    assert body["equity_metadata"] == {
        "currency": "IRR", "baseline": baseline, "baseline_source": source,
        "baseline_is_synthetic": source == "fallback_10000",
        "dd_definition": "peak_to_trough",
        "closed_only": True, "scope": "real",
    }
    assert body["summary"]["currency"] == "IRR"
    assert body["equity_curve"][0]["equity"] == baseline


def _utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _freeze(monkeypatch, now):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz else now.replace(tzinfo=None)

    monkeypatch.setattr(analytics, "datetime", FrozenDateTime)
    monkeypatch.setattr(time_helpers, "datetime", FrozenDateTime)


def _seed(db, rows):
    strategy = Strategy(name="Date contract")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="dates")
    db.add(version)
    db.flush()
    for close_time, pnl in rows:
        db.add(Trade(
            version_id=version.id, symbol="XAUUSD", direction="buy",
            open_time=close_time - timedelta(hours=1), close_time=close_time,
            open_price=2000.0, close_price=2000.0, size=1.0,
            pnl=pnl, commission=0.0, swap=0.0,
            source=TradeSource.MANUAL, test_type=TestType.BACKTEST,
        ))
    db.commit()


def test_breakeven_not_counted_as_loss(client, db_session, monkeypatch):
    now = _utc("2026-10-08T12:00:00")
    _freeze(monkeypatch, now)
    _seed(db_session, [(now - timedelta(hours=1), pnl) for pnl in (20, -10, 5)])
    # Positive raw PnL, but breakeven after costs.
    trade = db_session.query(Trade).filter(Trade.pnl == 5).one()
    trade.commission = -3
    trade.swap = -2
    db_session.commit()
    response = client.get("/api/analytics/dashboard", params={"scope": "backtest"})
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["breakeven_trades"] == 1
    assert body["summary"]["avg_loss"] == 10
    assert body["today"] == {
        "pnl": 10, "trades_count": 3, "winning_trades": 1,
        "losing_trades": 1, "breakeven_trades": 1, "win_rate": 33.33,
    }


@pytest.mark.parametrize("count", [0, 2])
def test_avg_r_null_when_no_r_samples(client, db_session, count):
    _seed(db_session, [(_utc("2026-10-08T10:00:00"), 10)] * count)
    response = client.get("/api/analytics/dashboard", params={"scope": "backtest"})
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["avg_r_multiple"] is None
    assert summary["r_sample_count"] == 0
    assert summary["missing_r_count"] == count


def test_r_sample_count_reported(client, db_session):
    _seed(db_session, [(_utc("2026-10-08T10:00:00"), 10)] * 4)
    trades = db_session.query(Trade).order_by(Trade.id).all()
    for trade, r in zip(trades, [0, 2, None, 100]):
        trade.r_multiple = r
    trades[-1].close_time = None  # Open R must not enter the sample.
    db_session.commit()
    response = client.get("/api/analytics/dashboard", params={"scope": "backtest"})
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["closed_trades"] == 3
    assert summary["r_sample_count"] == 2
    assert summary["missing_r_count"] == 1
    assert summary["avg_r_multiple"] == 1


@pytest.mark.parametrize("value,end,expected", [
    ("2026-10-08", False, "2026-10-07T20:30:00"),
    ("2026-10-08", True, "2026-10-08T20:30:00"),
    (" 2026-10-08 ", True, "2026-10-08T20:30:00"),
    ("2026-10-08T00:00:00", True, "2026-10-08T00:00:00"),
    ("2026-10-08T12:00:00.123456+03:30", True, "2026-10-08T08:30:00.123456"),
    ("2026-10-08T12:00:00Z", False, "2026-10-08T12:00:00"),
])
def test_parse_bound(value, end, expected):
    assert analytics._parse_bound(value, end=end) == _utc(expected)


@pytest.mark.parametrize("value", [None, "", " ", "invalid", "2026-02-30"])
@pytest.mark.parametrize("end", [False, True])
def test_parse_bound_empty_or_invalid(value, end):
    assert analytics._parse_bound(value, end=end) is None


@pytest.mark.parametrize("date_from,date_to", [
    ("2026-10-08", "2026-10-08"),
    ("2026-10-08T00:00:00+03:30", "2026-10-09T00:00:00+03:30"),
])
def test_dashboard_half_open_boundaries(client, db_session, date_from, date_to):
    start = _utc("2026-10-07T20:30:00")
    end = _utc("2026-10-08T20:30:00")
    _seed(db_session, [
        (start - timedelta(microseconds=1), 1000), (start, 10),
        (end - timedelta(microseconds=1), 20), (end, 2000),
    ])
    response = client.get("/api/analytics/dashboard", params={
        "scope": "backtest", "date_from": date_from, "date_to": date_to,
    })
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["net_pnl"] == 30
    assert response.json()["summary"]["closed_trades"] == 2


def test_today_and_periods_exclude_future_closes(client, db_session, monkeypatch):
    now = _utc("2026-10-08T10:00:00")
    _freeze(monkeypatch, now)
    _seed(db_session, [
        (_utc("2026-10-07T20:30:00"), 100), (now, -20),
        (now + timedelta(microseconds=1), 500),
        (now + timedelta(days=1), 1000),
    ])
    response = client.get("/api/analytics/dashboard", params={"scope": "backtest"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["today"] == {
        "pnl": 80, "trades_count": 2, "win_rate": 50,
        "winning_trades": 1, "losing_trades": 1,
        "breakeven_trades": 0,
    }
    for period in ("month", "quarter", "year"):
        assert body["periods"][period]["pnl"] == 80


def test_today_intersects_selected_dates(client, db_session, monkeypatch):
    now = _utc("2026-10-08T10:00:00")
    _freeze(monkeypatch, now)
    _seed(db_session, [(now, 100)])
    response = client.get("/api/analytics/dashboard", params={
        "scope": "backtest", "date_to": "2026-10-07",
    })
    assert response.status_code == 200, response.text
    assert response.json()["today"]["pnl"] == 0
    assert response.json()["today"]["trades_count"] == 0


def test_yesterday_tehran_label_and_boundaries(client, db_session, monkeypatch):
    _freeze(monkeypatch, _utc("2026-10-08T21:00:00"))  # Oct 9 in Tehran
    start = _utc("2026-10-07T20:30:00")
    end = _utc("2026-10-08T20:30:00")
    _seed(db_session, [
        (start - timedelta(microseconds=1), 1000), (start, 10),
        (end - timedelta(microseconds=1), 20), (end, 2000),
    ])
    # Selected Dashboard dates must not constrain Yesterday.
    response = client.get("/api/analytics/yesterday", params={
        "scope": "backtest", "date_from": "2020-01-01", "date_to": "2020-01-01",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["date"] == "1405/07/16"
    assert body["day_of_week"] == "پنج‌شنبه"
    assert body["net_pnl"] == 30
    assert body["total_trades"] == 2