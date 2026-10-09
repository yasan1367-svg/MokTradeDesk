"""تست‌های فاز ۳۹.۱ — `WalletService` (تنها نویسندهٔ `FinancialAccount.balance`).

پوشش:
- جهت‌داری اثر هر نوع تراکنش (DEPOSIT/WITHDRAWAL/TRANSFER/ADJUSTMENT)
- محافظ موجودی (`allow_overdraft=False`) با پیام فارسی
- `reverse()` idempotent + برگشت دقیق اثر
- `reconcile()` : موجودی ذخیره‌شده در برابر مجموع دفتر
- `ledger()`    : جهت، مبلغ علامت‌دار، موجودی تجمعی و حساب مقابل
- مهاجرت فراخوانی‌های API (`POST/PATCH/DELETE /finance/transactions`)
"""
import pytest

from app.models.finance import (
    AccountType,
    Currency,
    FinancialAccount,
    TransactionType,
)
from app.services.wallet_service import WalletError, WalletService


# ═════════════════════════════════════════════
# helpers
# ═════════════════════════════════════════════
def _account(
    db,
    name="Wallet",
    acc_type=AccountType.CRYPTO_WALLET,
    balance=0.0,
    currency=Currency.USD,
):
    account = FinancialAccount(name=name, type=acc_type, currency=currency, balance=balance)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _balance(db, account_id) -> float:
    db.expire_all()
    return db.query(FinancialAccount).filter(FinancialAccount.id == account_id).first().balance


# ═════════════════════════════════════════════
# ۱) جهت‌داری اثر
# ═════════════════════════════════════════════
def test_post_deposit_increases_balance(db_session):
    acc = _account(db_session)

    tx = WalletService.post(
        db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=150.0
    )

    assert tx.id is not None                      # post همیشه flush می‌زند
    assert tx.type == TransactionType.DEPOSIT
    assert _balance(db_session, acc.id) == 150.0


def test_post_withdrawal_decreases_balance(db_session):
    acc = _account(db_session, balance=100.0)

    WalletService.post(db_session, account_id=acc.id, type=TransactionType.WITHDRAWAL, amount=40.0)

    assert _balance(db_session, acc.id) == 60.0


def test_post_single_sided_transfer_has_no_balance_effect(db_session):
    """انتقال یک‌طرفه = تبدیل بیرون از نرم‌افزار ⇒ ثبت می‌شود ولی موجودی را تغییر نمی‌دهد.

    این قرارداد قدیمی `/finance/transactions` است و تست‌های `test_exchange_rates` و
    `test_money_cycle` به آن وابسته‌اند.
    """
    acc = _account(db_session, "Ex", AccountType.EXCHANGE, balance=0.0, currency=Currency.IRR)

    tx = WalletService.post(
        db_session,
        account_id=acc.id,
        type=TransactionType.TRANSFER,
        amount=100_000_000,
        currency=Currency.IRR,
    )

    assert tx.id is not None
    assert tx.from_account_id is None
    assert tx.to_account_id is None
    assert _balance(db_session, acc.id) == 0.0


def test_post_transfer_moves_both(db_session):
    src = _account(db_session, "Source", AccountType.BANK, balance=500.0)
    dst = _account(db_session, "Dest", AccountType.EXCHANGE, balance=0.0)

    tx = WalletService.post(
        db_session,
        account_id=src.id,                        # عمداً مبدأ ⇒ باید به مقصد اصلاح شود
        type=TransactionType.TRANSFER,
        amount=200.0,
        from_account_id=src.id,
        to_account_id=dst.id,
    )

    assert tx.account_id == dst.id                # قرارداد فاز ۳۳: account_id = مقصد
    assert _balance(db_session, src.id) == 300.0
    assert _balance(db_session, dst.id) == 200.0


