from sqlalchemy import and_, or_
from ..models.finance import (
    AccountType,
    CashFlow,
    FinancialAccount,
    FinancialTransaction,
    TransactionType,
)


def bank_income_filter():
    """درآمدهایی را که واقعاً به حساب بانکی وارد شده‌اند فیلتر می‌کند."""
    return and_(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.amount > 0,
        or_(
            and_(
                FinancialTransaction.type == TransactionType.DEPOSIT,
                FinancialTransaction.account.has(FinancialAccount.type == AccountType.BANK),
            ),
            and_(
                FinancialTransaction.type == TransactionType.PROFIT,
                FinancialTransaction.account.has(FinancialAccount.type == AccountType.BANK),
            ),
            and_(
                FinancialTransaction.type == TransactionType.EXTERNAL_INCOME,
                FinancialTransaction.account.has(FinancialAccount.type == AccountType.BANK),
            ),
            and_(
                FinancialTransaction.type == TransactionType.TRANSFER,
                FinancialTransaction.account_id == FinancialTransaction.to_account_id,
                FinancialTransaction.from_account_id != FinancialTransaction.to_account_id,
                FinancialTransaction.account.has(FinancialAccount.type == AccountType.BANK),
                FinancialTransaction.from_account.has(FinancialAccount.type != AccountType.BANK),
            ),
        ),
    )


def is_bank_income(transaction: FinancialTransaction) -> bool:
    """بررسی Pythonic هم‌ارز bank_income_filter."""
    if transaction.is_deleted or float(transaction.amount or 0.0) <= 0:
        return False
    if transaction.type in (
        TransactionType.DEPOSIT,
        TransactionType.PROFIT,
        TransactionType.EXTERNAL_INCOME,
    ):
        return bool(transaction.account and transaction.account.type == AccountType.BANK)
    if (
        transaction.type == TransactionType.TRANSFER
        and transaction.account_id == transaction.to_account_id
        and transaction.from_account_id != transaction.to_account_id
        and transaction.account
        and transaction.account.type == AccountType.BANK
        and transaction.from_account
        and transaction.from_account.type != AccountType.BANK
    ):
        return True
    return False
