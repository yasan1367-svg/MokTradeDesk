import os
import shutil
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TransactionCategory(str, Enum):
    PROP_PAYOUT = "Prop Payout"
    PERSONAL_TRADE_PNL = "Personal Trade P&L"
    PROP_CHALLENGE_FEE = "Prop Challenge Fee"
    VPS_EXPENSE = "VPS Expense"
    DEPOSIT = "Deposit"
    WITHDRAWAL = "Withdrawal"
    OTHER_INCOME = "Other Income"
    OTHER_EXPENSE = "Other Expense"


class TransactionType(str, Enum):
    INCOME = "Income"
    EXPENSE = "Expense"


class EmotionalState(str, Enum):
    CALM = "Calm"
    CONFIDENT = "Confident"
    ANXIOUS = "Anxious"
    REVENGE = "Revenge Trading"
    FOMO = "FOMO"
    GREEDY = "Greedy"
    DISCIPLINED = "Disciplined"


class ExecutionQuality(str, Enum):
    EXCELLENT = "A+ (Flawless)"
    GOOD = "A (Good Execution)"
    AVERAGE = "B (Minor Mistakes)"
    POOR = "C (Broke Rules)"
    BLUNDER = "F (Severe Mistake)"


class LedgerTransaction(BaseModel):
    id: int
    account_id: int
    category: TransactionCategory
    type: TransactionType
    amount: float
    description: Optional[str] = None
    reference_id: Optional[str] = None  # مانند trade_id یا payout_id برای auto-sync
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JournalEntry(BaseModel):
    id: int
    trade_id: str
    execution_quality: ExecutionQuality
    emotional_state: EmotionalState
    notes: Optional[str] = None
    lessons_learned: Optional[str] = None
    screenshot_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PersonalAccount(BaseModel):
    id: int
    name: str
    balance: float = 0.0
    currency: str = "USD"