def test_transfer_same_account_rejected(db_session):
    acc = _account(db_session, balance=500.0)

    with pytest.raises(WalletError):
        WalletService.post(
            db_session,
            account_id=acc.id,
            type=TransactionType.TRANSFER,
            amount=100.0,
            from_account_id=acc.id,
            to_account_id=acc.id,
        )

    assert _balance(db_session, acc.id) == 500.0


def test_adjustment_signed(db_session):
    acc = _account(db_session, balance=100.0)

    # افزایش با amount مثبت
    WalletService.post(db_session, account_id=acc.id, type=TransactionType.ADJUSTMENT, amount=50.0)
    assert _balance(db_session, acc.id) == 150.0

    # کاهش با signed_amount منفی (بدون محافظ موجودی — اصلاح دستی)
    WalletService.post(
        db_session, account_id=acc.id, type=TransactionType.ADJUSTMENT, signed_amount=-30.0
    )
    assert _balance(db_session, acc.id) == 120.0

    # صفر ممنوع
    with pytest.raises(WalletError):
        WalletService.post(
            db_session, account_id=acc.id, type=TransactionType.ADJUSTMENT, signed_amount=0.0
        )


# ═════════════════════════════════════════════
# ۲) اعتبارسنجی و محافظ موجودی
# ═════════════════════════════════════════════
def test_post_rejects_non_positive_amount(db_session):
    acc = _account(db_session)

    for bad in (0.0, -10.0):
        with pytest.raises(WalletError):
            WalletService.post(
                db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=bad
            )

    assert _balance(db_session, acc.id) == 0.0


def test_overdraft_blocked(db_session):
    src = _account(db_session, "منبع", AccountType.BANK, balance=100.0)
    dst = _account(db_session, "مقصد", AccountType.EXCHANGE, balance=0.0)

    with pytest.raises(WalletError) as excinfo:
        WalletService.post(
            db_session,
            account_id=dst.id,
            type=TransactionType.TRANSFER,
            amount=500.0,
            from_account_id=src.id,
            to_account_id=dst.id,
        )
    assert "کافی نیست" in str(excinfo.value)

    # برداشت بیش از موجودی هم مسدود است
    with pytest.raises(WalletError):
        WalletService.post(
            db_session, account_id=src.id, type=TransactionType.WITHDRAWAL, amount=500.0
        )

    assert _balance(db_session, src.id) == 100.0
    assert _balance(db_session, dst.id) == 0.0


def test_overdraft_allowed_when_flag_set(db_session):
    acc = _account(db_session, balance=0.0)

    WalletService.post(
        db_session,
        account_id=acc.id,
        type=TransactionType.WITHDRAWAL,
        amount=100.0,
        allow_overdraft=True,
    )

    assert _balance(db_session, acc.id) == -100.0


# ═════════════════════════════════════════════
# ۳) برگشت (reverse)
# ═════════════════════════════════════════════
def test_reverse_restores_balance(db_session):
    src = _account(db_session, "S", AccountType.BANK, balance=500.0)
    dst = _account(db_session, "D", AccountType.CRYPTO_WALLET, balance=0.0)

    WalletService.post(db_session, account_id=dst.id, type=TransactionType.DEPOSIT, amount=150.0)
    tx = WalletService.post(
        db_session,
        account_id=dst.id,
        type=TransactionType.TRANSFER,
        amount=200.0,
        from_account_id=src.id,
        to_account_id=dst.id,
    )
    assert _balance(db_session, src.id) == 300.0
    assert _balance(db_session, dst.id) == 350.0

    assert WalletService.reverse(db_session, tx) is True

    assert tx.is_deleted is True
    assert _balance(db_session, src.id) == 500.0
    assert _balance(db_session, dst.id) == 150.0

    # idempotent: برگشت دوباره بی‌اثر است
    assert WalletService.reverse(db_session, tx) is False
    assert _balance(db_session, src.id) == 500.0
    assert _balance(db_session, dst.id) == 150.0


