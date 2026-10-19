"""گردش وجه حساب‌های معاملاتی شخصی بروکر ↔ حساب‌های مالی."""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session, joinedload

from ..core.database import get_db
from ..models.finance import Currency
from ..models.trading import BrokerCashMovement, PersonalTradingAccount
from ..services.broker_cash_service import (
    DEPOSIT_TO_BROKER,
    WITHDRAWAL_FROM_BROKER,
    BrokerCashService,
)

router = APIRouter()


def _parse_filter_date(value: Optional[str], *, end: bool = False):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="فرمت تاریخ معتبر نیست")
    if end and len(value) == 10:
        from datetime import time
        parsed = datetime.combine(parsed.date(), time.max)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


class BrokerCashMovementCreate(BaseModel):
    direction: Literal["deposit_to_broker", "withdrawal_from_broker"]
    personal_trading_account_id: int
    financial_account_id: int
    amount: float = Field(gt=0, allow_inf_nan=False)
    date: Optional[datetime] = None
    note: Optional[str] = None


class BrokerCashMovementUpdate(BaseModel):
    direction: Optional[Literal["deposit_to_broker", "withdrawal_from_broker"]] = None
    personal_trading_account_id: Optional[int] = None
    financial_account_id: Optional[int] = None
    amount: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    date: Optional[datetime] = None
    note: Optional[str] = None

    @model_validator(mode="after")
    def reject_empty_required_fields(self):
        for field in ("direction", "personal_trading_account_id", "financial_account_id", "amount"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError("نوع گردش، حساب‌ها و مبلغ نمی‌توانند خالی باشند")
        return self


def _movement_query(
    db: Session,
    *,
    personal_trading_account_id: Optional[int] = None,
    financial_account_id: Optional[int] = None,
    currency: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    # هر گزارش فقط یک ارز را جمع می‌زند؛ پیش‌فرض مطابق ارز اصلی برنامه USDT است.
    target = currency or Currency.USDT.value
    q = (
        db.query(BrokerCashMovement)
        .options(
            joinedload(BrokerCashMovement.trading_account).joinedload(PersonalTradingAccount.broker),
            joinedload(BrokerCashMovement.financial_account),
        )
        .filter(BrokerCashMovement.currency == target)
    )
    if personal_trading_account_id:
        q = q.filter(BrokerCashMovement.personal_trading_account_id == personal_trading_account_id)
    if financial_account_id:
        q = q.filter(BrokerCashMovement.financial_account_id == financial_account_id)
    if direction:
        q = q.filter(BrokerCashMovement.direction == direction)
    if date_from:
        q = q.filter(BrokerCashMovement.date >= _parse_filter_date(date_from))
    if date_to:
        q = q.filter(BrokerCashMovement.date <= _parse_filter_date(date_to, end=True))
    return q


def _serialize(movement: BrokerCashMovement) -> dict:
    trading = movement.trading_account
    financial = movement.financial_account
    broker = trading.broker if trading else None
    return {
        "id": movement.id,
        "direction": movement.direction,
        "personal_trading_account_id": movement.personal_trading_account_id,
        "personal_account_name": (trading.account_label or trading.account_number) if trading else None,
        "broker_name": broker.name if broker else None,
        "financial_account_id": movement.financial_account_id,
        "financial_account_name": financial.name if financial else None,
        "destination_account_name": financial.name if financial else None,
        "account_id": movement.personal_trading_account_id,  # سازگاری فیلترهای قدیمی
        "account_name": financial.name if financial else None,
        "amount": movement.amount,
        "currency": movement.currency.value if movement.currency else None,
        "date": movement.date.isoformat() if movement.date else None,
        "description": movement.note,
        "note": movement.note,
    }


@router.get("/cash-movements")
def list_cash_movements(
    personal_trading_account_id: Optional[int] = None,
    financial_account_id: Optional[int] = None,
    currency: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    rows = _movement_query(
        db,
        personal_trading_account_id=personal_trading_account_id,
        financial_account_id=financial_account_id,
        currency=currency,
        direction=direction,
        date_from=date_from,
        date_to=date_to,
    ).order_by(BrokerCashMovement.date.desc(), BrokerCashMovement.id.desc()).all()
    return [_serialize(row) for row in rows]


@router.get("/cash-movements/stats")
def get_cash_movement_stats(
    personal_trading_account_id: Optional[int] = None,
    financial_account_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = _movement_query(
        db,
        personal_trading_account_id=personal_trading_account_id,
        financial_account_id=financial_account_id,
        currency=currency,
        date_from=date_from,
        date_to=date_to,
    )
    rows = q.all()
    deposits = [r for r in rows if r.direction == DEPOSIT_TO_BROKER]
    withdrawals = [r for r in rows if r.direction == WITHDRAWAL_FROM_BROKER]
    amounts = [float(r.amount or 0.0) for r in rows]
    monthly: dict[str, dict[str, float]] = {}
    by_account: dict[int, dict] = {}
    for row in rows:
        month = row.date.strftime("%Y-%m") if row.date else "بدون تاریخ"
        bucket = monthly.setdefault(month, {"deposits": 0.0, "withdrawals": 0.0, "amount": 0.0})
        key = "deposits" if row.direction == DEPOSIT_TO_BROKER else "withdrawals"
        bucket[key] += float(row.amount or 0.0)
        bucket["amount"] += float(row.amount or 0.0)

        account = row.trading_account
        account_id = account.id if account else 0
        name = (account.account_label or account.account_number) if account else "حساب حذف‌شده"
        by_account.setdefault(account_id, {"name": name, "amount": 0.0, "count": 0})
        by_account[account_id]["amount"] += float(row.amount or 0.0)
        by_account[account_id]["count"] += 1

    return {
        "total": round(sum(amounts), 2),
        "total_deposits": round(sum(float(r.amount or 0.0) for r in deposits), 2),
        "total_withdrawals": round(sum(float(r.amount or 0.0) for r in withdrawals), 2),
        "count": len(rows),
        "average": round(sum(amounts) / len(amounts), 2) if amounts else 0.0,
        "largest": round(max(amounts), 2) if amounts else 0.0,
        "monthly": [
            {"month": month, **{key: round(value, 2) for key, value in bucket.items()}}
            for month, bucket in sorted(monthly.items())
        ],
        "by_account": [
            {**value, "amount": round(value["amount"], 2)}
            for _, value in sorted(by_account.items())
        ],
    }


@router.post("/cash-movements")
def create_cash_movement(data: BrokerCashMovementCreate, db: Session = Depends(get_db)):
    try:
        row = BrokerCashService.create(db, data.model_dump())
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "گردش بروکر ثبت شد", "movement": _serialize(row)}


@router.patch("/cash-movements/{movement_id}")
def update_cash_movement(
    movement_id: int, data: BrokerCashMovementUpdate, db: Session = Depends(get_db)
):
    row = db.query(BrokerCashMovement).filter(BrokerCashMovement.id == movement_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="گردش بروکر پیدا نشد")
    try:
        row = BrokerCashService.update(db, row, data.model_dump(exclude_unset=True))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "گردش بروکر ویرایش شد", "movement": _serialize(row)}


@router.delete("/cash-movements/{movement_id}")
def delete_cash_movement(movement_id: int, db: Session = Depends(get_db)):
    row = db.query(BrokerCashMovement).filter(BrokerCashMovement.id == movement_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="گردش بروکر پیدا نشد")
    try:
        BrokerCashService.delete(db, row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "گردش بروکر حذف و اثر موجودی برگردانده شد"}


def _legacy_withdrawals(db: Session, account_id=None, currency=None, date_from=None, date_to=None):
    return _movement_query(
        db,
        personal_trading_account_id=account_id,
        currency=currency,
        direction=WITHDRAWAL_FROM_BROKER,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/payouts")
def list_broker_payouts(
    account_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """سازگاری مسیر قدیمی؛ فقط برداشت واقعی از حساب معاملاتی بروکر."""
    rows = _legacy_withdrawals(db, account_id, currency, date_from, date_to).order_by(
        BrokerCashMovement.date.desc(), BrokerCashMovement.id.desc()
    ).all()
    return [_serialize(row) for row in rows]


@router.get("/payouts/stats")
def get_broker_payout_stats(
    account_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """سازگاری مسیر قدیمی آمار برداشت؛ فقط برداشت از حساب بروکر."""
    q = _legacy_withdrawals(db, account_id, currency, date_from, date_to)
    rows = q.all()
    total = sum(float(row.amount or 0.0) for row in rows)
    monthly: dict[str, float] = {}
    by_account: dict[int, dict] = {}
    for row in rows:
        month = row.date.strftime("%Y-%m") if row.date else "بدون تاریخ"
        monthly[month] = monthly.get(month, 0.0) + float(row.amount or 0.0)
        account = row.trading_account
        key = account.id if account else 0
        name = (account.account_label or account.account_number) if account else "حساب حذف‌شده"
        item = by_account.setdefault(key, {"name": name, "amount": 0.0, "count": 0})
        item["amount"] += float(row.amount or 0.0)
        item["count"] += 1
    return {
        "total": round(total, 2),
        "count": len(rows),
        "average": round(total / len(rows), 2) if rows else 0.0,
        "largest": round(max((float(row.amount or 0.0) for row in rows), default=0.0), 2),
        "monthly": [{"month": key, "amount": round(value, 2)} for key, value in sorted(monthly.items())],
        "by_account": [{**item, "amount": round(item["amount"], 2)} for _, item in sorted(by_account.items())],
    }
