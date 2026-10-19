"""تست‌های فاز ۴۵ — یکپارچگی دفتر کل مالی (Financial Ledger Integrity).

هر تسک، بخش خودش را دارد. هدف کلی: `FinancialAccount.balance` فقط از مسیر
`WalletService` تغییر کند و `reconcile.delta == 0` بماند.
"""
from datetime import datetime

import pytest

from app.models.finance import (
    AccountType,
    Currency,
    FinancialAccount,
    TransactionType,
)
from app.services.wallet_service import WalletService


def _accounts(client):
    return client.get("/api/finance/accounts").json()


def _transactions(client, **params):
    return client.get("/api/finance/transactions", params=params).json()


# ═════════════════════════════════════════════
# ۴۵.۱ — ممنوعیت PATCH موجودی + موجودی اولیه از مسیر دفتر
# ═════════════════════════════════════════════
def test_patch_account_balance_rejected(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 0,
    }).json()["id"]

    r = client.patch(f"/api/finance/accounts/{acc_id}", json={"balance": 9999})
    assert r.status_code in (200, 422)  # یا نادیده گرفته می‌شود یا رد

    acc = db_session.get(FinancialAccount, acc_id)
    db_session.refresh(acc)
    assert acc.balance == 0  # دور زدن WalletService ممکن نیست


def test_create_account_with_initial_balance_creates_adjustment(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 1000,
    }).json()["id"]

    acc = db_session.get(FinancialAccount, acc_id)
    db_session.refresh(acc)
    assert acc.balance == 1000

    txs = _transactions(client, account_id=acc_id)
    assert len(txs) == 1
    assert txs[0]["type"] == "adjustment"
    assert txs[0]["amount"] == 1000


def test_create_account_reconcile_zero(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 250,
    }).json()["id"]

    r = WalletService.reconcile(db_session, acc_id)
    assert r["delta"] == 0
    assert r["is_balanced"] is True


# ═════════════════════════════════════════════
# ۴۵.۲ — تغییر ارز فقط برای حساب بدون تراکنش
# ═════════════════════════════════════════════
def test_change_currency_with_transactions_rejected(client, db_session):
    # ساخت با موجودی ⇒ یک ADJUSTMENT ایجاد می‌شود
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 100,
    }).json()["id"]

    r = client.patch(f"/api/finance/accounts/{acc_id}", json={"currency": "IRR"})
    assert r.status_code == 409
    acc = db_session.get(FinancialAccount, acc_id)
    db_session.refresh(acc)
    assert acc.currency == Currency.USD


def test_change_currency_without_transactions_ok(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 0,
    }).json()["id"]

    r = client.patch(f"/api/finance/accounts/{acc_id}", json={"currency": "IRR"})
    assert r.status_code == 200
    acc = db_session.get(FinancialAccount, acc_id)
    db_session.refresh(acc)
    assert acc.currency == Currency.IRR


# ═════════════════════════════════════════════
# ۴۵.۳ — حذف نرم حساب (آرشیو) + بدون cascade
# ═════════════════════════════════════════════
def test_delete_account_with_transactions_409(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 100,
    }).json()["id"]

    r = client.delete(f"/api/finance/accounts/{acc_id}")
    assert r.status_code == 409
    assert db_session.get(FinancialAccount, acc_id) is not None


def test_delete_account_with_balance_409(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 0,
    }).json()["id"]
    # موجودی غیرصفر بدون هیچ تراکنش (سناریوی drift قدیمی)
    acc = db_session.get(FinancialAccount, acc_id)
    acc.balance = 50.0
    db_session.commit()

    r = client.delete(f"/api/finance/accounts/{acc_id}")
    assert r.status_code == 409