def test_post_rollback_discards_balance_change(db_session):
    acc = _account(db_session)

    tx = WalletService.post(
        db_session, account_id=acc.id, type=TransactionType.PROFIT, amount=10.0, commit=False
    )
    assert tx.id is not None
    assert _balance(db_session, acc.id) == 10.0

    db_session.rollback()
    assert _balance(db_session, acc.id) == 0.0



# ═════════════════════════════════════════════
# ۴) reconcile — موجودی ذخیره‌شده vs مجموع دفتر
# ═════════════════════════════════════════════
def test_reconcile_balanced(db_session):
    acc = _account(db_session)

    WalletService.post(db_session, account_id=acc.id, type=TransactionType.DEPOSIT, amount=150.0)
    WalletService.post(db_session, account_id=acc.id, type=TransactionType.WITHDRAWAL, amount=50.0)
    WalletService.post(
        db_session, account_id=acc.id, type=TransactionType.ADJUSTMENT, signed_amount=25.0
    )

    row = WalletService.reconcile(db_session, acc.id)

    assert row["account_id"] == acc.id
    assert row["stored"] == 125.0
    assert row["ledger"] == 125.0
    assert row["delta"] == 0.0
    assert row["is_balanced"] is True
    assert row["entry_count"] == 3


def test_reconcile_flags_unexplained_opening_balance(db_session):
    """کیف‌پولی که با `balance` مستقیم ساخته شده، تراکنش افتتاحیه ندارد (شکاف G1)."""
    acc = _account(db_session, name="Legacy", balance=1000.0)

    row = WalletService.reconcile(db_session, acc.id)

    assert row["stored"] == 1000.0
    assert row["ledger"] == 0.0
    assert row["delta"] == 1000.0
    assert row["is_balanced"] is False
    assert row["entry_count"] == 0


def test_reconcile_opening_balance_via_adjustment(db_session):
    """راه درست ثبت موجودی اولیه: کیف‌پول خالی + ADJUSTMENT ⇒ تراز از ابتدا."""
    acc = _account(db_session, name="New", balance=0.0)

    WalletService.post(
        db_session, account_id=acc.id, type=TransactionType.ADJUSTMENT, signed_amount=1000.0
    )

    row = WalletService.reconcile(db_session, acc.id)

    assert row["stored"] == 1000.0
    assert row["ledger"] == 1000.0
    assert row["delta"] == 0.0
    assert row["is_balanced"] is True
    assert row["entry_count"] == 1


def test_reconcile_unknown_account(db_session):
    with pytest.raises(WalletError):
        WalletService.reconcile(db_session, 999_999)


# ═════════════════════════════════════════════
# ۵) ledger — صورت‌حساب کیف‌پول
# ═════════════════════════════════════════════
def test_ledger_running_balance_and_peers(db_session):
    src = _account(db_session, "Source", AccountType.BANK)
    dst = _account(db_session, "Dest", AccountType.EXCHANGE)

    WalletService.post(db_session, account_id=src.id, type=TransactionType.DEPOSIT, amount=500.0)
    WalletService.post(
        db_session,
        account_id=dst.id,
        type=TransactionType.TRANSFER,
        amount=200.0,
        from_account_id=src.id,
        to_account_id=dst.id,
    )

    entries = WalletService.ledger(db_session, src.id)

    assert len(entries) == 2
    assert entries[0]["direction"] == "in"
    assert entries[0]["signed_amount"] == 500.0
    assert entries[0]["running_balance"] == 500.0

    assert entries[1]["direction"] == "out"
    assert entries[1]["signed_amount"] == -200.0
    assert entries[1]["running_balance"] == 300.0
    assert entries[1]["peer_account_id"] == dst.id
    assert entries[1]["peer_account_name"] == "Dest"

    # آستانهٔ پایانی = موجودی فعلی
    assert entries[-1]["running_balance"] == _balance(db_session, src.id) == 300.0



