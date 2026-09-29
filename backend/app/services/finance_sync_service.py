"""سرویس همگام‌سازی معاملات → حسابداری (DEPRECATED در فاز ۲۸)

⚠️ تغییر معماری فاز ۲۷/۲۸:
پیش‌تر این سرویس هر معاملهٔ بستهٔ REAL را به یک `FinancialAccount` **مالی** پل می‌زد
(`Trade.finance_account_id` / `PropAccount.finance_account_id`). با تفکیک کامل دامنه‌ها،
این پل‌ها حذف شدند:

- `Trade` دیگر به هیچ حساب **مالی** وصل نیست (فقط `PersonalTradingAccount` / `PropStage`).
- `PropAccount.finance_account_id` حذف شد.
- پول تنها از مسیر **برداشت** (`PropWithdrawal.destination_account_id` → حساب مالی) وارد FINANCE می‌شود.

بنابراین این سرویس عملاً غیرفعال است تا طراحی «ثبت خودکار P&L معاملات در حسابداری»
در یک فاز جداگانه بازبینی شود. هر فراخوانی، ۰ برمی‌گرداند (بدون نوشتن FinancialTransaction).
"""
from typing import List, Optional

from sqlalchemy.orm import Session


class FinanceSyncService:
    """شِیم حفظ‌شده برای سازگاری فراخوانی‌ها — عملاً no-op (فاز ۲۸)."""

    def __init__(self, db: Session):
        self.db = db

    def sync_closed_trades(self, trade_ids: Optional[List[int]] = None) -> int:
        """غیرفعال: هیچ FinancialTransactionی ساخته نمی‌شود. همیشه ۰ برمی‌گرداند."""
        return 0