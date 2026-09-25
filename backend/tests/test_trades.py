"""تست‌های TradeValidator و endpointهای معاملات (فاز ۱۲)"""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion
from app.utils.trade_metrics import calculate_r_multiple
from app.utils.trade_validator import TradeValidator


# ═════════════════════════════════════════════
# TradeValidator — Classification
# ═════════════════════════════════════════════
def test_validate_classification_backtest():
    ok, err = TradeValidator.validate_classification("backtest", None, None, None)
    assert ok is False and "version_id" in err

    ok, err = TradeValidator.validate_classification("backtest", 1, None, None)
    assert ok is True and err is None

    ok, _ = TradeValidator.validate_classification("backtest", 1, 5, None)
    assert ok is False


def test_validate_classification_real_xor():
    assert TradeValidator.validate_classification("real", 1, 5, None)[0] is True
    assert TradeValidator.validate_classification("real", 1, None, None)[0] is False
    assert TradeValidator.validate_classification("real", 1, 5, 7)[0] is False


def test_validate_classification_invalid_type():
    assert TradeValidator.validate_classification("nope", 1, None, None)[0] is False


# ═════════════════════════════════════════════
# TradeValidator — Numbers / Dates
# ═════════════════════════════════════════════
def test_validate_numbers():
    assert TradeValidator.validate_numbers(size=1, open_price=100)[0] is True
    assert TradeValidator.validate_numbers(size=0, open_price=100)[0] is False
    assert TradeValidator.validate_numbers(size=1, open_price=-1)[0] is False
    assert TradeValidator.validate_numbers(size=1, open_price=100, close_price=-5)[0] is False


def test_validate_dates():
    t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
    assert TradeValidator.validate_dates(t1)[0] is True
    assert TradeValidator.validate_dates(None)[0] is False
    assert TradeValidator.validate_dates(t2, t1)[0] is False


# ═════════════════════════════════════════════
# calculate_r_multiple
# ═════════════════════════════════════════════
def test_calculate_r_multiple():
    assert calculate_r_multiple("buy", 100, 110, 95) == 2.0
    assert calculate_r_multiple("sell", 100, 90, 105) == 2.0
    assert calculate_r_multiple("buy", 100, 110, None) is None
    assert calculate_r_multiple("buy", 100, 110, 105) is None


# ═════════════════════════════════════════════
# Endpointها
# ═════════════════════════════════════════════
def test_manual_trade_endpoint(client, db_session):
    s = Strategy(name="S1")
    db_session.add(s)
    db_session.flush()
    v = StrategyVersion(strategy_id=s.id, version_name="v1")
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)

    payload = {
        "symbol": "XAUUSD",
        "direction": "buy",
        "open_time": "2025-01-01T10:00:00Z",
        "close_time": "2025-01-01T11:00:00Z",
        "open_price": 2000,
        "close_price": 2010,
        "size": 1,
        "sl": 1995,
        "pnl": 10,
        "test_type": "backtest",
        "version_id": v.id,
    }
    r = client.post("/api/trades/manual", json=payload)
    assert r.status_code == 200
    trade_id = r.json()["id"]

    listing = client.get("/api/trades/").json()
    assert listing["total"] == 1
    assert listing["trades"][0]["symbol"] == "XAUUSD"

    detail = client.get(f"/api/trades/{trade_id}")
    assert detail.status_code == 200
    # r_multiple خودکار = (2010-2000)/(2000-1995) = 2.0
    assert detail.json()["r_multiple"] == 2.0


def test_manual_trade_invalid_classification(client):
    r = client.post("/api/trades/manual", json={
        "symbol": "XAUUSD",
        "direction": "buy",
        "open_time": "2025-01-01T10:00:00Z",
        "open_price": 2000,
        "size": 1,
        "test_type": "backtest",
    })
    assert r.status_code == 400


def test_manual_trade_invalid_direction(client):
    r = client.post("/api/trades/manual", json={
        "symbol": "XAUUSD",
        "direction": "sideways",
        "open_time": "2025-01-01T10:00:00Z",
        "open_price": 2000,
        "size": 1,
        "test_type": "backtest",
    })
    assert r.status_code == 400


def test_get_trade_not_found(client):
    assert client.get("/api/trades/9999").status_code == 404
