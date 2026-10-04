"""Hard-delete trade regressions replacing the former soft-delete filter tests."""
from datetime import datetime, timezone

from app.models.imports import ImportIdentity
from app.models.personal import Screenshot
from app.models.strategy import Strategy, StrategyVersion, Trade, TradeSource, TestType


def _trade(db):
    strategy = Strategy(name="hard-delete-test")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db.add(version)
    db.flush()
    trade = Trade(
        version_id=version.id, symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 3, 1, 10, tzinfo=timezone.utc),
        close_time=datetime(2025, 3, 1, 11, tzinfo=timezone.utc),
        open_price=2000.0, close_price=2010.0, size=1.0, pnl=100.0,
        commission=0.0, swap=0.0, source=TradeSource.MANUAL,
        test_type=TestType.BACKTEST,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def test_delete_permanently_removes_trade_from_database_and_get(client, db_session):
    trade = _trade(db_session)
    trade_id = trade.id
    response = client.delete(f"/api/trades/{trade_id}")
    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Trade, trade_id) is None
    assert client.get(f"/api/trades/{trade_id}").status_code == 404
    assert all(row["id"] != trade_id for row in client.get("/api/trades/").json()["trades"])


def test_delete_cleans_import_identity_and_screenshot_file_and_row(client, db_session, tmp_path):
    trade = _trade(db_session)
    db_session.add(ImportIdentity(
        trade_id=trade.id, source="MT4_IMPORT", symbol=trade.symbol,
        open_time=trade.open_time, identity_hash="hard-delete-regression",
    ))
    path = tmp_path / "delete-shot.png"
    path.write_bytes(b"image")
    screenshot = Screenshot(entity_type="trade", entity_id=trade.id, file_path=str(path))
    db_session.add(screenshot)
    db_session.commit()
    trade_id, screenshot_id = trade.id, screenshot.id

    assert client.delete(f"/api/trades/{trade_id}").status_code == 200
    db_session.expire_all()
    assert db_session.query(ImportIdentity).filter_by(trade_id=trade_id).count() == 0
    assert db_session.get(Screenshot, screenshot_id) is None
    assert not path.exists()


def test_normal_trade_response_has_no_deleted_flag(client, db_session):
    trade = _trade(db_session)
    body = client.get(f"/api/trades/{trade.id}").json()
    assert body["id"] == trade.id
    assert "is_deleted" not in body
