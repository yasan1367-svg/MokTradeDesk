from sqlalchemy import and_, or_
from ..models.finance import CashFlow, FinancialTransaction


def bank_income_filter():
    """گزارش درآمد بانک را با همان قرارداد CashFlow ذخیره‌شده فیلتر می‌کند."""
    return and_(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.amount > 0,
        FinancialTransaction.cash_flow == CashFlow.INCOME,
    )


def is_bank_income(transaction: FinancialTransaction) -> bool:
    """ورژن Pythonic bank_income_filter؛ منبع حقیقت ستون cash_flow است."""
    if transaction.is_deleted or float(transaction.amount or 0.0) <= 0:
        return False
    return transaction.cash_flow == CashFlow.INCOME