class PersonalService:
    # دیتابیس درون‌حافظه‌ای جهت توسعه و تست
    accounts_db: Dict[int, PersonalAccount] = {
        1: PersonalAccount(id=1, name="Main Trading Account", balance=10000.0)
    }
    transactions_db: Dict[int, LedgerTransaction] = {}
    journal_db: Dict[str, JournalEntry] = {}  # Key: trade_id

    _tx_counter = 1
    _journal_counter = 1
    UPLOAD_DIR = "uploads/screenshots"

    @classmethod
    def _ensure_upload_dir(cls):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)

    @classmethod
    def add_transaction(
        cls,
        account_id: int,
        category: TransactionCategory,
        tx_type: TransactionType,
        amount: float,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        tx_timestamp: Optional[datetime] = None
    ) -> LedgerTransaction:
        account = cls.accounts_db.get(account_id)
        if not account:
            raise ValueError(f"Personal account with id {account_id} not found.")

        # به‌روزرسانی موجودی حساب
        if tx_type == TransactionType.INCOME:
            account.balance += amount
        else:
            account.balance -= amount

        tx = LedgerTransaction(
            id=cls._tx_counter,
            account_id=account_id,
            category=category,
            type=tx_type,
            amount=amount,
            description=description,
            reference_id=reference_id,
            timestamp=tx_timestamp or datetime.utcnow()
        )
        cls.transactions_db[tx.id] = tx
        cls._tx_counter += 1
        return tx

    @classmethod
    def auto_sync_personal_pnl(cls, account_id: int, trade_id: str, pnl: float) -> LedgerTransaction:
        """
        همگام‌سازی خودکار سود/زیان معامله شخصی با دفتر کل
        """
        tx_type = TransactionType.INCOME if pnl >= 0 else TransactionType.EXPENSE
        amount = abs(pnl)
        desc = f"Auto-sync PnL for Trade #{trade_id}"

        return cls.add_transaction(
            account_id=account_id,
            category=TransactionCategory.PERSONAL_TRADE_PNL,
            tx_type=tx_type,
            amount=amount,
            description=desc,
            reference_id=f"TRADE_{trade_id}"
        )

    @classmethod
    def auto_sync_prop_payout(cls, account_id: int, payout_id: str, amount: float) -> LedgerTransaction:
        """
        همگام‌سازی خودکار برداشت سود از حساب پراپ به حساب شخصی
        """
        desc = f"Prop Firm Payout Deposit #{payout_id}"
        return cls.add_transaction(
            account_id=account_id,
            category=TransactionCategory.PROP_PAYOUT,
            tx_type=TransactionType.INCOME,
            amount=amount,
            description=desc,
            reference_id=f"PAYOUT_{payout_id}"
        )

    @classmethod
    def get_cash_flow_report(
        cls,
        account_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        محاسبه گزارش جریان نقدی (Cash Flow) با امکان فیلتر بر اساس بازه زمانی
        """
        txs = list(cls.transactions_db.values())

        if account_id:
            txs = [t for t in txs if t.account_id == account_id]
        if start_date:
            txs = [t for t in txs if t.timestamp >= start_date]
        if end_date:
            txs = [t for t in txs if t.timestamp <= end_date]

        total_income = sum(t.amount for t in txs if t.type == TransactionType.INCOME)
        total_expense = sum(t.amount for t in txs if t.type == TransactionType.EXPENSE)
        net_cash_flow = total_income - total_expense

        # تفکیک بر اساس دسته‌بندی
        breakdown = {}
        for cat in TransactionCategory:
            cat_txs = [t for t in txs if t.category == cat]
            cat_income = sum(t.amount for t in cat_txs if t.type == TransactionType.INCOME)
            cat_expense = sum(t.amount for t in cat_txs if t.type == TransactionType.EXPENSE)
            breakdown[cat.value] = {
                "income": round(cat_income, 2),
                "expense": round(cat_expense, 2),
                "net": round(cat_income - cat_expense, 2)
            }

        return {
            "period": {
                "start": start_date.isoformat() if start_date else "Beginning",
                "end": end_date.isoformat() if end_date else "Now"
            },
            "summary": {
                "total_income": round(total_income, 2),
                "total_expense": round(total_expense, 2),
                "net_cash_flow": round(net_cash_flow, 2)
            },
            "category_breakdown": breakdown
        }

    @classmethod
    def upsert_journal_entry(
        cls,
        trade_id: str,
        execution_quality: ExecutionQuality,
        emotional_state: EmotionalState,
        notes: Optional[str] = None,
        lessons_learned: Optional[str] = None
    ) -> JournalEntry:
        """
        ثبت یا ویرایش ژورنال معامله
        """
        entry = cls.journal_db.get(trade_id)
        if entry:
            entry.execution_quality = execution_quality
            entry.emotional_state = emotional_state
            entry.notes = notes
            entry.lessons_learned = lessons_learned
            entry.updated_at = datetime.utcnow()
        else:
            entry = JournalEntry(
                id=cls._journal_counter,
                trade_id=trade_id,
                execution_quality=execution_quality,
                emotional_state=emotional_state,
                notes=notes,
                lessons_learned=lessons_learned
            )
            cls.journal_db[trade_id] = entry
            cls._journal_counter += 1

        return entry

    @classmethod
    def save_journal_screenshot(cls, trade_id: str, file_bytes: bytes, filename: str) -> str:
        """
        ذخیره محلی فایل اسکرین‌شات چارت در پوشه uploads و پیوند آن به ژورنال
        """
        cls._ensure_upload_dir()
        ext = os.path.splitext(filename)[1] or ".png"
        unique_filename = f"trade_{trade_id}_{int(datetime.utcnow().timestamp())}{ext}"
        file_path = os.path.join(cls.UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # پیوند آدرس تصویر به ژورنال مربوطه
        entry = cls.journal_db.get(trade_id)
        if entry:
            entry.screenshot_url = file_path
            entry.updated_at = datetime.utcnow()

        return file_path