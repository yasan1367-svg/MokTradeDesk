from sqlalchemy import and_, or_

from ..models.finance import AccountType, FinancialAccount, FinancialTransaction, TransactionType


def bank_income_filter():
    """تراکنش‌هایی که نشان‌دهندهٔ ورود پول به سیستم مالی شخص هستند.

    - DEPOSIT و PROFIT (صرف‌نظر از نوع حساب مقصد)
    - TRANSFER از حساب غیربانکی به بانک (money entering the banking system)
    """
    return and_(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.amount > 0,
        or_(
            FinancialTransaction.type.in_([TransactionType.DEPOSIT, TransactionType.PROFIT]),
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
    """ورژن Pythonic bank_income_filter برای یک شیء تراکنش."""
    if transaction.is_deleted or float(transaction.amount or 0.0) <= 0:
        return False
    if transaction.type in (TransactionType.DEPOSIT, TransactionType.PROFIT):
        return True
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