# ═════════════════════════════════════════════
# ۶) مهاجرت فراخوانی‌های API (integration)
# ═════════════════════════════════════════════
def _api_account(client, name="B", acc_type="bank", balance=0.0) -> int:
    return client.post(
        "/api/finance/accounts",
        json={"name": name, "type": acc_type, "balance": balance},
    ).json()["id"]


def test_api_create_transaction_updates_balance(client, db_session):
    acc_id = _api_account(client)

    r = client.post(
        "/api/finance/transactions",
        json={"account_id": acc_id, "amount": 500, "type": "deposit"},
    )

    assert r.status_code == 200
    assert _balance(db_session, acc_id) == 500.0


def test_api_delete_transaction_reverses_balance(client, db_session):
    acc_id = _api_account(client)
    tx_id = client.post(
        "/api/finance/transactions",
        json={"account_id": acc_id, "amount": 500, "type": "deposit"},
    ).json()["id"]
    assert _balance(db_session, acc_id) == 500.0

    assert client.delete(f"/api/finance/transactions/{tx_id}").status_code == 200

    assert _balance(db_session, acc_id) == 0.0


def test_api_update_transaction_reapplies_balance(client, db_session):
    acc_id = _api_account(client)
    tx_id = client.post(
        "/api/finance/transactions",
        json={"account_id": acc_id, "amount": 500, "type": "deposit"},
    ).json()["id"]

    r = client.patch(f"/api/finance/transactions/{tx_id}", json={"amount": 800})

    assert r.status_code == 200
    assert _balance(db_session, acc_id) == 800.0


def test_api_update_transaction_rejects_zero_amount(client, db_session):
    """ویرایش به صفر نباید اثر قبلی را بی‌صدا حذف کند."""
    acc_id = _api_account(client)
    tx_id = client.post(
        "/api/finance/transactions",
        json={"account_id": acc_id, "amount": 500, "type": "deposit"},
    ).json()["id"]

    r = client.patch(f"/api/finance/transactions/{tx_id}", json={"amount": 0})

    assert r.status_code == 400
    assert _balance(db_session, acc_id) == 500.0


def test_api_create_transaction_invalid_account_rejected(client):
    r = client.post(
        "/api/finance/transactions",
        json={"account_id": 999_999, "amount": 10, "type": "deposit"},
    )
    assert r.status_code == 400


def test_api_generic_transaction_allows_overdraft(client, db_session):
    """`POST /finance/transactions` یک دفتر کل دستی است ⇒ محافظ موجودی ندارد
    (سازگاری با قرارداد فاز ۱۲/۲۲ — و تضمین عدم شکستن `test_money_flow`)."""
    acc_id = _api_account(client)

    r = client.post(
        "/api/finance/transactions",
        json={"account_id": acc_id, "amount": 100, "type": "withdrawal"},
    )

    assert r.status_code == 200
    assert _balance(db_session, acc_id) == -100.0



# ═════════════════════════════════════════════
# ۷) رگرسیون: چرخهٔ برداشت پراپ (فاز ۳۳)
# ═════════════════════════════════════════════
def _funded_stage(db, profit=1500.0, profit_share=80.0):
    """مرحلهٔ FUNDED_REAL با سود ۱۵۰۰ ⇒ قابل برداشت = 1500 × 0.8 = 1200"""
    from datetime import datetime, timezone

    from app.models.prop import (
        PropAccount,
        PropFirm,
        PropStage,
        StageStatus,
        StageType,
    )
    from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource

    firm = PropFirm(name="FTMO")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="A1")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id,
        stage_type=StageType.FUNDED_REAL,
        status=StageStatus.ACTIVE,
        initial_balance=10000.0,
        profit_target=1000.0,
        max_daily_dd=500.0,
        max_total_dd=1000.0,
        min_trading_days=3,
        profit_share_percentage=profit_share,
        total_withdrawn=0.0,
    )
    db.add(stage)
    db.flush()

    strategy = Strategy(name="S")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db.add(version)
    db.flush()
    db.add(Trade(
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2000.0,
        size=1.0,
        pnl=profit,
        source=TradeSource.MANUAL,
        test_type=TestType.REAL_PROP,
        prop_stage_id=stage.id,
        version_id=version.id,
    ))
    db.commit()
    db.refresh(stage)
    return stage


