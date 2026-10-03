"""API contract regressions for trade enums, references, PATCH, and errors."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.api.trades import TradeUpdate
from app.models.finance import Currency
from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, TradeSource
from app.models.trading import Broker, PersonalTradingAccount
from app.utils.trade_validator import TradeReferenceNotFound, TradeValidator


def _version(db):
    strategy = Strategy(name="Phase59")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v59")
    db.add(version)
    db.flush()
    return version


def _personal_account(db):
    broker = Broker(name="Phase59Broker")
    db.add(broker)
    db.flush()
    account = PersonalTradingAccount(
        broker_id=broker.id,
        account_number="P59-1",
        currency=Currency.USDT,
        initial_balance=10000,
        current_balance=10000,
    )
    db.add(account)
    db.flush()
    return account


def _prop_stage(db):
    firm = PropFirm(name="Phase59Firm")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="P59Prop")
    db.add(account)
    db.flush()
    stage = PropStage(
        prop_account_id=account.id,
        stage_type=StageType.STAGE_1,
        status=StageStatus.ACTIVE,
        initial_balance=10000,
    )
    db.add(stage)
    db.flush()
    return stage


def _manual_payload(version_id, **kwargs):
    payload = {
        "symbol": "XAUUSD",
        "direction": "buy",
        "open_time": "2025-01-01T10:00:00Z",
        "close_time": "2025-01-01T11:00:00Z",
        "open_price": 2000,
        "close_price": 2010,
        "size": 1,
        "test_type": "backtest",
        "version_id": version_id,
        "note": "initial",
    }
    payload.update(kwargs)
    return payload


def _create_trade(client, version_id, **kwargs):
    response = client.post("/api/trades/manual", json=_manual_payload(version_id, **kwargs))
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_trade_enum_contract_http_values_and_database_names(client, db_session):
    version = _version(db_session)
    trade_id = _create_trade(client, version.id, test_type="backtest")

    response = client.get(f"/api/trades/{trade_id}")
    assert response.status_code == 200
    assert response.json()["test_type"] == "backtest"
    assert response.json()["source"] == "manual"
    stored = db_session.connection().exec_driver_sql(
        "SELECT test_type FROM trades WHERE id = ?", (trade_id,)
    ).scalar_one()
    assert stored == "BACKTEST"
    assert TestType.BACKTEST.value == "backtest"
    assert TradeSource.MANUAL.value == "manual"


def test_validate_fk_checks_version_account_and_prop_stage(db_session):
    version = _version(db_session)
    account = _personal_account(db_session)
    stage = _prop_stage(db_session)
    db_session.flush()

    TradeValidator.validate_fk(db_session, version.id, account.id, stage.id)
    with pytest.raises(TradeReferenceNotFound, match="Version not found"):
        TradeValidator.validate_fk(db_session, 98765, None, None)
    with pytest.raises(TradeReferenceNotFound, match="Personal Account not found"):
        TradeValidator.validate_fk(db_session, version.id, 98765, None)
    with pytest.raises(TradeReferenceNotFound, match="Prop Stage not found"):
        TradeValidator.validate_fk(db_session, version.id, None, 98765)


def test_manual_trade_missing_foreign_key_maps_to_404(client, db_session):
    version = _version(db_session)
    account = _personal_account(db_session)
    stage = _prop_stage(db_session)

    missing_version = client.post("/api/trades/manual", json=_manual_payload(98765))
    assert missing_version.status_code == 404
    assert missing_version.json()["detail"] == "Version not found"

    missing_personal = client.post(
        "/api/trades/manual",
        json=_manual_payload(
            version.id, test_type="real_personal", personal_trading_account_id=98765
        ),
    )
    assert missing_personal.status_code == 404
    assert missing_personal.json()["detail"] == "Personal Account not found"

    missing_stage = client.post(
        "/api/trades/manual",
        json=_manual_payload(version.id, test_type="real_prop", prop_stage_id=98765),
    )
    assert missing_stage.status_code == 404
    assert missing_stage.json()["detail"] == "Prop Stage not found"
    assert account.id and stage.id  # valid related rows were also created for isolation


def test_patch_missing_foreign_key_maps_to_404(client, db_session):
    version = _version(db_session)
    trade_id = _create_trade(client, version.id)

    response = client.patch(f"/api/trades/{trade_id}", json={"version_id": 98765})
    assert response.status_code == 404
    assert response.json()["detail"] == "Version not found"


def test_patch_omitted_fields_preserve_and_explicit_null_clears(client, db_session):
    version = _version(db_session)
    trade_id = _create_trade(client, version.id)

    omitted = client.patch(f"/api/trades/{trade_id}", json={})
    assert omitted.status_code == 200
    unchanged = client.get(f"/api/trades/{trade_id}").json()
    assert unchanged["note"] == "initial"
    assert unchanged["close_time"] is not None

    cleared = client.patch(
        f"/api/trades/{trade_id}", json={"note": None, "close_time": None, "sl": None}
    )
    assert cleared.status_code == 200, cleared.text
    result = client.get(f"/api/trades/{trade_id}").json()
    assert result["note"] is None
    assert result["close_time"] is None
    assert result["sl"] is None


def test_patch_reclassification_clears_incompatible_reference(client, db_session):
    version = _version(db_session)
    account = _personal_account(db_session)
    trade_id = _create_trade(
        client,
        version.id,
        test_type="real_personal",
        personal_trading_account_id=account.id,
    )

    response = client.patch(f"/api/trades/{trade_id}", json={"test_type": "backtest"})
    assert response.status_code == 200, response.text
    result = client.get(f"/api/trades/{trade_id}").json()
    assert result["test_type"] == "backtest"
    assert result["personal_trading_account_id"] is None
    assert result["prop_stage_id"] is None


def test_trade_errors_map_to_400_409_and_404(client, db_session, monkeypatch):
    version = _version(db_session)
    trade_id = _create_trade(client, version.id)

    invalid = client.patch(f"/api/trades/{trade_id}", json={"test_type": "unknown"})
    assert invalid.status_code == 400
    null_required = client.patch(f"/api/trades/{trade_id}", json={"symbol": None})
    assert null_required.status_code == 400

    missing = client.patch("/api/trades/98765", json={"note": "missing"})
    assert missing.status_code == 404

    def raise_integrity_error():
        raise IntegrityError("UPDATE trades", {}, Exception("constraint"))

    monkeypatch.setattr(db_session, "commit", raise_integrity_error)
    conflict = client.patch(f"/api/trades/{trade_id}", json={"note": "conflict"})
    assert conflict.status_code == 409
    assert db_session.is_active

    def raise_value_error():
        raise ValueError("invalid trade value")

    monkeypatch.setattr(db_session, "commit", raise_value_error)
    bad_value = client.patch(f"/api/trades/{trade_id}", json={"note": "bad"})
    assert bad_value.status_code == 400


def test_trade_update_dto_preserves_explicit_null_presence():
    omitted = TradeUpdate()
    explicit_null = TradeUpdate(note=None)
    assert omitted.model_dump(exclude_unset=True) == {}
    assert explicit_null.model_dump(exclude_unset=True) == {"note": None}