"""Hard-delete, import identity, and Symbol Mapping regression tests."""
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.imports import ImportBatch, ImportIdentity, ImportRowStatus, ImportStatus
from app.models.personal import Screenshot
from app.models.strategy import SymbolMapping, Trade, TradeSource, TestType
from app.utils.import_identity import build_identity_hash, normalize_utc
from tests.test_import_engine import _commit, _mt4_html, _preview_mt4, _preview_soft4x, _soft4x_row, _version, _xlsx_bytes

@pytest.fixture(autouse=True)
def _reset_import_rate_limit():
    from app.core.rate_limit import limiter
    limiter.reset()
    yield

def _make_trade(db, version_id, close_time=None):
    trade = Trade(version_id=version_id, symbol="XAUUSD", direction="buy",
        open_time=datetime(2025,1,2,10,tzinfo=timezone.utc),
        close_time=close_time or datetime(2025,1,2,12,tzinfo=timezone.utc),
        open_price=2000, close_price=2010, size=1, pnl=5,
        source=TradeSource.MANUAL, test_type=TestType.BACKTEST)
    db.add(trade); db.commit(); db.refresh(trade); return trade

def _seed_mapping(db, original="GOLD", canonical="XAUUSD"):
    if not db.query(SymbolMapping).filter_by(original_symbol=original).first():
        db.add(SymbolMapping(original_symbol=original, canonical_symbol=canonical)); db.commit()

def test_identity_hash_is_stable_and_scope_aware():
    values=dict(source="MT4_IMPORT",external_ticket="1001",symbol="XAUUSD",open_time="2025-01-02 10:00:00",close_time="2025-01-02 11:00:00")
    identity=build_identity_hash(**values,version_id=1,test_type=TestType.BACKTEST)
    assert identity==build_identity_hash(**values,version_id=1,test_type=TestType.BACKTEST)
    assert identity!=build_identity_hash(**values,version_id=2,test_type=TestType.BACKTEST)
    assert normalize_utc(values["open_time"]).isoformat().startswith("2025-01-02T10:00:00")

def test_identity_hash_is_unique_in_database(db_session):
    version=_version(db_session); a=_make_trade(db_session,version.id)
    b=_make_trade(db_session,version.id,datetime(2025,1,2,13,tzinfo=timezone.utc))
    fields=dict(source="MT4_IMPORT",symbol="XAUUSD",open_time=a.open_time,identity_hash="shared-hash")
    db_session.add(ImportIdentity(trade_id=a.id,**fields)); db_session.commit()
    db_session.add(ImportIdentity(trade_id=b.id,**fields))
    with pytest.raises(IntegrityError): db_session.commit()
    db_session.rollback()

def test_import_again_is_duplicate(client,db_session):
    version=_version(db_session); first=_preview_mt4(client,test_type="backtest",version_id=version.id).json()
    _commit(client,first["batch_id"])
    again=_preview_mt4(client,test_type="backtest",version_id=version.id).json()
    assert again["counts"][ImportRowStatus.DUPLICATE.value]==1
    assert _commit(client,again["batch_id"]).json()["imported"]==0
    assert db_session.query(Trade).count()==1

def test_hard_delete_removes_identity_and_reimport_is_new(client,db_session):
    version=_version(db_session); first=_preview_mt4(client,test_type="backtest",version_id=version.id).json()
    _commit(client,first["batch_id"]); trade_id=db_session.query(Trade).one().id
    assert db_session.query(ImportIdentity).count()==1
    assert client.delete(f"/api/trades/{trade_id}").status_code==200
    db_session.expire_all(); assert db_session.get(Trade,trade_id) is None
    assert db_session.query(ImportIdentity).count()==0
    again=_preview_mt4(client,test_type="backtest",version_id=version.id).json()
    assert again["counts"][ImportRowStatus.NEW.value]==1
    assert _commit(client,again["batch_id"]).json()["imported"]==1