def test_payout_still_works(client, db_session):
    """رگرسیون فاز ۳۳: چرخهٔ برداشت پراپ بعد از مهاجرت به WalletService دست‌نخورده کار می‌کند.

    - `REQUESTED` ⇒ بدون پول و بدون درآمد
    - `RECEIVED` در کیف‌پول ⇒ افزایش دارایی بدون ثبت درآمد بانکی
    """
    stage = _funded_stage(db_session)
    dest = _account(db_session, "Trust Wallet", AccountType.TRUST_WALLET)

    r = client.post("/api/prop/payouts", json={
        "prop_stage_id": stage.id,
        "amount": 500.0,
        "destination_account_id": dest.id,
    })
    assert r.status_code == 200, r.text
    payout = r.json()
    assert payout["status"] == "requested"
    assert payout["transaction_id"] is None
    assert _balance(db_session, dest.id) == 0.0

    for target in ("approved", "processing", "received"):
        step = client.post(f"/api/prop/payouts/{payout['id']}/status", json={"status": target})
        assert step.status_code == 200, step.text

    # دریافت در کیف‌پول هم درآمد محسوب می‌شود (فاز ۳۳: income در RECEIVED ثبت می‌شود).
    assert _balance(db_session, dest.id) == 500.0
    assert client.get("/api/finance/summary").json()["total_income"] == 0.0

    db_session.refresh(stage)
    assert stage.total_withdrawn == 500.0


def test_money_cycle_reflects_ledger(client, db_session):
    """`current_balance` = مجموع واقعی موجودی کیف‌پول‌ها (فاز ۳۹ / رفع G1)."""
    bank_id = client.post(
        "/api/finance/accounts", json={"name": "Bank", "type": "bank", "balance": 3000}
    ).json()["id"]

    client.post("/api/finance/transactions", json={
        "account_id": bank_id, "amount": 5000, "type": "deposit",
    })
    client.post("/api/finance/transactions", json={
        "account_id": bank_id, "amount": 2000, "type": "withdrawal",
    })
    # انتقال یک‌طرفه (تبدیل بیرون از نرم‌افزار) ⇒ بدون اثر روی موجودی
    client.post("/api/finance/transactions", json={
        "account_id": bank_id, "amount": 1000, "type": "transfer",
    })

    body = client.get("/api/finance/money-cycle").json()
    assert body["current_balance"] == 6000.0        # 3000 + 5000 − 2000
    assert body["total_exchanges"] == 1000



# ═════════════════════════════════════════════
# ۸) زیرفاز ۳۹.۲ — رفع G6 (`/finance/spendable-assets`)
# ═════════════════════════════════════════════
def test_spendable_assets_trust_wallet(client):
    """G6: سبد `trust_wallet` از `TRUST_WALLET` پر می‌شود، نه `CRYPTO_WALLET`."""
    client.post("/api/finance/accounts", json={
        "name": "TW", "type": "trust_wallet", "currency": "USD", "balance": 700,
    })
    client.post("/api/finance/accounts", json={
        "name": "CW", "type": "crypto_wallet", "currency": "USD", "balance": 300,
    })

    body = client.get("/api/finance/spendable-assets").json()

    assert body["trust_wallet"]["amount"] == 700
    assert body["crypto_wallet"]["amount"] == 300
    assert body["trust_wallet"]["currency"] == "USDT"
    assert body["crypto_wallet"]["currency"] == "USDT"
    # پیش از فاز ۳۹ سبد trust_wallet اشتباهاً ۳۰۰ بود (باگ G6)


