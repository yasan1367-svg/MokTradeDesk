"""فاز ۳۳ — سرویس برداشت پراپ (چرخه‌ی عمر + اتصال به FinancialTransaction).

قانون طلایی این فاز:
- **درآمد فقط در نقطه‌ی دریافت (RECEIVED)** ثبت می‌شود
  (`Transaction.type = PROFIT` ⇒ در `finance/summary` به‌عنوان Income شمرده می‌شود).
- **انتقال‌ها درآمد نیستند**: مسیر «Prop → Trust Wallet → Exchange → IRR → Bank Card»
  با `Transaction.type = EXCHANGE` و `from_account_id`/`to_account_id` ثبت می‌شود
  (در `finance/summary` در `total_transfers` می‌آید، نه `total_income`).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.prop import (
    PropStage,
    PropWithdrawal,
    StageType,
    WithdrawalStatus,
    WITHDRAWAL_TRANSITIONS,
)
from ..models.finance import (
    Account,
    Category,
    CategoryType,
    Currency,
    Transaction,
    TransactionType,
)

logger = logging.getLogger("moktrade")

INCOME_CATEGORY_NAME = "برداشت پراپ"
TRANSFER_CATEGORY_NAME = "انتقال بین حساب‌ها"


class PayoutService:
    """منطق مشترک برداشت پراپ (create / status-transition / transfer / update / delete)."""

    # ── helpers ──
    @staticmethod
    def _to_currency(value) -> Currency:
        raw = (str(value) if value is not None else "USD").upper()
        try:
            return Currency(raw)
        except ValueError:
            logger.warning("Invalid currency %r — falling back to USD", value)
            return Currency.USD

    @staticmethod
    def _get_or_create_category(
        db: Session, name: str, cat_type: CategoryType, color: str, icon: str
    ) -> Category:
        cat = db.query(Category).filter(Category.name == name).first()
        if cat:
            return cat
        cat = Category(name=name, type=cat_type, color=color, icon=icon)
        db.add(cat)
        db.flush()
        return cat

    @staticmethod
    def parse_datetime(value) -> datetime:
        """ISO 8601 → datetime آگاه از UTC (ناپذیرفتنی ⇒ ValueError)."""
        if not value:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @staticmethod
    def allowed_transitions(status) -> List[str]:
        current = status if isinstance(status, WithdrawalStatus) else WithdrawalStatus(status)
        return [s.value for s in WITHDRAWAL_TRANSITIONS.get(current, ())]

    # ── create (REQUESTED, بدون تراکنش مالی) ──
    @staticmethod
    def create(
        db: Session,
        *,
        stage: PropStage,
        amount: float,
        destination_account_id: int,
        note: Optional[str] = None,
        reference: Optional[str] = None,
        withdrawal_date=None,
        currency=None,
        commit: bool = True,
    ) -> PropWithdrawal:
        if amount <= 0:
            raise ValueError("مبلغ برداشت باید مثبت باشد")

        dest = db.query(Account).filter(Account.id == destination_account_id).first()
        if not dest:
            raise ValueError("حساب مقصد معتبر نیست (باید بانک/صرافی/کیف‌پول باشد)")

        try:
            when = PayoutService.parse_datetime(withdrawal_date)
        except ValueError:
            raise ValueError("فرمت تاریخ برداشت نامعتبر است (ISO 8601: YYYY-MM-DD)")

        withdrawal = PropWithdrawal(
            prop_stage_id=stage.id,
            amount=amount,
            currency=PayoutService._to_currency(currency if currency else dest.currency),
            destination_account_id=destination_account_id,
            withdrawal_date=when,
            status=WithdrawalStatus.REQUESTED,
            reference=reference,
            note=note,
        )
        db.add(withdrawal)
        if commit:
            db.commit()
            db.refresh(withdrawal)
        else:
            db.flush()
        return withdrawal

    # ── status transition (نقطه‌ی دریافت) ──
    @staticmethod
    def set_status(
        db: Session,
        withdrawal: PropWithdrawal,
        new_status,
        *,
        commit: bool = True,
    ) -> Tuple[PropWithdrawal, Optional[Transaction]]:
        """وضعیت برداشت را تغییر می‌دهد و در صورت RECEIVED، درآمد را ثبت می‌کند."""
        target = new_status if isinstance(new_status, WithdrawalStatus) else WithdrawalStatus(new_status)
        current = (
            withdrawal.status
            if isinstance(withdrawal.status, WithdrawalStatus)
            else WithdrawalStatus(withdrawal.status)
        )
        if target == current:
            return withdrawal, None
        if target not in WITHDRAWAL_TRANSITIONS.get(current, ()):
            raise ValueError(f"انتقال وضعیت از {current.value} به {target.value} مجاز نیست")

        withdrawal.status = target
        posted: Optional[Transaction] = None
        if target == WithdrawalStatus.RECEIVED:
            posted = PayoutService._post_income(db, withdrawal)

        if commit:
            db.commit()
            db.refresh(withdrawal)
        else:
            db.flush()
        return withdrawal, posted

    @staticmethod
    def _post_income(db: Session, withdrawal: PropWithdrawal) -> Optional[Transaction]:
        """درآمد را در نقطه‌ی دریافت ثبت می‌کند (idempotent — بدون Double Counting)."""
        if withdrawal.transaction_id:
            return (
                db.query(Transaction)
                .filter(Transaction.id == withdrawal.transaction_id)
                .first()
            )

        dest = (
            db.query(Account)
            .filter(Account.id == withdrawal.destination_account_id)
            .first()
        )
        if not dest:
            raise ValueError("حساب مقصد معتبر نیست")

        stage = db.query(PropStage).filter(PropStage.id == withdrawal.prop_stage_id).first()
        label = stage.account.account_label if stage and stage.account else "پراپ"

        cat = PayoutService._get_or_create_category(
            db, INCOME_CATEGORY_NAME, CategoryType.INCOME, "#27AE60", "💰"
        )
        description = f"برداشت از {label}"
        if withdrawal.note:
            description += f" - {withdrawal.note}"

        tx = Transaction(
            account_id=dest.id,
            category_id=cat.id,
            amount=withdrawal.amount,
            currency=withdrawal.currency or Currency.USD,
            date=withdrawal.withdrawal_date,
            description=description,
            type=TransactionType.PROFIT,  # ← درآمد واقعی (نه withdrawal)
            from_account_id=None,
            to_account_id=dest.id,
            related_prop_account_id=stage.prop_account_id if stage else None,
        )
        db.add(tx)
        db.flush()

        dest.balance = (dest.balance or 0.0) + (withdrawal.amount or 0.0)
        withdrawal.transaction_id = tx.id
        if stage:
            stage.total_withdrawn = (stage.total_withdrawn or 0.0) + (withdrawal.amount or 0.0)
        return tx

    # ── انتقال بین حسابFinancial (درآمد نیست) ──
    @staticmethod
    def record_transfer(
        db: Session,
        *,
        from_account_id: int,
        to_account_id: int,
        amount: float,
        currency=None,
        note: Optional[str] = None,
        related_prop_account_id: Optional[int] = None,
        date=None,
        commit: bool = True,
    ) -> Transaction:
        """یک پرش انتقال (مثلاً Trust Wallet → Exchange) را ثبت می‌کند.

        نوع تراکنش `EXCHANGE` است ⇒ در `finance/summary` به‌عنوان **انتقال** شمرده
        می‌شود، نه درآمد. موجودی مبدأ کم و مقصد زیاد می‌شود.
        """
        if amount <= 0:
            raise ValueError("مبلغ انتقال باید مثبت باشد")
        if from_account_id == to_account_id:
            raise ValueError("حساب مبدأ و مقصد باید متفاوت باشند")

        src = db.query(Account).filter(Account.id == from_account_id).first()
        dst = db.query(Account).filter(Account.id == to_account_id).first()
        if not src or not dst:
            raise ValueError("حساب مبدأ یا مقصد معتبر نیست")

        try:
            when = PayoutService.parse_datetime(date)
        except ValueError:
            raise ValueError("فرمت تاریخ انتقال نامعتبر است (ISO 8601)")

        cat = PayoutService._get_or_create_category(
            db, TRANSFER_CATEGORY_NAME, CategoryType.TRANSFER, "#6366f1", "🔄"
        )
        tx = Transaction(
            account_id=dst.id,
            category_id=cat.id,
            amount=amount,
            currency=PayoutService._to_currency(currency if currency else dst.currency),
            date=when,
            description=note or f"انتقال از {src.name} به {dst.name}",
            type=TransactionType.EXCHANGE,  # ← انتقال، نه درآمد
            from_account_id=src.id,
            to_account_id=dst.id,
            related_prop_account_id=related_prop_account_id,
        )
        db.add(tx)
        db.flush()

        src.balance = (src.balance or 0.0) - amount
        dst.balance = (dst.balance or 0.0) + amount

        if commit:
            db.commit()
            db.refresh(tx)
        else:
            db.flush()
        return tx

    # ── update ──
    @staticmethod
    def update(db: Session, withdrawal: PropWithdrawal, payload: dict, *, commit: bool = True):
        """ویرایش برداشت با حفظ یکپارچگی مالی.

        - تغییر وضعیت ⇒ از مسیر `set_status` (با ثبت درآمد در RECEIVED)
        - تغییر مبلغ در حالت RECEIVED ⇒ هم‌زمان با ترمیم تراکنش/موجودی/`total_withdrawn`
        """
        payload = dict(payload)

        if payload.get("currency") is not None:
            payload["currency"] = PayoutService._to_currency(payload["currency"])

        if "withdrawal_date" in payload and payload["withdrawal_date"]:
            try:
                payload["withdrawal_date"] = PayoutService.parse_datetime(payload["withdrawal_date"])
            except ValueError:
                raise ValueError("فرمت تاریخ برداشت نامعتبر است (ISO 8601: YYYY-MM-DD)")

        if "destination_account_id" in payload and payload["destination_account_id"] is not None:
            dest = db.query(Account).filter(Account.id == payload["destination_account_id"]).first()
            if not dest:
                raise ValueError("حساب مقصد معتبر نیست")

        status = payload.pop("status", None)
        if status is not None:
            target = status if isinstance(status, WithdrawalStatus) else WithdrawalStatus(status)
            current = (
                withdrawal.status
                if isinstance(withdrawal.status, WithdrawalStatus)
                else WithdrawalStatus(withdrawal.status)
            )
            if target != current:
                PayoutService.set_status(db, withdrawal, target, commit=False)

        if "amount" in payload and payload["amount"] is not None:
            new_amount = float(payload["amount"])
            old_amount = float(withdrawal.amount or 0.0)
            delta = new_amount - old_amount
            if delta != 0 and withdrawal.transaction_id:
                tx = db.query(Transaction).filter(Transaction.id == withdrawal.transaction_id).first()
                if tx and not tx.is_deleted:
                    tx.amount = new_amount
                    dest = db.query(Account).filter(Account.id == tx.account_id).first()
                    if dest:
                        dest.balance = (dest.balance or 0.0) + delta
                    stage = db.query(PropStage).filter(PropStage.id == withdrawal.prop_stage_id).first()
                    if stage:
                        stage.total_withdrawn = max((stage.total_withdrawn or 0.0) + delta, 0.0)

        for field, value in payload.items():
            if hasattr(withdrawal, field):
                setattr(withdrawal, field, value)

        if commit:
            db.commit()
            db.refresh(withdrawal)
        else:
            db.flush()
        return withdrawal

    # ── delete + reverse ──
    @staticmethod
    def delete_and_reverse(db: Session, withdrawal: PropWithdrawal, *, commit: bool = True) -> None:
        """حذف برداشت + برگشت اثر مالی آن (اگر دریافت شده بود)."""
        if withdrawal.transaction_id:
            tx = db.query(Transaction).filter(Transaction.id == withdrawal.transaction_id).first()
            if tx and not tx.is_deleted:
                dest = db.query(Account).filter(Account.id == tx.account_id).first()
                if dest:
                    dest.balance = (dest.balance or 0.0) - (tx.amount or 0.0)
                stage = db.query(PropStage).filter(PropStage.id == withdrawal.prop_stage_id).first()
                if stage:
                    stage.total_withdrawn = max(
                        (stage.total_withdrawn or 0.0) - (withdrawal.amount or 0.0), 0.0
                    )
                tx.is_deleted = True

        db.delete(withdrawal)
        if commit:
            db.commit()
        else:
            db.flush()


