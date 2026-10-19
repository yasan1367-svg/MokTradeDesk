"""بازمحاسبهٔ موجودی حساب معاملاتی از معاملات بسته و گردش وجه بروکر."""
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.strategy import TestType, Trade
from ..models.trading import BrokerCashMovement, PersonalTradingAccount


class FinanceSyncService:
    def __init__(self, db: Session):
        self.db = db

    def recompute_account_balance(self, account_id: int) -> float:
        """بازمحاسبهٔ current_balance برای یک حساب معاملاتی."""
        account = self.db.get(PersonalTradingAccount, account_id)
        if account is None:
            return 0.0

        trade_sum = self.db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(Trade.pnl, 0)
                    + func.coalesce(Trade.commission, 0)
                    + func.coalesce(Trade.swap, 0)
                ),
                0.0,
            )
        ).filter(
            Trade.personal_trading_account_id == account_id,
            Trade.test_type == TestType.REAL_PERSONAL,
            Trade.close_time.isnot(None),
        ).scalar() or 0.0

        deposit_sum = self.db.query(
            func.coalesce(func.sum(BrokerCashMovement.amount), 0.0)
        ).filter(
            BrokerCashMovement.personal_trading_account_id == account_id,
            BrokerCashMovement.direction == "deposit_to_broker",
        ).scalar() or 0.0

        withdrawal_sum = self.db.query(
            func.coalesce(func.sum(BrokerCashMovement.amount), 0.0)
        ).filter(
            BrokerCashMovement.personal_trading_account_id == account_id,
            BrokerCashMovement.direction == "withdrawal_from_broker",
        ).scalar() or 0.0

        new_balance = (
            float(account.initial_balance or 0.0)
            + float(trade_sum)
            + float(deposit_sum)
            - float(withdrawal_sum)
        )
        account.current_balance = round(new_balance, 4)
        return account.current_balance

    def sync_closed_trades(self, trade_ids: Optional[List[int]] = None) -> int:
        """بازمحاسبهٔ حساب‌های متأثر؛ بدون شناسه‌ها همگام‌سازی همهٔ حساب‌ها."""
        if trade_ids:
            rows = self.db.query(Trade.personal_trading_account_id).filter(
                Trade.id.in_(trade_ids),
                Trade.personal_trading_account_id.isnot(None),
            ).distinct().all()
            account_ids = {row[0] for row in rows}
        else:
            trade_rows = self.db.query(Trade.personal_trading_account_id).filter(
                Trade.personal_trading_account_id.isnot(None)
            ).distinct().all()
            movement_rows = self.db.query(
                BrokerCashMovement.personal_trading_account_id
            ).distinct().all()
            account_ids = {row[0] for row in trade_rows}
            account_ids.update(row[0] for row in movement_rows)

        updated = 0
        for account_id in account_ids:
            if account_id is not None:
                self.recompute_account_balance(account_id)
                updated += 1
        self.db.commit()
        return updated

    def recompute_accounts(self, account_ids: list, *, commit: bool = True) -> int:
        """بازمحاسبه و commit حساب‌های مشخص‌شده."""
        updated = 0
        for account_id in set(account_ids):
            if account_id is not None:
                self.recompute_account_balance(account_id)
                updated += 1
        if commit:
            self.db.commit()
        return updated