def test_spendable_assets_irr_total(client):
    """G6: `total.irr` = Σ موجودی همهٔ کیف‌پول‌های IRR (نه فقط سبد `bank`)."""
    for name, acc_type, amount in (
        ("Bank", "bank", 1_000_000),
        ("Exch", "exchange", 500_000),
        ("Cash", "cash", 200_000),
        ("Card", "card", 300_000),
    ):
        client.post("/api/finance/accounts", json={
            "name": name, "type": acc_type, "currency": "IRR", "balance": amount,
        })
    # کیف‌پول دلاری نباید در جمع IRR بیاید
    client.post("/api/finance/accounts", json={
        "name": "USD-Wallet", "type": "crypto_wallet", "currency": "USD", "balance": 50,
    })

    body = client.get("/api/finance/spendable-assets").json()

    assert body["bank"]["amount"] == 1_000_000
    assert body["cash"]["amount"] == 200_000
    assert body["card"]["amount"] == 300_000
    # پیش از فاز ۳۹ این مقدار فقط ۱٬۰۰۰٬۰۰۰ (سبد بانک) بود (باگ G6)
    assert body["total"]["irr"] == 2_000_000
    assert body["total"]["irr"] != body["bank"]["amount"]


def test_spendable_assets_preserves_legacy_keys(client):
    """کلیدهای قدیمی برای سازگاری فرانت‌اند باید بمانند."""
    body = client.get("/api/finance/spendable-assets").json()

    for key in ("prop_stage_3", "broker", "exchange", "trust_wallet", "bank", "total"):
        assert key in body, key
    assert set(body["total"]) == {"usdt", "irr"}
    for key in ("prop_stage_3", "broker", "exchange", "trust_wallet", "bank",
                "crypto_wallet", "card", "cash"):
        assert set(body[key]) == {"amount", "currency"}



# ═════════════════════════════════════════════
# ۹) زیرفاز ۳۹.۲ — مهاجرت `/finance/withdrawals` (برداشت بروکر)
# ═════════════════════════════════════════════
def test_withdrawal_api_create_updates_balance(client, db_session):
    acc_id = _api_account(client, name="Bank", balance=1000.0)

    r = client.post("/api/finance/withdrawals", json={
        "account_id": acc_id, "amount": 250, "description": "برداشت بروکر",
    })

    assert r.status_code == 200, r.text
    assert r.json()["id"] is not None
    assert _balance(db_session, acc_id) == 750.0


def test_withdrawal_api_update_reapplies_balance(client, db_session):
    acc_id = _api_account(client, name="Bank", balance=1000.0)
    wid = client.post("/api/finance/withdrawals", json={
        "account_id": acc_id, "amount": 250,
    }).json()["id"]
    assert _balance(db_session, acc_id) == 750.0

    r = client.patch(f"/api/finance/withdrawals/{wid}", json={"amount": 400})

    assert r.status_code == 200, r.text
    assert _balance(db_session, acc_id) == 600.0


def test_withdrawal_api_update_rejects_zero_amount(client, db_session):
    acc_id = _api_account(client, name="Bank", balance=1000.0)
    wid = client.post("/api/finance/withdrawals", json={
        "account_id": acc_id, "amount": 250,
    }).json()["id"]

    r = client.patch(f"/api/finance/withdrawals/{wid}", json={"amount": 0})

    assert r.status_code == 400
    assert _balance(db_session, acc_id) == 750.0


