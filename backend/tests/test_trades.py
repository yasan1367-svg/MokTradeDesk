"""تست‌های TradeValidator و endpointهای معاملات (فاز ۱۲ + فاز ۲۵)"""
from datetime import datetime, timezone

from app.models.strategy import (
    Strategy, StrategyVersion, Trade, TradeSource, TestType,
)
from app.utils.trade_metrics import calculate_r_multiple
from app.utils.trade_validator import TradeValidator


def _mk_trade(db, *, source=TradeSource.MANUAL, symbol="XAUUSD", pnl=10.0):
    """ساخت سریع یک معامله در دیتابیس تست"""
    t = Trade(
        symbol=symbol,
        direction="buy",
        open_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        source=source,
        test_type=TestType.BACKTEST,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


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


# ═════════════════════════════════════════════
# Phase 25 — Soft Delete + Batch Delete
# ═════════════════════════════════════════════
def test_soft_delete_mt4_trade(client, db_session):
    """معامله‌ی MT4 (که قبلاً غیرقابل‌حذف بود) اکنون Soft Delete می‌شود."""
    t = _mk_trade(db_session, source=TradeSource.MT4_IMPORT)

    r = client.delete(f"/api/trades/{t.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["hard"] is False
    assert body["count"] == 1

    # داده در دیتابیس باقی می‌ماند ولی is_deleted=True
    db_session.refresh(t)
    assert t.is_deleted is True

    # از لیست و جزئیات پنهان می‌شود
    listing = client.get("/api/trades/").json()
    assert all(x["id"] != t.id for x in listing["trades"])
    assert client.get(f"/api/trades/{t.id}").status_code == 404


def test_soft_delete_soft4x_trade(client, db_session):
    """معامله‌ی Soft4X اکنون Soft Delete می‌شود."""
    t = _mk_trade(db_session, source=TradeSource.SOFT4X_IMPORT, symbol="DJIUSD")

    r = client.delete(f"/api/trades/{t.id}")
    assert r.status_code == 200, r.text
    assert r.json()["hard"] is False

    db_session.refresh(t)
    assert t.is_deleted is True
    assert client.get(f"/api/trades/{t.id}").status_code == 404


def test_soft_delete_is_idempotent(client, db_session):
    """حذف دوباره‌ی همان معامله خطا نمی‌دهد و count=0 است."""
    t = _mk_trade(db_session, source=TradeSource.MT4_IMPORT)
    assert client.delete(f"/api/trades/{t.id}").json()["count"] == 1
    second = client.delete(f"/api/trades/{t.id}")
    assert second.status_code == 200
    assert second.json()["count"] == 0


def test_batch_delete_soft(client, db_session):
    """حذف گروهی معاملات با منابع مختلف → همه Soft Delete می‌شوند."""
    a = _mk_trade(db_session, source=TradeSource.MT4_IMPORT, symbol="XAUUSD")
    b = _mk_trade(db_session, source=TradeSource.SOFT4X_IMPORT, symbol="DJIUSD")
    c = _mk_trade(db_session, source=TradeSource.MANUAL, symbol="XAUUSD")

    r = client.post(
        "/api/trades/batch-delete",
        json={"trade_ids": [a.id, b.id, c.id]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted"] == 3
    assert body["skipped"] == []
    assert body["hard"] is False

    for t in (a, b, c):
        db_session.refresh(t)
        assert t.is_deleted is True

    assert client.get("/api/trades/").json()["total"] == 0


def test_batch_delete_reports_skipped(client, db_session):
    """شناسه‌های ناموجود در فیلد skipped گزارش می‌شوند."""
    t = _mk_trade(db_session, source=TradeSource.MT4_IMPORT)
    r = client.post(
        "/api/trades/batch-delete",
        json={"trade_ids": [t.id, 9999]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] == 1
    assert 9999 in body["skipped"]


def test_batch_delete_empty_list_rejected(client):
    r = client.post("/api/trades/batch-delete", json={"trade_ids": []})
    assert r.status_code == 400


def test_hard_delete_trade(client, db_session):
    """حذف کامل (hard=true) رکورد را از دیتابیس پاک می‌کند."""
    t = _mk_trade(db_session, source=TradeSource.MT4_IMPORT)
    tid = t.id

    r = client.delete(f"/api/trades/{tid}?hard=true")
    assert r.status_code == 200, r.text
    assert r.json()["hard"] is True

    from sqlalchemy import select
    remaining = db_session.execute(
        select(Trade).where(Trade.id == tid)
    ).first()
    assert remaining is None


def test_batch_hard_delete(client, db_session):
    a = _mk_trade(db_session, source=TradeSource.MT4_IMPORT)
    b = _mk_trade(db_session, source=TradeSource.SOFT4X_IMPORT)
    r = client.post(
        "/api/trades/batch-delete",
        json={"trade_ids": [a.id, b.id], "hard": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] == 2

    from sqlalchemy import select, func
    count = db_session.execute(select(func.count()).select_from(Trade)).scalar()
    assert count == 0
