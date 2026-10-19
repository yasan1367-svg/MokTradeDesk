"""گردش واقعی وجه بین حساب معاملاتی شخصی و حساب مالی کاربر."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from ..models.finance import (
    AccountType,
    Category,
    CategoryType,
    FinancialAccount,
    FinancialTransaction,
    TransactionType,
)
from ..models.trading import BrokerCashMovement, PersonalTradingAccount
from .wallet_service import WalletError, WalletService

DEPOSIT_TO_BROKER = "deposit_to_broker"
WITHDRAWAL_FROM_BROKER = "withdrawal_from_broker"
_DIRECTIONS = {DEPOSIT_TO_BROKER, WITHDRAWAL_FROM_BROKER}
_BANK_DEPOSIT_CATEGORY = "واریز از بروکر"


def _parse_date(value) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _category(db: Session) -> Category:
    row = db.query(Category).filter(
        Category.name == _BANK_DEPOSIT_CATEGORY,
        Category.type == CategoryType.INCOME,
    ).first()
    if row:
        return row
    row = Category(
        name=_BANK_DEPOSIT_CATEGORY,
        type=CategoryType.INCOME,
        color="#27AE60",
        icon="💰",
    )
    db.add(row)
    db.flush()
    return row


def _load_accounts(db: Session, trading_id: int, financial_id: int):
    trading = db.query(PersonalTradingAccount).options(joinedload(PersonalTradingAccount.broker)).filter(
        PersonalTradingAccount.id == trading_id
    ).first()
    financial = db.query(FinancialAccount).filter(FinancialAccount.id == financial_id).first()
    if not trading or not trading.is_active:
        raise ValueError("حساب معاملاتی بروکر پیدا نشد یا غیرفعال است")
    if not financial or financial.is_archived:
        raise ValueError("حساب مالی پیدا نشد یا آرشیو شده است")
    if trading.currency != financial.currency:
        raise ValueError("ارز حساب بروکر و حساب مالی باید یکسان باشد؛ تبدیل ارز را خارج از برنامه انجام بده")
    return trading, financial


def _validate(direction: str, amount: float) -> None:
    if direction not in _DIRECTIONS:
        raise ValueError("نوع گردش باید واریز به بروکر یا برداشت از بروکر باشد")
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("مبلغ گردش باید مثبت باشد")


def _trading_delta(direction: str, amount: float) -> float:
    return amount if direction == DEPOSIT_TO_BROKER else -amount


def _financial_tx_values(direction: str, financial: FinancialAccount, amount: float):
    if direction == DEPOSIT_TO_BROKER:
        # جابجایی سرمایهٔ خود کاربر به بروکر هزینه نیست.
        return TransactionType.ADJUSTMENT, -amount, None
    if financial.type == AccountType.BANK:
        # درآمد در لحظه‌ای ثبت می‌شود که مبلغ از بروکر به بانک برسد.
        return TransactionType.DEPOSIT, amount, _category
    # دریافت به کیف‌پول یا صرافی دارایی است، نه درآمد بانکی.
    return TransactionType.ADJUSTMENT, amount, None


def _description(direction: str, trading: PersonalTradingAccount, note: Optional[str]) -> str:
    label = trading.account_label or trading.account_number
    action = "واریز به بروکر" if direction == DEPOSIT_TO_BROKER else "برداشت از بروکر"
    text = f"{action} {trading.broker.name if trading.broker else ''} — {label}"
    return f"{text} - {note}" if note else text


def _post_financial_leg(
    db: Session,
    *,
    direction: str,
    trading: PersonalTradingAccount,
    financial: FinancialAccount,
    amount: float,
    date: datetime,
    note: Optional[str],
    commit: bool,
) -> FinancialTransaction:
    tx_type, signed_amount, category_factory = _financial_tx_values(direction, financial, amount)
    category_id = category_factory(db).id if category_factory else None
    return WalletService.post(
        db,
        account_id=financial.id,
        type=tx_type,
        amount=abs(signed_amount),
        signed_amount=signed_amount if tx_type == TransactionType.ADJUSTMENT else None,
        currency=financial.currency,
        date=date,
        category_id=category_id,
        description=_description(direction, trading, note),
        allow_overdraft=False,
        commit=commit,
    )


class BrokerCashService:
    @staticmethod
    def create(db: Session, payload: dict, *, commit: bool = True) -> BrokerCashMovement:
        direction = str(payload.get("direction", ""))
        amount = float(payload.get("amount") or 0.0)
        _validate(direction, amount)
        trading, financial = _load_accounts(
            db,
            int(payload["personal_trading_account_id"]),
            int(payload["financial_account_id"]),
        )
        if direction == DEPOSIT_TO_BROKER and float(financial.balance or 0.0) + 0.005 < amount:
            raise WalletError(f"موجودی حساب مالی «{financial.name}» برای واریز کافی نیست")
        if direction == WITHDRAWAL_FROM_BROKER and float(trading.current_balance or 0.0) + 0.005 < amount:
            raise ValueError("موجودی حساب معاملاتی بروکر برای برداشت کافی نیست")

        date = _parse_date(payload.get("date"))
        note = payload.get("note")
        tx = _post_financial_leg(
            db, direction=direction, trading=trading, financial=financial,
            amount=amount, date=date, note=note, commit=False,
        )
        movement = BrokerCashMovement(
            personal_trading_account_id=trading.id,
            financial_account_id=financial.id,
            transaction_id=tx.id,
            direction=direction,
            amount=amount,
            currency=trading.currency,
            date=date,
            note=note,
        )
        db.add(movement)
        db.flush()
        from .finance_sync_service import FinanceSyncService
        FinanceSyncService(db).recompute_account_balance(trading.id)
        if commit:
            db.commit()
            db.refresh(movement)
            db.refresh(trading)
        else:
            db.flush()
        return movement

    @staticmethod
    def update(db: Session, movement: BrokerCashMovement, payload: dict, *, commit: bool = True):
        direction = str(payload.get("direction", movement.direction))
        amount = float(payload.get("amount", movement.amount))
        _validate(direction, amount)
        trading_id = int(payload.get("personal_trading_account_id", movement.personal_trading_account_id))
        financial_id = int(payload.get("financial_account_id", movement.financial_account_id))
        trading, financial = _load_accounts(db, trading_id, financial_id)
        currency = trading.currency
        date = _parse_date(payload.get("date", movement.date))
        note = payload.get("note", movement.note)
        tx = db.query(FinancialTransaction).filter(
            FinancialTransaction.id == movement.transaction_id,
            FinancialTransaction.is_deleted == False,
        ).first()
        if tx is None:
            raise ValueError("تراکنش مالی این گردش حذف شده یا پیدا نشد؛ از حذف گردش بروکر استفاده کن")
        old_trading = db.query(PersonalTradingAccount).filter(
            PersonalTradingAccount.id == movement.personal_trading_account_id
        ).first()
        if old_trading is None:
            raise ValueError("حساب معاملاتی قبلی گردش پیدا نشد")

        old_trading_delta = _trading_delta(movement.direction, float(movement.amount or 0.0))
        new_trading_delta = _trading_delta(direction, amount)
        projected_trading = float(old_trading.current_balance or 0.0) - old_trading_delta
        projected = {}
        if old_trading.id == trading.id:
            projected_trading += new_trading_delta
            projected = {trading.id: projected_trading}
        else:
            projected[old_trading.id] = projected_trading
            projected[trading.id] = float(trading.current_balance or 0.0) + new_trading_delta
        for account_id, balance in projected.items():
            if balance < -0.005:
                raise ValueError(f"ویرایش باعث منفی‌شدن موجودی حساب معاملاتی {account_id} می‌شود")

        old_finance_deltas = WalletService.deltas(tx)
        new_tx_type, new_finance_delta, category_factory = _financial_tx_values(direction, financial, amount)
        new_finance_deltas = {financial.id: new_finance_delta}
        finance_ids = set(old_finance_deltas) | set(new_finance_deltas)
        financial_accounts = {
            a.id: a for a in db.query(FinancialAccount).filter(FinancialAccount.id.in_(finance_ids)).all()
        }
        for account_id in finance_ids:
            if account_id not in financial_accounts:
                raise ValueError(f"حساب مالی مرتبط با گردش پیدا نشد: {account_id}")
            projected_balance = (
                float(financial_accounts[account_id].balance or 0.0)
                - old_finance_deltas.get(account_id, 0.0)
                + new_finance_deltas.get(account_id, 0.0)
            )
            if projected_balance < -0.005:
                raise ValueError(f"ویرایش باعث منفی‌شدن موجودی حساب مالی «{financial_accounts[account_id].name}» می‌شود")

        WalletService.apply_effects(db, tx, sign=-1)
        tx.account_id = financial.id
        tx.type = new_tx_type
        tx.amount = new_finance_delta if new_tx_type == TransactionType.ADJUSTMENT else amount
        tx.currency = currency
        tx.date = date
        tx.category_id = category_factory(db).id if category_factory else None
        tx.description = _description(direction, trading, note)
        tx.from_account_id = None
        tx.to_account_id = None
        WalletService.apply_effects(db, tx, sign=+1)

        movement.personal_trading_account_id = trading.id
        movement.financial_account_id = financial.id
        movement.direction = direction
        movement.amount = amount
        movement.currency = currency
        movement.date = date
        movement.note = note
        db.flush()
        from .finance_sync_service import FinanceSyncService
        FinanceSyncService(db).recompute_accounts(list(projected), commit=False)
        if commit:
            db.commit()
            db.refresh(movement)
            for account_id in projected:
                account = db.get(PersonalTradingAccount, account_id)
                if account:
                    db.refresh(account)
        else:
            db.flush()
        return movement

    @staticmethod
    def delete(db: Session, movement: BrokerCashMovement, *, commit: bool = True) -> None:
        trading = db.query(PersonalTradingAccount).filter(
            PersonalTradingAccount.id == movement.personal_trading_account_id
        ).first()
        tx = db.query(FinancialTransaction).filter(
            FinancialTransaction.id == movement.transaction_id
        ).first()
        if trading is None or tx is None or tx.is_deleted:
            raise ValueError("حساب یا تراکنش مالی گردش پیدا نشد؛ امکان برگشت امن وجود ندارد")
        new_balance = float(trading.current_balance or 0.0) - _trading_delta(
            movement.direction, float(movement.amount or 0.0)
        )
        if new_balance < -0.005:
            raise ValueError("حذف گردش باعث منفی‌شدن موجودی حساب معاملاتی می‌شود")
        WalletService.reverse(db, tx, commit=False)
        db.delete(movement)
        db.flush()
        from .finance_sync_service import FinanceSyncService
        FinanceSyncService(db).recompute_account_balance(trading.id)
        db.flush()
        if commit:
            db.commit()
            db.refresh(trading)
        else:
            db.flush()
