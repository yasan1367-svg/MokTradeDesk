"""تست‌های Phase 33 — Prop Withdrawal (چرخه‌ی عمر + یکپارچگی مالی).

پوشش:
- وضعیت پیش‌فرض REQUESTED (بدون درآمد)
- ثبت درآمد فقط در نقطه‌ی RECEIVED
- رد انتقال وضعیت نامعتبر
- انتقال بین حساب‌ها = درآمد نیست
- ویرایش/حذف با برگشت اثر مالی
"""
from datetime import datetime, timezone


from app.models.prop import (
    PropFirm, PropAccount, PropStage, StageType, StageStatus,
    WithdrawalStatus,
)
from app.models.finance import FinancialAccount, AccountType, Currency, FinancialTransaction, TransactionType
from app.models.strategy import Trade, TradeSource, TestType, Strategy, StrategyVersion


def _version(db):
    s = Strategy(name="S")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name="v1")
    db.add(v)
    db.flush()
    return v


def _trade(pnl, close_day, stage_id, version_id):
    return Trade(
        symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, close_day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, close_day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0, close_price=2000.0, size=1.0, pnl=pnl,
        source=TradeSource.MANUAL, test_type=TestType.REAL_PROP,
        prop_stage_id=stage_id, version_id=version_id,
    )


def _funded_stage(db, profit=1500.0, profit_share=80.0):
    """مرحله رییل با سود ۱۵۰۰ ⇒ قابل برداشت = 1500*0.8 = 1200"""
    firm = PropFirm(name="FTMO")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="A1")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id, stage_type=StageType.FUNDED_REAL,
        status=StageStatus.ACTIVE, initial_balance=10000.0,
        profit_target=1000.0, max_daily_dd=500.0, max_total_dd=1000.0,
        min_trading_days=3, profit_share_percentage=profit_share,
        total_withdrawn=0.0,
    )
    db.add(stage)
    db.flush()
    v = _version(db)
    db.add(_trade(1000, 1, stage.id, v.id))
    db.add(_trade(500, 2, stage.id, v.id))
    db.commit()
    db.refresh(stage)
    return stage


def _account(db, name="Trust Wallet", acc_type=AccountType.CRYPTO_WALLET):
    a = FinancialAccount(name=name, type=acc_type, currency=Currency.USD, balance=0.0)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _create(client, stage_id, dest_id, amount=500.0, **extra):
    payload = {"prop_stage_id": stage_id, "amount": amount,
               "destination_account_id": dest_id, **extra}
    return client.post("/api/prop/payouts", json=payload)


# ═════════════════════════════════════════════
# create → REQUESTED (بدون درآمد)
# ═════════════════════════════════════════════
def test_create_withdrawal_default_requested_no_income(client, db_session):
    stage = _funded_stage(db_session)
    dest = _account(db_session)

    r = _create(client, stage.id, dest.id, 500.0)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "requested"
    assert body["transaction_id"] is None

    db_session.refresh(dest)
    assert dest.balance == 0.0
    assert db_session.query(FinancialTransaction).count() == 0
    db_session.refresh(stage)
    assert (stage.total_withdrawn or 0.0) == 0.0


def test_validation_only_funded_stage(client, db_session):
    firm = PropFirm(name="FTMO")
    db_session.add(firm)
    db_session.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="A1")
    db_session.add(acc)
    db_session.flush()
    stage = PropStage(prop_account_id=acc.id, stage_type=StageType.STAGE_1,
                      status=StageStatus.ACTIVE, initial_balance=10000.0)
    db_session.add(stage)
    db_session.commit()
    dest = _account(db_session)

    r = _create(client, stage.id, dest.id, 100.0)
    assert r.status_code == 400


def test_validation_amount_over_withdrawable(client, db_session):
    stage = _funded_stage(db_session)  # withdrawable = 1200
    dest = _account(db_session)

    r = _create(client, stage.id, dest.id, 1300.0)
    assert r.status_code == 400
    assert "قابل برداشت" in r.json()["detail"]


# ═════════════════════════════════════════════
# lifecycle → income at RECEIVED
# ═════════════════════════════════════════════
def test_status_transitions_and_income_at_received(client, db_session):
    stage = _funded_stage(db_session)
    dest = _account(db_session)
    pid = _create(client, stage.id, dest.id, 500.0).json()["id"]

    # REQUESTED → APPROVED → PROCESSING (هنوز بدون درآمد)
    for target in ("approved", "processing"):
        r = client.post(f"/api/prop/payouts/{pid}/status", json={"status": target})
        assert r.status_code == 200
        assert r.json()["payout"]["status"] == target
        assert r.json()["income_transaction_id"] is None
    assert db_session.query(FinancialTransaction).count() == 0

    # PROCESSING → RECEIVED (در کیف‌پول فقط دارایی ثبت می‌شود، نه درآمد)
    r = client.post(f"/api/prop/payouts/{pid}/status", json={"status": "received"})
    assert r.status_code == 200
    tx_id = r.json()["income_transaction_id"]
    assert tx_id is None

    tx = db_session.query(FinancialTransaction).first()
    assert tx is not None
    assert tx.type == TransactionType.ADJUSTMENT
    assert tx.amount == 500.0

    db_session.refresh(dest)
    assert dest.balance == 500.0
    db_session.refresh(stage)
    assert stage.total_withdrawn == 500.0

    summary = client.get("/api/finance/summary").json()
    assert summary["total_income"] == 0.0

    # idempotent: دوباره RECEIVED ⇒ تراکنش جدید ساخته نمی‌شود
    r = client.post(f"/api/prop/payouts/{pid}/status", json={"status": "received"})
    assert r.status_code == 200
    assert db_session.query(FinancialTransaction).count() == 1