def test_delete_empty_account_archives(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 0,
    }).json()["id"]

    r = client.delete(f"/api/finance/accounts/{acc_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    acc = db_session.get(FinancialAccount, acc_id)
    db_session.refresh(acc)
    assert acc.is_archived is True
    # از لیست پنهان است
    assert acc_id not in [a["id"] for a in _accounts(client)]


# ═════════════════════════════════════════════
# ۴۵.۴ — PATCH تراکنش: فقط غیرحذف‌شده + هم‌گامی TRANSFER
# ═════════════════════════════════════════════
def _new_account(client, name, balance=0):
    return client.post("/api/finance/accounts", json={
        "name": name, "type": "bank", "currency": "USD", "balance": balance,
    }).json()["id"]


def test_patch_deleted_transaction_404(client, db_session):
    acc_id = _new_account(client, "A", balance=100)
    tx_id = client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 50, "type": "deposit",
    }).json()["id"]
    assert client.delete(f"/api/finance/transactions/{tx_id}").status_code == 200

    r = client.patch(f"/api/finance/transactions/{tx_id}", json={"amount": 60})
    assert r.status_code == 404


def test_patch_transfer_syncs_account_id(client, db_session):
    a = _new_account(client, "A", balance=100)
    b = _new_account(client, "B", balance=0)
    c = _new_account(client, "C", balance=0)

    tx_id = client.post("/api/finance/transactions", json={
        "account_id": a, "amount": 30, "type": "transfer",
        "from_account_id": a, "to_account_id": b,
    }).json()["id"]

    r = client.patch(f"/api/finance/transactions/{tx_id}", json={"to_account_id": c})
    assert r.status_code == 200, r.text

    row = next(t for t in _transactions(client) if t["id"] == tx_id)
    assert row["to_account_id"] == c
    assert row["account_id"] == c      # هم‌گام با مقصد
    assert row["from_account_id"] == a

    # تراز می‌ماند: A=70، B=0، C=30
    db_session.expire_all()
    assert db_session.get(FinancialAccount, a).balance == 70
    assert db_session.get(FinancialAccount, b).balance == 0
    assert db_session.get(FinancialAccount, c).balance == 30


# ═════════════════════════════════════════════
# ۴۵.۵ — اعتبارسنجی ارز + تبدیل ارز
# ═════════════════════════════════════════════
def test_wallet_post_currency_mismatch_rejected(client, db_session):
    usd = _new_account(client, "USD-A", balance=500)
    r = client.post("/api/finance/transactions", json={
        "account_id": usd, "amount": 1000, "currency": "IRR", "type": "deposit",
    })
    assert r.status_code == 400
    assert "ارز" in r.json()["detail"]


def test_transfer_cross_currency_rejected(client, db_session):
    usd = _new_account(client, "USD-B", balance=500)
    irr = client.post("/api/finance/accounts", json={
        "name": "IRR-B", "type": "bank", "currency": "IRR", "balance": 0,
    }).json()["id"]
    r = client.post("/api/finance/transactions", json={
        "account_id": usd, "amount": 100, "type": "transfer",
        "from_account_id": usd, "to_account_id": irr,
    })
    assert r.status_code == 400
    assert "ارز" in r.json()["detail"]


