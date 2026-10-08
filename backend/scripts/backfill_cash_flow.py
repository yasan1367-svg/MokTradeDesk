"""Backfill cash_flow for existing transactions (فاز ۴۷.۱)."""
# Import همه‌ی مدل‌ها تا SQLAlchemy relationshipها رو بشناسه
from app.models import finance, strategy, prop, trading, personal, imports  # noqa: F401
from app.core.database import SessionLocal
from app.models.finance import FinancialTransaction, CashFlow, TransactionType, FinancialAccount
from app.services.wallet_service import detect_cash_flow


def main():
    db = SessionLocal()
    try:
        rows = db.query(FinancialTransaction).filter(
            FinancialTransaction.is_deleted == False
        ).all()
        updated = 0
        for tx in rows:
            from_acc = db.get(FinancialAccount, tx.from_account_id) if tx.from_account_id else None
            to_acc = db.get(FinancialAccount, tx.to_account_id) if tx.to_account_id else None
            target = db.get(FinancialAccount, tx.account_id) if tx.account_id else None
            if tx.type in (TransactionType.DEPOSIT, TransactionType.PROFIT, TransactionType.EXTERNAL_INCOME):
                to_acc = target
            elif tx.type in (TransactionType.WITHDRAWAL, TransactionType.LOSS, TransactionType.FEE, TransactionType.PURCHASE, TransactionType.EXTERNAL_EXPENSE):
                from_acc = target
            new_flow = detect_cash_flow(tx.type, from_account=from_acc, to_account=to_acc)
            if tx.cash_flow != new_flow:
                tx.cash_flow = new_flow
                updated += 1
        db.commit()
        print(f"Updated {updated} transactions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()