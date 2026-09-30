"""فاز ۴۵.۱۰ — تست Property (Hypothesis): هر دنباله از عملیات، دفتر کل را تراز نگه می‌دارد.

برای همهٔ حساب‌ها باید `reconcile.delta == 0` باشد؛ یعنی `balance` ذخیره‌شده همیشه
با مجموع اثر تراکنش‌ها توضیح‌پذیر است.
"""
import random

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.models.finance import (
    AccountType,
    Currency,
    FinancialAccount,
    FinancialTransaction,
    TransactionType,
)
from app.services.wallet_service import WalletError, WalletService

OPS = [
    "deposit",
    "withdrawal",
    "transfer",
    "adjustment",
    "reverse_deposit",
    "reverse_withdrawal",
]


@settings(
    max_examples=25,
    deadline=None,
    # fixture درون هر مثال ریست نمی‌شود، ولی انباشت عملیات دقیقاً همان چیزی است
    # که می‌خواهیم بسنجیم (دنبالهٔ طولانی عملیات).
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(operations=st.lists(st.sampled_from(OPS), min_size=10, max_size=60))
def test_random_operations_keep_balance_consistent(db_session, operations):
    """هر دنباله از عملیات، balance == ledger (reconcile.delta == 0)."""
    rng = random.Random(20260930)

    accounts = []
    for i in range(3):
        acc = FinancialAccount(
            name=f"W{i}", type=AccountType.BANK, currency=Currency.USD, balance=0.0,
        )
        db_session.add(acc)
        db_session.flush()
        accounts.append(acc)
    db_session.commit()

    def _open_txs(kinds):
        return (
            db_session.query(FinancialTransaction)
            .filter(
                FinancialTransaction.is_deleted == False,  # noqa: E712
                FinancialTransaction.type.in_(kinds),
            )
            .all()
        )

    for op in operations:
        try:
            if op == "deposit":
                a = rng.choice(accounts)
                WalletService.post(
                    db_session, account_id=a.id, type=TransactionType.DEPOSIT,
                    amount=float(rng.randint(10, 100)),
                )
            elif op == "withdrawal":
                a = rng.choice(accounts)
                WalletService.post(
                    db_session, account_id=a.id, type=TransactionType.WITHDRAWAL,
                    amount=float(rng.randint(10, 100)), allow_overdraft=True,
                )
            elif op == "transfer":
                a, b = rng.sample(accounts, 2)
                WalletService.post(
                    db_session, account_id=a.id, type=TransactionType.TRANSFER,
                    amount=float(rng.randint(10, 100)),
                    from_account_id=a.id, to_account_id=b.id, allow_overdraft=True,
                )
            elif op == "adjustment":
                a = rng.choice(accounts)
                signed = float(rng.choice([-100, -50, -25, 25, 50, 100]))
                WalletService.post(
                    db_session, account_id=a.id, type=TransactionType.ADJUSTMENT,
                    amount=abs(signed), signed_amount=signed,
                )
            elif op == "reverse_deposit":
                txs = _open_txs([
                    TransactionType.DEPOSIT, TransactionType.PROFIT, TransactionType.ADJUSTMENT,
                ])
                if txs:
                    WalletService.reverse(db_session, rng.choice(txs))
            elif op == "reverse_withdrawal":
                txs = _open_txs([TransactionType.WITHDRAWAL, TransactionType.LOSS])
                if txs:
                    WalletService.reverse(db_session, rng.choice(txs))
        except WalletError:
            db_session.rollback()
            continue

    for acc in accounts:
        r = WalletService.reconcile(db_session, acc.id)
        assert r["delta"] == 0, f"حساب {acc.id} ناتراز: {r}"
