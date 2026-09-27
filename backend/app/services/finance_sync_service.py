"""سرویس همگام‌سازی معاملات → حسابداری (فاز ۲۱)

وقتی یک معامله در بروکر یا مرحله ۳ پراپ بسته می‌شود، یک `Transaction`
ایجاد می‌کند و `Account.balance` را به‌روزرسانی می‌کند.

جلوگیری از تکرار: اگر `Transaction` با `related_trade_id` قبلاً وجود داشته باشد، نادیده گرفته می‌شود.
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from ..models.finance import Account, AccountType, Transaction, TransactionType, Currency
from ..models.strategy import Trade
from ..models.prop import PropStage, StageType, PropAccount


class FinanceSyncService:
    """همگام‌سازی معاملات بسته‌شده با حسابداری"""

    def __init__(self, db: Session):
        self.db = db

    def sync_closed_trades(self, trade_ids: Optional[List[int]] = None) -> int:
        """همه معاملات بسته‌شده‌ی بدون Transaction را پردازش می‌کند.

        Args:
            trade_ids: اگر داده شود فقط این معاملات خاص پردازش می‌شوند.

        Returns:
            تعداد Transactionهای ساخته‌شده
        """
        q = self.db.query(Trade).filter(
            Trade.close_time.isnot(None),
            # فاز ۲۵: معاملات حذف‌شده (Soft Delete) هرگز با حسابداری همگام نمی‌شوند
            Trade.is_deleted == False,
            # جلوگیری از تکرار
            ~self.db.query(Transaction).filter(
                Transaction.related_trade_id == Trade.id,
                Transaction.is_deleted == False,
            ).exists(),
        )
        if trade_ids:
            q = q.filter(Trade.id.in_(trade_ids))

        created = 0
        for trade in q.all():
            ok = self._process_trade(trade)
            if ok:
                created += 1

        if created > 0:
            self.db.commit()
        return created

    def _process_trade(self, trade: Trade) -> bool:
        """یک معامله را پردازش می‌کند. True اگر Transaction ساخته شود."""
        net_pnl = (trade.pnl or 0) + (trade.commission or 0) + (trade.swap or 0)
        if net_pnl == 0:
            return False

        account = self._find_account(trade)
        if not account:
            return False

        tx_type = TransactionType.PROFIT if net_pnl > 0 else TransactionType.LOSS
        amount = abs(net_pnl)
        currency = Currency.USD  # پیش‌فرض

        prop_account_id = None
        if trade.prop_stage_id:
            stage = self.db.query(PropStage).filter(
                PropStage.id == trade.prop_stage_id
            ).first()
            if stage:
                prop_account_id = stage.prop_account_id

        tx = Transaction(
            account_id=account.id,
            amount=amount,
            currency=currency,
            date=trade.close_time or trade.created_at,
            description=f"سود/زیان معامله #{trade.id}",
            type=tx_type,
            related_trade_id=trade.id,
            related_prop_account_id=prop_account_id,
        )
        self.db.add(tx)

        # به‌روزرسانی موجودی
        if tx_type == TransactionType.PROFIT:
            account.balance = (account.balance or 0) + amount
        else:
            account.balance = (account.balance or 0) - amount

        return True

    def _find_account(self, trade: Trade) -> Optional[Account]:
        """حساب مالی مربوط به معامله را پیدا می‌کند.

        اولویت: بروکر (finance_account_id) → پراپ مرحله ۳ (prop_stage_id)
        """
        if trade.finance_account_id:
            acct = self.db.query(Account).filter(
                Account.id == trade.finance_account_id
            ).first()
            if acct and acct.type == AccountType.BROKER:
                return acct

        if trade.prop_stage_id:
            stage = self.db.query(PropStage).filter(
                PropStage.id == trade.prop_stage_id
            ).first()
            if stage and stage.stage_type == StageType.FUNDED_REAL:
                prop_acc = self.db.query(PropAccount).filter(
                    PropAccount.id == stage.prop_account_id
                ).first()
                if prop_acc and prop_acc.finance_account_id:
                    return self.db.query(Account).filter(
                        Account.id == prop_acc.finance_account_id
                    ).first()

        return None