def test_possible_duplicate_requires_confirmation(client,db_session):
    version=_version(db_session); _make_trade(db_session,version.id)
    preview=_preview_soft4x(client,content=_xlsx_bytes([_soft4x_row()]),test_type="backtest",version_id=version.id).json()
    assert preview["counts"][ImportRowStatus.POSSIBLE_DUPLICATE.value]==1
    assert _commit(client,preview["batch_id"]).status_code==409
    assert _commit(client,preview["batch_id"],allow=True).status_code==200

def test_duplicate_rows_inside_same_file(client,db_session):
    version=_version(db_session)
    preview=_preview_soft4x(client,content=_xlsx_bytes([_soft4x_row(),_soft4x_row()]),test_type="backtest",version_id=version.id).json()
    assert preview["counts"][ImportRowStatus.NEW.value]==1
    assert preview["counts"][ImportRowStatus.DUPLICATE.value]==1
    assert _commit(client,preview["batch_id"]).json()["imported"]==1

def test_scope_isolation_between_versions(client,db_session):
    a=_version(db_session,"A"); b=_version(db_session,"B")
    first=_preview_mt4(client,test_type="backtest",version_id=a.id).json(); _commit(client,first["batch_id"])
    second=_preview_mt4(client,test_type="backtest",version_id=b.id).json()
    assert second["counts"][ImportRowStatus.NEW.value]==1

def test_batch_counters_and_completed_at(client,db_session):
    version=_version(db_session); _make_trade(db_session,version.id)
    preview=_preview_soft4x(client,content=_xlsx_bytes([_soft4x_row(),_soft4x_row()]),test_type="backtest",version_id=version.id).json()
    batch=db_session.query(ImportBatch).one(); assert batch.duplicate==2 and batch.completed_at is None
    result=_commit(client,preview["batch_id"],allow=True).json()
    assert result["status"]==ImportStatus.COMMITTED.value and result["imported"]==1
    db_session.expire_all(); assert db_session.query(ImportBatch).one().completed_at is not None


def test_symbol_mapping_applied_and_unmapped_symbol_preserved(client, db_session):
    _seed_mapping(db_session)
    mapped_version = _version(db_session, "mapped")
    preview = _preview_mt4(client, _mt4_html(symbol="GOLD"),
                           test_type="backtest", version_id=mapped_version.id).json()
    _commit(client, preview["batch_id"])
    assert db_session.query(Trade).one().symbol == "XAUUSD"

    unmapped_version = _version(db_session, "unmapped")
    preview = _preview_mt4(client, _mt4_html(symbol="EURUSD"),
                           test_type="backtest", version_id=unmapped_version.id).json()
    _commit(client, preview["batch_id"])
    assert {t.symbol for t in db_session.query(Trade).all()} == {"XAUUSD", "EURUSD"}


def test_duplicate_after_mapping_matches_canonical_alias(client, db_session):
    _seed_mapping(db_session)
    version = _version(db_session)
    preview = _preview_mt4(client, _mt4_html(symbol="GOLD"),
                           test_type="backtest", version_id=version.id).json()
    _commit(client, preview["batch_id"])
    again = _preview_mt4(client, _mt4_html(symbol="XAUUSD"),
                         test_type="backtest", version_id=version.id).json()
    assert again["counts"][ImportRowStatus.DUPLICATE.value] == 1
    identity = db_session.query(ImportIdentity).one()
    assert identity.symbol == db_session.query(Trade).one().symbol == "XAUUSD"


