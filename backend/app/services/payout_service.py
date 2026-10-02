"""سرویس برداشت پراپ (چرخه‌ی عمر + اتصال به FinancialTransaction).

قانون مالی:
- در وضعیت `RECEIVED` موجودی حساب مقصد به‌روز می‌شود.
- فقط دریافت در حساب بانکی `PROFIT` و درآمد محسوب می‌شود؛ دریافت در کیف‌پول/صرافی
  یک `ADJUSTMENT` مثبت است تا دارایی ثبت شود، بدون اینکه درآمد زودتر از واریز بانکی گزارش شود.
- انتقال‌های مالی با `TRANSFER` ثبت می‌شوند؛ انتقال از حساب غیربانکی به بانک
  در گزارش درآمد نیز محاسبه می‌شود. انتقال بین دو بانک درآمد تازه نیست.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.prop import (
    PropStage,
    PropWithdrawal,
    WithdrawalStatus,
    WITHDRAWAL_TRANSITIONS,
)
from ..models.finance import (
    AccountType,
    FinancialAccount,
    Category,
    CategoryType,
    Currency,
    FinancialTransaction,
    TransactionType,
)
# فاز ۳۹: تنها نویسندهٔ FinancialAccount.balance
from .wallet_service import WalletService
from ..utils.currency import to_currency

logger = logging.getLogger("moktrade")

INCOME_CATEGORY_NAME = "برداشت پراپ"
TRANSFER_CATEGORY_NAME = "انتقال بین حساب‌ها"


class PayoutService:
    """منطق مشترک برداشت پراپ (create / status-transition / transfer / update / delete)."""

    # ── helpers ──
    @staticmethod
    def _to_currency(value) -> Currency:
        """فاز ۴۵.۶: ابزار مشترک (invalid ⇒ USD با حفظ سازگاری قدیم)."""
        return to_currency(value, default=Currency.USDT)

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
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("مبلغ برداشت باید مثبت باشد")

        dest = db.query(FinancialAccount).filter(FinancialAccount.id == destination_account_id).first()
        if not dest:
            raise ValueError("حساب مقصد معتبر نیست (باید بانک/صرافی/کیف‌پول باشد)")

        payout_currency = PayoutService._to_currency(currency if currency else dest.currency)
        if payout_currency != dest.currency:
            raise ValueError("ارز برداشت باید با ارز حساب مقصد یکسان باشد؛ تبدیل ارز را در صرافی ثبت کنید")

        try:
            when = PayoutService.parse_datetime(withdrawal_date)
        except ValueError:
            raise ValueError("فرمت تاریخ برداشت نامعتبر است (ISO 8601: YYYY-MM-DD)")

        withdrawal = PropWithdrawal(
            prop_stage_id=stage.id,
            amount=amount,
            currency=payout_currency,
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
    ) -> Tuple[PropWithdrawal, Optional[FinancialTransaction]]:
        """وضعیت برداشت را تغییر می‌دهد و در RECEIVED موجودی مقصد را ثبت می‌کند."""
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
        posted: Optional[FinancialTransaction] = None
        if target == WithdrawalStatus.RECEIVED:
            posted = PayoutService._post_income(db, withdrawal)

        if commit:
            db.commit()
            db.refresh(withdrawal)
        else:
            db.flush()
        return withdrawal, posted

    @staticmethod
    def _post_income(db: Session, withdrawal: PropWithdrawal) -> Optional[FinancialTransaction]:
        """دریافت را ثبت می‌کند؛ فقط حساب بانکی درآمد است (idempotent)."""
        if withdrawal.transaction_id:
            return (
                db.query(FinancialTransaction)
                .filter(FinancialTransaction.id == withdrawal.transaction_id)
                .first()
            )

        dest = (
            db.query(FinancialAccount)
            .filter(FinancialAccount.id == withdrawal.destination_account_id)
            .first()
        )
        if not dest:
            raise ValueError("حساب مقصد معتبر نیست")

        stage = db.query(PropStage).filter(PropStage.id == withdrawal.prop_stage_id).first()
        label = stage.account.account_label if stage and stage.account else "پراپ"

        is_bank = dest.type == AccountType.BANK
        cat = PayoutService._get_or_create_category(
            db, INCOME_CATEGORY_NAME, CategoryType.INCOME, "#27AE60", "💰"
        )
        description = f"برداشت از {label}"
        if withdrawal.note:
            description += f" - {withdrawal.note}"

        tx = WalletService.post(
            db,
            account_id=dest.id,
            type=TransactionType.PROFIT,
            amount=withdrawal.amount,
            currency=withdrawal.currency or Currency.USDT,
            date=withdrawal.withdrawal_date,
            category_id=cat.id if cat else None,
            description=description,
            related_prop_account_id=stage.prop_account_id if stage else None,
            commit=False,                 # commit در set_status
        )
        withdrawal.transaction_id = tx.id
        if stage:
            stage.total_withdrawn = (stage.total_withdrawn or 0.0) + (withdrawal.amount or 0.0)
        return tx

    # ── انتقال بین حساب‌های مالی (درآمد نیست) ──
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
        allow_overdraft: bool = False,
        commit: bool = True,
    ) -> FinancialTransaction:
        """یک پرش انتقال (مثلاً Trust Wallet → Exchange) را ثبت می‌کند.

        نوع تراکنش `TRANSFER` است (فاز ۳۸.۴: جانشین `EXCHANGE` حذف‌شده) ⇒ در
        `finance/summary` به‌عنوان **انتقال** شمرده می‌شود، نه درآمد. موجودی مبدأ کم و مقصد زیاد می‌شود.

        فاز ۳۹: موجودی **فقط** از مسیر `WalletService` تغییر می‌کند و
        `allow_overdraft=False` (پیش‌فرض) مانع منفی‌شدن موجودی مبدأ می‌شود.
        """
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("مبلغ انتقال باید مثبت باشد")
        if from_account_id == to_account_id:
            raise ValueError("حساب مبدأ و مقصد باید متفاوت باشند")

        src = db.query(FinancialAccount).filter(FinancialAccount.id == from_account_id).first()
        dst = db.query(FinancialAccount).filter(FinancialAccount.id == to_account_id).first()
        if not src or not dst:
            raise ValueError("حساب مبدأ یا مقصد معتبر نیست")

        try:
            when = PayoutService.parse_datetime(date)
        except ValueError:
            raise ValueError("فرمت تاریخ انتقال نامعتبر است (ISO 8601)")

        cat = PayoutService._get_or_create_category(
            db, TRANSFER_CATEGORY_NAME, CategoryType.TRANSFER, "#6366f1", "🔄"
        )
        return WalletService.post(
            db,
            account_id=dst.id,               # ← مقصد (قرارداد فاز ۳۳)
            type=TransactionType.TRANSFER,   # ← انتقال، نه درآمد
            amount=amount,
            currency=PayoutService._to_currency(currency if currency else dst.currency),
            date=when,
            category_id=cat.id,
            from_account_id=src.id,
            to_account_id=dst.id,
            description=note or f"انتقال از {src.name} به {dst.name}",
            related_prop_account_id=related_prop_account_id,
            allow_overdraft=allow_overdraft,
            commit=commit,
        )

    # ── update ──
    @staticmethod
    def update(db: Session, withdrawal: PropWithdrawal, payload: dict, *, commit: bool = True):
        """ویرایش برداشت با حفظ یکپارچگی مالی.

        - تغییر وضعیت ⇒ از مسیر `set_status` (ثبت موجودی در RECEIVED)
        - تغییر مبلغ در حالت RECEIVED ⇒ هم‌زمان با ترمیم تراکنش/موجودی/`total_withdrawn`
        """
        payload = dict(payload)

        if payload.get("currency") is not None:
            payload["currency"] = PayoutService._to_currency(payload["currency"])

        if "withdrawal_date" in payload:
            try:
                payload["withdrawal_date"] = PayoutService.parse_datetime(payload["withdrawal_date"])
            except ValueError:
                raise ValueError("فرمت تاریخ برداشت نامعتبر است (ISO 8601: YYYY-MM-DD)")

        status = payload.pop("status", None)
        target = WithdrawalStatus(status) if status is not None else None
        current = WithdrawalStatus(withdrawal.status)
        if target is not None and target != current and target not in WITHDRAWAL_TRANSITIONS.get(current, ()):
            raise ValueError(f"انتقال وضعیت از {current.value} به {target.value} مجاز نیست")

        amount = float(payload.get("amount", withdrawal.amount))
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("مبلغ برداشت باید مثبت باشد")
        dest_id = payload.get("destination_account_id", withdrawal.destination_account_id)
        dest = db.query(FinancialAccount).filter(FinancialAccount.id == dest_id).first()
        if not dest:
            raise ValueError("حساب مقصد معتبر نیست")
        currency = payload.get("currency", withdrawal.currency or dest.currency)
        currency = PayoutService._to_currency(currency)
        if currency != dest.currency:
            raise ValueError("ارز برداشت باید با ارز حساب مقصد یکسان باشد؛ تبدیل ارز را در صرافی ثبت کنید")
        payload["amount"] = amount
        payload["destination_account_id"] = dest_id
        payload["currency"] = currency

        # در صورت ثبت قبلی دریافت، همان تراکنش را با مقصد و مشخصات جدید همگام می‌کنیم.
        tx = None
        if current == WithdrawalStatus.RECEIVED and not withdrawal.transaction_id:
            raise ValueError("برداشت دریافت‌شده تراکنش مالی متصل ندارد؛ ابتدا آن را از بخش مالی اصلاح کنید")
        if withdrawal.transaction_id:
            tx = db.query(FinancialTransaction).filter(
                FinancialTransaction.id == withdrawal.transaction_id
            ).first()
            if tx is None or tx.is_deleted:
                raise ValueError("تراکنش مالی دریافت‌شده حذف شده یا پیدا نشد؛ ابتدا ارتباط آن را از بخش مالی اصلاح کنید")
        if tx is not None:
            new_type = TransactionType.PROFIT
            old_deltas = WalletService.deltas(tx)
            new_delta = {dest.id: amount}
            account_ids = set(old_deltas) | set(new_delta)
            accounts = {a.id: a for a in db.query(FinancialAccount).filter(FinancialAccount.id.in_(account_ids)).all()}
            for aid in account_ids:
                if aid not in accounts:
                    raise ValueError(f"حساب مالی {aid} مرتبط با برداشت پیدا نشد")
                projected = float(accounts[aid].balance or 0.0) - old_deltas.get(aid, 0.0) + new_delta.get(aid, 0.0)
                if projected < -0.005:
                    raise ValueError(f"ویرایش باعث منفی‌شدن موجودی حساب «{accounts[aid].name}» می‌شود")
            WalletService.apply_effects(db, tx, sign=-1)
            tx.account_id = dest.id
            tx.from_account_id = None
            tx.to_account_id = None
            tx.type = new_type
            tx.amount = amount
            tx.currency = currency
            tx.date = payload.get("withdrawal_date", withdrawal.withdrawal_date)
            tx.category_id = PayoutService._get_or_create_category(db, INCOME_CATEGORY_NAME, CategoryType.INCOME, "#27AE60", "💰").id
            tx.description = f"برداشت از {withdrawal.stage.account.account_label if withdrawal.stage and withdrawal.stage.account else 'پراپ'}"
            if payload.get("note", withdrawal.note):
                tx.description += f" - {payload.get('note', withdrawal.note)}"
            tx.related_prop_account_id = withdrawal.stage.prop_account_id if withdrawal.stage else None
            WalletService.apply_effects(db, tx, sign=+1)
            stage = db.query(PropStage).filter(PropStage.id == withdrawal.prop_stage_id).first()
            if stage:
                stage.total_withdrawn = max(float(stage.total_withdrawn or 0.0) + amount - float(withdrawal.amount or 0.0), 0.0)

        for field, value in payload.items():
            if hasattr(withdrawal, field):
                setattr(withdrawal, field, value)

        if target is not None and target != current:
            PayoutService.set_status(db, withdrawal, target, commit=False)

        if commit:
            db.commit()
            db.refresh(withdrawal)
        else:
            db.flush()
        return withdrawal

    # ── delete + reverse ──
    @staticmethod
    def delete_and_reverse(db: Session, withdrawal: PropWithdrawal, *, commit: bool = True) -> None:
        """حذف برداشت + برگشت اثر مالی آن (اگر دریافت شده بود) — فاز ۳۹: از مسیر WalletService."""
        if withdrawal.transaction_id:
            tx = db.query(FinancialTransaction).filter(
                FinancialTransaction.id == withdrawal.transaction_id
            ).first()
            if tx and not tx.is_deleted:
                WalletService.reverse(db, tx, commit=False)
                stage = db.query(PropStage).filter(PropStage.id == withdrawal.prop_stage_id).first()
                if stage:
                    stage.total_withdrawn = max(
                        (stage.total_withdrawn or 0.0) - (withdrawal.amount or 0.0), 0.0
                    )

        db.delete(withdrawal)
        if commit:
            db.commit()
        else:
            db.flush()