def test_withdrawal_api_update_rejects_currency_mismatch_atomically(client, db_session):
    from app.models.finance import FinancialTransaction

    acc_id = _api_account(client, name="USDT Bank", balance=1000.0)
    irr_id = client.post("/api/finance/accounts", json={
        "name": "IRR Bank", "type": "bank", "currency": "IRR", "balance": 0.0,
    }).json()["id"]
    wid = client.post("/api/finance/withdrawals", json={
        "account_id": acc_id, "amount": 250,
    }).json()["id"]

    response = client.patch(f"/api/finance/withdrawals/{wid}", json={
        "account_id": irr_id,
    })

    assert response.status_code == 400
    assert _balance(db_session, acc_id) == 750.0
    assert _balance(db_session, irr_id) == 0.0
    withdrawal = db_session.get(FinancialTransaction, wid)
    assert withdrawal.account_id == acc_id
    assert withdrawal.currency.value == "USDT"


def test_withdrawal_api_update_allows_matching_account_currency(client, db_session):
    irr_id = client.post("/api/finance/accounts", json={
        "name": "IRR Bank", "type": "bank", "currency": "IRR", "balance": 0.0,
    }).json()["id"]
    usdt_id = _api_account(client, name="USDT Bank", balance=1000.0)
    wid = client.post("/api/finance/withdrawals", json={
        "account_id": usdt_id, "amount": 250,
    }).json()["id"]

    response = client.patch(f"/api/finance/withdrawals/{wid}", json={
        "account_id": irr_id, "currency": "IRR", "amount": 300,
    })

    assert response.status_code == 200, response.text
    assert _balance(db_session, usdt_id) == 1000.0
    assert _balance(db_session, irr_id) == -300.0


def test_withdrawal_api_delete_reverses_balance(client, db_session):
    acc_id = _api_account(client, name="Bank", balance=1000.0)
    wid = client.post("/api/finance/withdrawals", json={
        "account_id": acc_id, "amount": 250,
    }).json()["id"]

    assert client.delete(f"/api/finance/withdrawals/{wid}").status_code == 200

    assert _balance(db_session, acc_id) == 1000.0


def test_withdrawal_api_allows_overdraft(client, db_session):
    """مسیر دستی (مثل `/finance/transactions`) ⇒ محافظ موجودی ندارد."""
    acc_id = _api_account(client, name="Empty")

    r = client.post("/api/finance/withdrawals", json={"account_id": acc_id, "amount": 100})

    assert r.status_code == 200
    assert _balance(db_session, acc_id) == -100.0


# ═════════════════════════════════════════════
# ۱۰) زیرفاز ۳۹.۲ — محافظ موجودی مسیرهای واقعی (G9)
# ═════════════════════════════════════════════
def _prop_account(client, label="A1") -> int:
    firm = client.post("/api/prop/firms", json={"name": f"Firm-{label}"}).json()
    acc = client.post("/api/prop/accounts", json={
        "prop_firm_id": firm["id"], "account_label": label,
    }).json()
    return acc["id"]


def test_prop_cost_decreases_payer_balance(client, db_session):
    prop_account_id = _prop_account(client, "buy-ok")
    payer_id = _api_account(client, name="Payer", balance=5000.0)

    r = client.post("/api/prop/costs", json={
        "prop_account_id": prop_account_id,
        "cost_type": "purchase",
        "amount": 540.0,
        "currency": "USD",
        "pay_from_account_id": payer_id,
        "create_transaction": True,
    })

    assert r.status_code == 200, r.text
    assert r.json()["transaction_id"] is not None
    assert _balance(db_session, payer_id) == 4460.0


def test_prop_cost_overdraft_blocked(client, db_session):
    """G9: خرید پراپ بیش از موجودی ⇒ 400 و بدون هیچ اثر مالی."""
    prop_account_id = _prop_account(client, "buy-fail")
    payer_id = _api_account(client, name="Poor", balance=100.0)

    r = client.post("/api/prop/costs", json={
        "prop_account_id": prop_account_id,
        "cost_type": "purchase",
        "amount": 540.0,
        "currency": "USD",
        "pay_from_account_id": payer_id,
        "create_transaction": True,
    })

    assert r.status_code == 400
    assert "کافی نیست" in r.json()["detail"]
    assert _balance(db_session, payer_id) == 100.0