def test_bank_payout_is_profit_income(client, db_session):
    stage = _funded_stage(db_session)
    bank = _account(db_session, "Bank", AccountType.BANK)
    pid = _create(client, stage.id, bank.id, 500.0).json()["id"]

    for target in ("approved", "processing", "received"):
        response = client.post(f"/api/prop/payouts/{pid}/status", json={"status": target})
        assert response.status_code == 200

    tx = db_session.query(FinancialTransaction).first()
    assert tx is not None
    assert tx.type == TransactionType.PROFIT
    assert tx.amount == 500.0
    assert client.get("/api/finance/summary").json()["total_income"] == 500.0


def test_invalid_transition_rejected(client, db_session):
    stage = _funded_stage(db_session)
    dest = _account(db_session)
    pid = _create(client, stage.id, dest.id, 200.0).json()["id"]

    # REQUESTED → RECEIVED مجاز نیست (باید از APPROVED/PROCESSING بگذرد)
    r = client.post(f"/api/prop/payouts/{pid}/status", json={"status": "received"})
    assert r.status_code == 400
    assert db_session.query(FinancialTransaction).count() == 0


def test_cancel_records_no_income(client, db_session):
    stage = _funded_stage(db_session)
    dest = _account(db_session)
    pid = _create(client, stage.id, dest.id, 300.0).json()["id"]

    r = client.post(f"/api/prop/payouts/{pid}/status", json={"status": "cancelled"})
    assert r.status_code == 200
    assert r.json()["payout"]["status"] == "cancelled"
    assert db_session.query(FinancialTransaction).count() == 0
    db_session.refresh(dest)
    assert dest.balance == 0.0
    db_session.refresh(stage)
    assert (stage.total_withdrawn or 0.0) == 0.0


# ═════════════════════════════════════════════
# transfers are NOT income
# ═════════════════════════════════════════════
def test_transfer_is_not_income(client, db_session):
    stage = _funded_stage(db_session)
    wallet = _account(db_session, "Trust Wallet", AccountType.CRYPTO_WALLET)
    exchange = _account(db_session, "Exchange", AccountType.EXCHANGE)

    # دریافت ۵۰۰ در Trust Wallet (دارایی است، نه درآمد)
    pid = _create(client, stage.id, wallet.id, 500.0).json()["id"]
    for target in ("approved", "processing", "received"):
        client.post(f"/api/prop/payouts/{pid}/status", json={"status": target})

    income_before = client.get("/api/finance/summary").json()["total_income"]
    assert income_before == 0.0

    # انتقال Trust Wallet → Exchange (درآمد نیست)
    r = client.post(f"/api/prop/payouts/{pid}/transfer", json={
        "to_account_id": exchange.id, "amount": 500.0, "currency": "USD",
    })
    assert r.status_code == 200

    summary = client.get("/api/finance/summary").json()
    assert summary["total_income"] == 0.0  # تغییر نکرد
    assert summary["total_transfers"] == 500.0

    db_session.refresh(wallet)
    db_session.refresh(exchange)
    assert wallet.balance == 0.0
    assert exchange.balance == 500.0

    tx = db_session.query(FinancialTransaction).filter(
        FinancialTransaction.type == TransactionType.TRANSFER  # فاز ۳۸.۴: جانشین EXCHANGE
    ).first()
    assert tx is not None


# ═════════════════════════════════════════════
# delete / update integrity
# ═════════════════════════════════════════════
def test_delete_reverses_income(client, db_session):
    stage = _funded_stage(db_session)
    dest = _account(db_session)
    pid = _create(client, stage.id, dest.id, 400.0).json()["id"]
    for target in ("approved", "processing", "received"):
        client.post(f"/api/prop/payouts/{pid}/status", json={"status": target})

    assert client.delete(f"/api/prop/payouts/{pid}").status_code == 200

    db_session.refresh(dest)
    assert dest.balance == 0.0
    db_session.refresh(stage)
    assert stage.total_withdrawn == 0.0
    tx = db_session.query(FinancialTransaction).first()
    assert tx.is_deleted is True


def test_update_amount_adjusts_transaction(client, db_session):
    stage = _funded_stage(db_session)
    dest = _account(db_session)
    pid = _create(client, stage.id, dest.id, 500.0).json()["id"]
    for target in ("approved", "processing", "received"):
        client.post(f"/api/prop/payouts/{pid}/status", json={"status": target})

    r = client.put(f"/api/prop/payouts/{pid}", json={"amount": 700.0})
    assert r.status_code == 200

    tx = db_session.query(FinancialTransaction).first()
    assert tx.amount == 700.0
    db_session.refresh(dest)
    assert dest.balance == 700.0
    db_session.refresh(stage)
    assert stage.total_withdrawn == 700.0


def test_serializer_exposes_status_and_transitions(client, db_session):
    stage = _funded_stage(db_session)
    dest = _account(db_session)
    _create(client, stage.id, dest.id, 100.0)

    rows = client.get("/api/prop/payouts").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == WithdrawalStatus.REQUESTED.value
    assert row["currency"] == "USDT"
    assert set(row["allowed_transitions"]) == {"approved", "cancelled"}


