"""تست‌های TradeValidator و endpointهای معاملات (فاز ۱۲ + فاز ۲۵)"""
from datetime import datetime, timezone

from app.models.strategy import (
    Strategy, StrategyVersion, Trade, TradeSource, TestType,
)
from app.utils.trade_metrics import calculate_r_multiple
from app.utils.trade_validator import TradeValidator


def _mk_version(db, name="v1"):
    """نسخه‌ی استراتژی — چون version_id اکنون اجباری است (فاز ۲۸)"""
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _mk_trade(db, *, source=TradeSource.MANUAL, symbol="XAUUSD", pnl=10.0, version_id=None):
    """ساخت سریع یک معامله در دیتابیس تست"""
    if version_id is None:
        version_id = _mk_version(db, name=f"v-{symbol}").id
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
        version_id=version_id,
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


def test_validate_classification_real_personal():
    # REAL_PERSONAL: version_id + personal_trading_account_id اجباری، prop ممنوع
    assert TradeValidator.validate_classification("real_personal", 1, 5, None)[0] is True
    assert TradeValidator.validate_classification("real_personal", 1, None, None)[0] is False
    assert TradeValidator.validate_classification("real_personal", 1, 5, 7)[0] is False


def test_validate_classification_real_prop():
    # REAL_PROP: version_id + prop_stage_id اجباری، حساب شخصی ممنوع (XOR)
    assert TradeValidator.validate_classification("real_prop", 1, None, 7)[0] is True
    assert TradeValidator.validate_classification("real_prop", 1, None, None)[0] is False
    assert TradeValidator.validate_classification("real_prop", 1, 5, 7)[0] is False


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
# فاز ۳۸.۵ — ثبت معاملهٔ دستی با دامنهٔ REAL (قرارداد فاز ۲۷)
# ═════════════════════════════════════════════
def _mk_pta(db, label="IC-1"):
    """بروکر + حساب معاملاتی شخصی (دامنهٔ REAL_PERSONAL)"""
    from app.models.finance import Currency
    from app.models.trading import Broker, PersonalTradingAccount

    b = Broker(name=f"B-{label}")
    db.add(b)
    db.flush()
    a = PersonalTradingAccount(
        broker_id=b.id, account_number=label, account_label=label,
        currency=Currency.USD, initial_balance=1000.0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _manual_payload(version_id, **extra):
    base = {
        "symbol": "XAUUSD",
        "direction": "buy",
        "open_time": "2025-01-01T10:00:00Z",
        "open_price": 2000,
        "size": 1,
        "version_id": version_id,
    }
    base.update(extra)
    return base


def _mk_prop_stage(db, label="sync"):
    from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType

    firm = PropFirm(name=f"Sync firm {label}")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label=f"Sync account {label}")
    db.add(account)
    db.flush()
    stage = PropStage(
        prop_account_id=account.id,
        stage_type=StageType.STAGE_1,
        status=StageStatus.ACTIVE,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


def test_manual_trade_real_personal_accepts_personal_trading_account(client, db_session):
    """فاز ۳۸.۵: `personal_trading_account_id` معتبر است (جایگزین منسوخ `finance_account_id`)."""
    v = _mk_version(db_session, name="rp")
    pta = _mk_pta(db_session)

    r = client.post("/api/trades/manual", json=_manual_payload(
        v.id, test_type="real_personal", personal_trading_account_id=pta.id,
    ))
    assert r.status_code == 200, r.text

    detail = client.get(f"/api/trades/{r.json()['id']}").json()
    assert detail["test_type"] == "real_personal"
    assert detail["personal_trading_account_id"] == pta.id
    assert detail["personal_trading_account_name"] == "IC-1"
    assert detail["prop_stage_id"] is None


def test_manual_trade_legacy_real_test_type_rejected(client, db_session):
    """فاز ۳۸.۵: مقدار قدیمی `test_type='real'` (که فرانت می‌فرستاد) نامعتبر است."""
    v = _mk_version(db_session, name="legacy")

    r = client.post("/api/trades/manual", json=_manual_payload(v.id, test_type="real"))
    assert r.status_code == 400
    assert "نوع تست نامعتبر" in r.json()["detail"]


def test_manual_trade_real_prop_requires_prop_stage(client, db_session):
    """REAL_PROP بدون prop_stage_id ⇒ ۴۰۰ (TradeValidator)"""
    v = _mk_version(db_session, name="rprop")

    r = client.post("/api/trades/manual", json=_manual_payload(v.id, test_type="real_prop"))
    assert r.status_code == 400
    assert "prop_stage_id" in r.json()["detail"]


def test_manual_real_prop_trade_syncs_stage(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    version = _mk_version(db_session, name="manual-prop-sync")
    stage = _mk_prop_stage(db_session, label="manual")
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.post(
        "/api/trades/manual",
        json=_manual_payload(
            version.id, test_type="real_prop", prop_stage_id=stage.id,
        ),
    )

    assert response.status_code == 200, response.text
    assert synced == [stage.id]


def test_manual_real_personal_trade_does_not_sync_stage(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    version = _mk_version(db_session, name="manual-personal-sync")
    account = _mk_pta(db_session, label="manual-personal")
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.post(
        "/api/trades/manual",
        json=_manual_payload(
            version.id,
            test_type="real_personal",
            personal_trading_account_id=account.id,
        ),
    )

    assert response.status_code == 200, response.text
    assert synced == []


def test_patch_stage_reassignment_syncs_old_and_new_stages(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    version = _mk_version(db_session, name="patch-stage-reassignment")
    old_stage = _mk_prop_stage(db_session, label="patch-old")
    new_stage = _mk_prop_stage(db_session, label="patch-new")
    trade = _mk_trade(db_session, version_id=version.id)
    trade.test_type = TestType.REAL_PROP
    trade.prop_stage_id = old_stage.id
    db_session.commit()
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.patch(
        f"/api/trades/{trade.id}",
        json={"test_type": "real_prop", "prop_stage_id": new_stage.id},
    )

    assert response.status_code == 200, response.text
    assert set(synced) == {old_stage.id, new_stage.id}
    assert len(synced) == 2


def test_patch_unchanged_stage_skips_sync(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    version = _mk_version(db_session, name="patch-same-stage")
    stage = _mk_prop_stage(db_session, label="patch-same")
    trade = _mk_trade(db_session, version_id=version.id)
    trade.test_type = TestType.REAL_PROP
    trade.prop_stage_id = stage.id
    db_session.commit()
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.patch(f"/api/trades/{trade.id}", json={"note": "unchanged stage"})

    assert response.status_code == 200, response.text
    assert synced == []


def test_patch_clearing_stage_syncs_only_old_stage(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    version = _mk_version(db_session, name="patch-clear-stage")
    stage = _mk_prop_stage(db_session, label="patch-clear")
    trade = _mk_trade(db_session, version_id=version.id)
    trade.test_type = TestType.REAL_PROP
    trade.prop_stage_id = stage.id
    db_session.commit()
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.patch(f"/api/trades/{trade.id}", json={"test_type": "backtest"})

    assert response.status_code == 200, response.text
    assert synced == [stage.id]


def test_patch_assigning_stage_syncs_only_new_stage(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    version = _mk_version(db_session, name="patch-assign-stage")
    stage = _mk_prop_stage(db_session, label="patch-assign")
    trade = _mk_trade(db_session, version_id=version.id)
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.patch(
        f"/api/trades/{trade.id}",
        json={"test_type": "real_prop", "prop_stage_id": stage.id},
    )

    assert response.status_code == 200, response.text
    assert synced == [stage.id]


def test_get_trades_filters_by_prop_account(client, db_session):
    """Prop-account filtering follows Trade → PropStage → PropAccount."""
    from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType

    firm = PropFirm(name="Filter firm")
    db_session.add(firm)
    db_session.flush()
    account_a = PropAccount(prop_firm_id=firm.id, account_label="Account A")
    account_b = PropAccount(prop_firm_id=firm.id, account_label="Account B")
    db_session.add_all([account_a, account_b])
    db_session.flush()
    stage_a = PropStage(prop_account_id=account_a.id, stage_type=StageType.STAGE_1, status=StageStatus.ACTIVE)
    stage_b = PropStage(prop_account_id=account_b.id, stage_type=StageType.STAGE_1, status=StageStatus.ACTIVE)
    db_session.add_all([stage_a, stage_b])
    db_session.commit()

    first = _mk_trade(db_session, symbol="XAUUSD")
    first.test_type = TestType.REAL_PROP
    first.prop_stage_id = stage_a.id
    second = _mk_trade(db_session, symbol="DJIUSD")
    second.test_type = TestType.REAL_PROP
    second.prop_stage_id = stage_b.id
    db_session.commit()

    response = client.get("/api/trades/", params={"prop_account_id": account_a.id})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [trade["symbol"] for trade in body["trades"]] == ["XAUUSD"]


def test_manual_trade_backtest_rejects_personal_account(client, db_session):
    """BACKTEST نباید personal_trading_account_id داشته باشد"""
    v = _mk_version(db_session, name="bt")
    pta = _mk_pta(db_session, label="IC-2")

    r = client.post("/api/trades/manual", json=_manual_payload(
        v.id, test_type="backtest", personal_trading_account_id=pta.id,
    ))
    assert r.status_code == 400
    assert "personal_trading_account_id" in r.json()["detail"]


# ═════════════════════════════════════════════
# Permanent Delete + Batch Delete
# ═════════════════════════════════════════════
def test_normal_delete_permanently_removes_trade(client, db_session):
    """DELETE عادی باید معامله را از DB و GET حذف کند."""
    t = _mk_trade(db_session, source=TradeSource.MT4_IMPORT)
    trade_id = t.id

    response = client.delete(f"/api/trades/{trade_id}")
    assert response.status_code == 200, response.text
    assert response.json()["count"] == 1

    db_session.expire_all()
    assert db_session.get(Trade, trade_id) is None
    assert client.get(f"/api/trades/{trade_id}").status_code == 404
    assert client.get("/api/trades/").json()["total"] == 0


def test_sync_failure_does_not_break_trade_delete(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    stage = _mk_prop_stage(db_session, label="delete-sync-failure")
    trade = _mk_trade(db_session)
    trade.test_type = TestType.REAL_PROP
    trade.prop_stage_id = stage.id
    db_session.commit()

    def fail_sync(db, stage_id):
        raise RuntimeError("sync failed")

    monkeypatch.setattr(trades_api, "sync_prop_stage_profit", fail_sync)

    response = client.delete(f"/api/trades/{trade.id}")

    assert response.status_code == 200, response.text
    assert response.json()["count"] == 1
    db_session.expire_all()
    assert db_session.get(Trade, trade.id) is None


def test_delete_syncs_trade_stage(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    stage = _mk_prop_stage(db_session, label="delete-sync")
    trade = _mk_trade(db_session)
    trade.test_type = TestType.REAL_PROP
    trade.prop_stage_id = stage.id
    db_session.commit()
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.delete(f"/api/trades/{trade.id}")

    assert response.status_code == 200, response.text
    assert synced == [stage.id]


def test_delete_removes_import_identity_and_allows_reimport(client, db_session):
    """DELETE عادی Identity را هم حذف می‌کند؛ همان import دیگر duplicate نیست."""
    from app.models.imports import ImportIdentity, ImportRowStatus
    from tests.test_import_engine import _commit, _preview_mt4, _version

    version = _version(db_session)
    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    _commit(client, preview["batch_id"])
    trade = db_session.query(Trade).one()
    trade_id = trade.id
    assert db_session.query(ImportIdentity).count() == 1

    response = client.delete(f"/api/trades/{trade_id}")
    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.query(ImportIdentity).count() == 0

    again = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert again["counts"][ImportRowStatus.NEW.value] == 1
    assert _commit(client, again["batch_id"]).json()["imported"] == 1


def test_delete_removes_trade_screenshot_rows_and_files(client, db_session, tmp_path):
    """Screenshot ارجاع FK به trade ندارد؛ DELETE باید ردیف و فایل را صریحاً پاک کند."""
    from app.models.personal import Screenshot

    trade = _mk_trade(db_session, source=TradeSource.SOFT4X_IMPORT, symbol="DJIUSD")
    image = tmp_path / "trade-shot.png"
    image.write_bytes(b"screenshot")
    db_session.add(Screenshot(
        entity_type="trade", entity_id=trade.id, file_path=str(image),
    ))
    db_session.commit()
    screenshot_id = db_session.query(Screenshot).one().id

    response = client.delete(f"/api/trades/{trade.id}")
    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Screenshot, screenshot_id) is None
    assert not image.exists()


def test_delete_cleans_review_screenshots_and_financial_trade_reference(client, db_session, tmp_path):
    """حذف review وابسته و تصاویرش بدون FK cascade مستقیم، و null کردن FK مالی nullable."""
    from app.models.finance import AccountType, FinancialAccount, FinancialTransaction, Currency, TransactionType
    from app.models.personal import JournalReview, Screenshot

    trade = _mk_trade(db_session)
    review = JournalReview(trade_id=trade.id, notes="review")
    db_session.add(review)
    db_session.flush()
    image = tmp_path / "review-shot.png"
    image.write_bytes(b"review screenshot")
    shot = Screenshot(
        entity_type="review", entity_id=review.id, review_id=review.id,
        file_path=str(image),
    )
    db_session.add(shot)

    account = FinancialAccount(name="Delete test account", type=AccountType.BANK, currency=Currency.USD)
    db_session.add(account)
    db_session.flush()
    tx = FinancialTransaction(
        account_id=account.id, amount=1.0, currency=Currency.USD,
        type=TransactionType.ADJUSTMENT, related_trade_id=trade.id,
    )
    db_session.add(tx)
    db_session.commit()
    review_id, shot_id, tx_id, trade_id = review.id, shot.id, tx.id, trade.id

    response = client.delete(f"/api/trades/{trade_id}")
    assert response.status_code == 200, response.text
    db_session.expire_all()
    assert db_session.get(JournalReview, review_id) is None
    assert db_session.get(Screenshot, shot_id) is None
    assert not image.exists()
    assert db_session.get(FinancialTransaction, tx_id).related_trade_id is None


def test_batch_delete_permanently_removes_trades(client, db_session):
    """حذف گروهی دائمی همه‌ی منابع معامله را حذف می‌کند."""
    a = _mk_trade(db_session, source=TradeSource.MT4_IMPORT, symbol="XAUUSD")
    b = _mk_trade(db_session, source=TradeSource.SOFT4X_IMPORT, symbol="DJIUSD")
    c = _mk_trade(db_session, source=TradeSource.MANUAL, symbol="XAUUSD")
    ids = [a.id, b.id, c.id]

    response = client.post("/api/trades/batch-delete", json={"trade_ids": ids})
    assert response.status_code == 200, response.text
    assert response.json()["deleted"] == 3
    assert response.json()["skipped"] == []
    db_session.expire_all()
    assert db_session.query(Trade).count() == 0
    assert client.get("/api/trades/").json()["total"] == 0


def test_batch_delete_syncs_each_affected_stage_once(client, db_session, monkeypatch):
    from app.api import trades as trades_api

    version = _mk_version(db_session, name="batch-stage-sync")
    stage_a = _mk_prop_stage(db_session, label="batch-a")
    stage_b = _mk_prop_stage(db_session, label="batch-b")
    trades = [_mk_trade(db_session, version_id=version.id, symbol=f"SYM{i}") for i in range(3)]
    for trade, stage in zip(trades, (stage_a, stage_a, stage_b)):
        trade.test_type = TestType.REAL_PROP
        trade.prop_stage_id = stage.id
    db_session.commit()
    synced = []
    monkeypatch.setattr(
        trades_api, "sync_prop_stage_profit", lambda db, stage_id: synced.append(stage_id)
    )

    response = client.post(
        "/api/trades/batch-delete",
        json={"trade_ids": [trade.id for trade in trades]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["deleted"] == len(trades)
    assert set(synced) == {stage_a.id, stage_b.id}
    assert len(synced) == 2


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
    """Compatibility: optional old hard=true query still performs hard delete."""
    t = _mk_trade(db_session, source=TradeSource.MT4_IMPORT)
    tid = t.id

    r = client.delete(f"/api/trades/{tid}?hard=true")
    assert r.status_code == 200, r.text

    from sqlalchemy import select
    remaining = db_session.execute(select(Trade).where(Trade.id == tid)).first()
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
