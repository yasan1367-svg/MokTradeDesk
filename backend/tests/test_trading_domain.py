"""تست‌های دامنهٔ TRADING (فاز ۲۸) — Broker / PersonalTradingAccount / Trade Contract."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.trading import (
    BrokerCreate, BrokerUpdate,
    PersonalTradingAccountCreate, PersonalTradingAccountUpdate,
)

from app.models.strategy import Trade, TradeSource, TestType, Strategy, StrategyVersion
from app.models.trading import Broker, PersonalTradingAccount
from app.models.finance import Currency
from app.utils.trade_validator import TradeValidator


def _version(db):
    s = Strategy(name="S")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name="v1")
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _pta(db, label="A"):
    b = Broker(name=f"Broker-{label}")
    db.add(b)
    db.flush()
    pta = PersonalTradingAccount(
        broker_id=b.id, account_number=f"ACC-{label}", account_label=label,
        currency=Currency.USD, initial_balance=10000.0, current_balance=10000.0,
    )
    db.add(pta)
    db.commit()
    db.refresh(pta)
    return pta


def _mk_trade(db, *, version_id, test_type, personal_trading_account_id=None, prop_stage_id=None):
    return Trade(
        version_id=version_id,
        test_type=test_type,
        personal_trading_account_id=personal_trading_account_id,
        prop_stage_id=prop_stage_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=10.0,
        source=TradeSource.MANUAL,
    )


# ═════════════════════════════════════════════
# Contract — لایهٔ Application
# ═════════════════════════════════════════════
def test_validator_truth_table():
    # BACKTEST / FORWARD
    assert TradeValidator.validate_classification("backtest", 1, None, None)[0] is True
    assert TradeValidator.validate_classification("forward", 1, None, None)[0] is True
    assert TradeValidator.validate_classification("backtest", 1, 5, None)[0] is False
    # REAL_PERSONAL
    assert TradeValidator.validate_classification("real_personal", 1, 5, None)[0] is True
    assert TradeValidator.validate_classification("real_personal", 1, None, None)[0] is False
    assert TradeValidator.validate_classification("real_personal", 1, 5, 7)[0] is False
    # REAL_PROP
    assert TradeValidator.validate_classification("real_prop", 1, None, 7)[0] is True
    assert TradeValidator.validate_classification("real_prop", 1, None, None)[0] is False
    assert TradeValidator.validate_classification("real_prop", 1, 5, 7)[0] is False
    # version_id اجباری برای همه
    assert TradeValidator.validate_classification("backtest", None, None, None)[0] is False


@pytest.mark.parametrize("schema,field,limit,extra", [
    (BrokerCreate, "name", 200, {}),
    (BrokerUpdate, "name", 200, {}),
    (PersonalTradingAccountCreate, "account_number", 100, {"broker_id": 1}),
    (PersonalTradingAccountUpdate, "account_number", 100, {}),
])
def test_trading_text_validation(schema, field, limit, extra):
    for value in ("", "   ", "x" * (limit + 1)):
        with pytest.raises(ValidationError):
            schema(**extra, **{field: value})
    assert getattr(schema(**extra, **{field: "  valid  "}), field) == "valid"
    assert getattr(schema(**extra, **{field: "x" * limit}), field) == "x" * limit


@pytest.mark.parametrize("schema,field", [
    (BrokerUpdate, "name"),
    (PersonalTradingAccountUpdate, "account_number"),
])
def test_trading_patch_accepts_omitted_and_null_text(schema, field):
    assert schema().model_dump(exclude_unset=True) == {}
    assert schema(**{field: None}).model_dump(exclude_unset=True) == {field: None}


@pytest.mark.parametrize("schema,extra", [
    (PersonalTradingAccountCreate, {"broker_id": 1, "account_number": "123"}),
    (PersonalTradingAccountUpdate, {}),
])
@pytest.mark.parametrize("field", ["initial_balance", "current_balance"])
def test_trading_balance_validation(schema, extra, field):
    with pytest.raises(ValidationError):
        schema(**extra, **{field: -1})
    for value in (0, 100):
        assert getattr(schema(**extra, **{field: value}), field) == value


@pytest.mark.parametrize("resource,field", [
    ("brokers", "name"), ("accounts", "account_number"),
])
def test_trading_api_rejects_blank_text(client, db_session, resource, field):
    account = _pta(db_session)
    resource_id = account.broker_id if resource == "brokers" else account.id
    payload = {field: "   "}
    if resource == "accounts":
        payload["broker_id"] = account.broker_id
    response = client.post(f"/api/trading/{resource}", json=payload)
    assert response.status_code == 422, response.text
    response = client.patch(f"/api/trading/{resource}/{resource_id}", json={field: "   "})
    assert response.status_code == 422, response.text


# ═════════════════════════════════════════════
# Contract — لایهٔ DB (CheckConstraint)
# ═════════════════════════════════════════════
def test_check_constraint_blocks_invalid_real_personal(db_session):
    v = _version(db_session)
    # REAL_PERSONAL بدون حساب → نقض CHECK
    with pytest.raises(IntegrityError):
        db_session.add(_mk_trade(db_session, version_id=v.id, test_type=TestType.REAL_PERSONAL))
        db_session.commit()
    db_session.rollback()


def test_check_constraint_blocks_backtest_with_prop(db_session):
    v = _version(db_session)
    # BACKTEST با prop_stage_id → نقض CHECK
    with pytest.raises(IntegrityError):
        db_session.add(_mk_trade(
            db_session, version_id=v.id, test_type=TestType.BACKTEST, prop_stage_id=1
        ))
        db_session.commit()
    db_session.rollback()


def test_check_constraint_allows_valid_real_personal(db_session):
    v = _version(db_session)
    pta = _pta(db_session)
    db_session.add(_mk_trade(
        db_session, version_id=v.id, test_type=TestType.REAL_PERSONAL,
        personal_trading_account_id=pta.id,
    ))
    db_session.commit()
    assert db_session.query(Trade).count() == 1


# ═════════════════════════════════════════════
# API دامنهٔ TRADING
# ═════════════════════════════════════════════
def test_broker_and_personal_account_api(client):
    r = client.post("/api/trading/brokers", json={"name": "IC Markets"})
    assert r.status_code == 200, r.text
    broker_id = r.json()["id"]

    r = client.post("/api/trading/accounts", json={
        "broker_id": broker_id,
        "account_number": "12345",
        "account_label": "Main",
        "currency": "USD",
        "initial_balance": 5000,
    })
    assert r.status_code == 200, r.text

    accounts = client.get("/api/trading/accounts").json()
    assert len(accounts) == 1
    assert accounts[0]["broker_name"] == "IC Markets"
    assert accounts[0]["current_balance"] == 5000

    brokers = client.get("/api/trading/brokers").json()
    assert brokers[0]["name"] == "IC Markets"


def test_personal_account_requires_existing_broker(client):
    r = client.post("/api/trading/accounts", json={
        "broker_id": 9999, "account_number": "1",
    })
    assert r.status_code == 404


@pytest.mark.parametrize("resource", ["accounts", "brokers"])
@pytest.mark.parametrize("with_movement", [False, True])
def test_delete_with_trades_returns_409(client, db_session, resource, with_movement):
    from app.models.finance import AccountType, FinancialAccount

    version = _version(db_session)
    account = _pta(db_session)
    for _ in range(2):
        db_session.add(_mk_trade(
            db_session, version_id=version.id, test_type=TestType.REAL_PERSONAL,
            personal_trading_account_id=account.id,
        ))
    db_session.commit()
    if with_movement:
        wallet = FinancialAccount(
            name="Wallet", type=AccountType.BANK, currency=account.currency, balance=0,
        )
        db_session.add(wallet)
        db_session.commit()
        response = client.post("/api/broker/cash-movements", json={
            "personal_trading_account_id": account.id,
            "financial_account_id": wallet.id,
            "direction": "withdrawal_from_broker",
            "amount": 10,
            "date": "2026-10-02T09:00:00Z",
        })
        assert response.status_code == 200, response.text

    resource_id = account.id if resource == "accounts" else account.broker_id
    response = client.delete(f"/api/trading/{resource}/{resource_id}")
    assert response.status_code == 409, response.text
    expected = (
        "این حساب 2 معامله دارد؛ ابتدا معاملات را حذف یا جابجا کن"
        if resource == "accounts" else
        "حساب‌های این بروکر 2 معامله دارند؛ ابتدا معاملات را حذف یا جابجا کن"
    )
    assert response.json()["detail"] == expected
    assert db_session.get(PersonalTradingAccount, account.id) is not None
    assert db_session.get(Broker, account.broker_id) is not None
    assert db_session.query(Trade).filter(
        Trade.personal_trading_account_id == account.id
    ).count() == 2


@pytest.mark.parametrize("resource", ["accounts", "brokers"])
def test_delete_without_trades_or_movements(client, db_session, resource):
    account = _pta(db_session)
    account_id = account.id
    resource_id = account.id if resource == "accounts" else account.broker_id
    response = client.delete(f"/api/trading/{resource}/{resource_id}")
    assert response.status_code == 200, response.text
    assert db_session.query(PersonalTradingAccount).filter_by(id=account_id).count() == 0