def test_seed_defaults_use_project_symbol_mappings(client, db_session):
    """فاز ۲-الف: بررسی وجود همه‌ی ۱۲ مپینگ پیش‌فرض بعد از seed."""
    response = client.post("/api/symbol-mappings/seed-defaults")
    assert response.status_code == 200
    mappings = {m.original_symbol: m.canonical_symbol for m in db_session.query(SymbolMapping).all()}
    # XAUUSD family (7 variants)
    assert mappings["XAUUSD"] == "XAUUSD"
    assert mappings["XAUUSD.x"] == "XAUUSD"
    assert mappings["XAUUSD.a"] == "XAUUSD"
    assert mappings["XAUUSD.pro"] == "XAUUSD"
    assert mappings["GOLD"] == "XAUUSD"
    assert mappings["GOLD.x"] == "XAUUSD"
    assert mappings["GOLD.a"] == "XAUUSD"
    # DJIUSD family (5 variants)
    assert mappings["DJIUSD"] == "DJIUSD"
    assert mappings["DJIUSD.x"] == "DJIUSD"
    assert mappings["DJIUSD.a"] == "DJIUSD"
    assert mappings["US30"] == "DJIUSD"
    assert mappings["US30.x"] == "DJIUSD"
    assert len(mappings) == 12


def test_seed_defaults_idempotent(client, db_session):
    """فاز ۲-ب: اجرای مجدد seed نباید duplicate ایجاد کند."""
    resp1 = client.post("/api/symbol-mappings/seed-defaults")
    assert resp1.status_code == 200
    first_count = db_session.query(SymbolMapping).count()

    resp2 = client.post("/api/symbol-mappings/seed-defaults")
    assert resp2.status_code == 200
    count2 = db_session.query(SymbolMapping).count()

    assert count2 == first_count, "تعداد مپینگ‌ها نباید بعد از seed مجدد افزایش یابد"
    assert resp2.json()["created"] == [], "ردیف جدیدی نباید ساخته شود"


def test_seed_defaults_preserves_user_mappings(client, db_session):
    """فاز ۲-ج: مپینگ‌های تعریف‌شده توسط کاربر بعد از seed مجدد باقی می‌ماند."""
    # یک مپینگ کاربری اضافه کن
    client.post("/api/symbol-mappings/", json={
        "original_symbol": "MYCUSTOM",
        "canonical_symbol": "XAUUSD",
        "description": "مپینگ دستی کاربر",
    })
    assert db_session.query(SymbolMapping).filter_by(original_symbol="MYCUSTOM").count() == 1

    # seed مجدد — نباید مپینگ کاربری را حذف یا تغییر دهد
    client.post("/api/symbol-mappings/seed-defaults")
    assert db_session.query(SymbolMapping).filter_by(original_symbol="MYCUSTOM").count() == 1
    assert db_session.query(SymbolMapping).filter_by(
        original_symbol="MYCUSTOM", canonical_symbol="XAUUSD"
    ).count() == 1

    # مپینگ‌های پیش‌فرض هم ساخته شده‌اند
    assert db_session.query(SymbolMapping).filter_by(original_symbol="XAUUSD.x").count() == 1


def test_mapping_does_not_change_prices_or_size(client, db_session):
    _seed_mapping(db_session)
    version = _version(db_session)
    preview = _preview_mt4(client, _mt4_html(symbol="GOLD"),
                           test_type="backtest", version_id=version.id).json()
    _commit(client, preview["batch_id"])
    trade = db_session.query(Trade).one()
    assert trade.symbol == "XAUUSD"
    assert (trade.open_price, trade.close_price, trade.size) == (2000.0, 2010.0, 1.0)


def test_hard_delete_cleans_screenshot_row_and_file(client, db_session, tmp_path):
    version = _version(db_session)
    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    _commit(client, preview["batch_id"])
    trade = db_session.query(Trade).one()
    image = tmp_path / "trade.png"
    image.write_bytes(b"image")
    screenshot = Screenshot(entity_type="trade", entity_id=trade.id, file_path=str(image))
    db_session.add(screenshot)
    db_session.commit()
    trade_id, screenshot_id = trade.id, screenshot.id

    assert client.delete(f"/api/trades/{trade_id}").status_code == 200
    db_session.expire_all()
    assert db_session.get(Screenshot, screenshot_id) is None
    assert not image.exists()
    assert db_session.query(ImportIdentity).filter_by(trade_id=trade_id).count() == 0