@pytest.mark.xfail(reason="endpoint `/wallets/convert` هنوز پیاده نشده (فاز ۴۵ برنامه‌ریزی شد)")
def test_convert_endpoint_creates_two_transactions(client, db_session):
    """تبدیل ارز با دو تراکنش ADJUSTMENT — endpoint در فاز ۴۵ برنامه‌ریزی شد ولی هنوز ساخته نشده."""
    usd = _new_account(client, "USD-C", balance=100)
    irr = client.post("/api/finance/accounts", json={
        "name": "IRR-C", "type": "bank", "currency": "IRR", "balance": 0,
    }).json()["id"]

    r = client.post("/api/finance/wallets/convert", json={
        "from_account_id": usd, "to_account_id": irr, "amount": 100, "rate": 90000,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["to_amount"] == 9_000_000

    db_session.expire_all()
    assert db_session.get(FinancialAccount, usd).balance == 0
    assert db_session.get(FinancialAccount, irr).balance == 9_000_000

    txs = _transactions(client)
    converts = [t for t in txs if t["description"] and t["description"].startswith("تبدیل ارز")]
    assert len(converts) == 2

    # هر دو حساب تراز
    assert WalletService.reconcile(db_session, usd)["delta"] == 0
    assert WalletService.reconcile(db_session, irr)["delta"] == 0


# ═════════════════════════════════════════════
# ۴۵.۶ — ابزار مشترک ارز (utils/currency.py)
# ═════════════════════════════════════════════
def test_to_currency_valid():
    from app.utils.currency import to_currency

    assert to_currency("usdt") == Currency.USDT
    assert to_currency("IRR") == Currency.IRR
    assert to_currency(Currency.USDT) == Currency.USDT
    assert to_currency(None) is None
    assert to_currency(None, default=Currency.USDT) == Currency.USDT


def test_to_currency_invalid_raises():
    import pytest

    from app.utils.currency import to_currency

    with pytest.raises(ValueError):
        to_currency("XYZ")
    # با default، fallback امن
    assert to_currency("XYZ", default=Currency.USDT) == Currency.USDT


# ═════════════════════════════════════════════
# ۴۵.۷ — رد برگشتِ منفی‌ساز
# ═════════════════════════════════════════════
def test_reverse_deposit_with_insufficient_balance_rejected(client, db_session):
    acc = _new_account(client, "A", balance=0)
    dep = client.post("/api/finance/transactions", json={
        "account_id": acc, "amount": 100, "type": "deposit",
    }).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": acc, "amount": 80, "type": "withdrawal",
    })
    # موجودی فعلی = 20 ⇒ حذف واریز 100 آن را منفی می‌کند
    r = client.delete(f"/api/finance/transactions/{dep}")
    assert r.status_code == 400
    assert "منفی" in r.json()["detail"]

    db_session.expire_all()
    assert db_session.get(FinancialAccount, acc).balance == 20


# ═════════════════════════════════════════════
# ۴۵.۸ — running_balance با offset / date_from
# ═════════════════════════════════════════════
def _mk_account(db, name="A"):
    acc = FinancialAccount(name=name, type=AccountType.BANK, currency=Currency.USD, balance=0.0)
    db.add(acc)
    db.commit()
    return acc


def test_ledger_running_balance_with_offset(db_session):
    acc = _mk_account(db_session)
    WalletService.post(db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=10.0)
    WalletService.post(db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=20.0)
    WalletService.post(db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=30.0)

    entries = WalletService.ledger(db_session, acc.id, limit=1, offset=1)
    assert len(entries) == 1
    # تراکنش دوم (۲۰) ⇒ موجودی تجمعی = ۱۰ + ۲۰ = ۳۰
    assert entries[0]["running_balance"] == 30.0


def test_ledger_running_balance_with_date_from(db_session):
    acc = _mk_account(db_session)
    WalletService.post(
        db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=10.0,
        date=datetime(2025, 1, 1),
    )
    WalletService.post(
        db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=20.0,
        date=datetime(2025, 1, 2),
    )

    entries = WalletService.ledger(db_session, acc.id, date_from=datetime(2025, 1, 2))
    assert len(entries) == 1
    # opening = ۱۰ (قبل از بازه) ⇒ running = ۳۰
    assert entries[0]["running_balance"] == 30.0


# ═════════════════════════════════════════════
# ۴۵.۹ — endpoint مغایرت‌یابی
# ═════════════════════════════════════════════
def test_reconcile_endpoint_returns_zero_for_balanced(client, db_session):
    acc_id = _new_account(client, "A", balance=100)
    body = client.get(f"/api/finance/accounts/{acc_id}/reconcile").json()
    assert body["delta"] == 0
    assert body["is_balanced"] is True


def test_reconcile_endpoint_returns_delta_for_unbalanced(client, db_session):
    acc_id = _new_account(client, "A", balance=0)
    acc = db_session.get(FinancialAccount, acc_id)
    acc.balance = 50.0  # موجودی بدون تراکنش (drift)
    db_session.commit()

    body = client.get(f"/api/finance/accounts/{acc_id}/reconcile").json()
    assert body["delta"] == 50.0
    assert body["is_balanced"] is False


def test_reconcile_endpoint_404_for_missing(client, db_session):
    assert client.get("/api/finance/accounts/999999/reconcile").status_code == 404







