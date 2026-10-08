"""API دامنهٔ TRADING (فاز ۲۸) — Broker + PersonalTradingAccount.

این دامنه از FINANCE جدا است. UI صفحهٔ مستقل Broker در فاز بعدی اضافه می‌شود؛
فعلاً فقط API ارائه می‌شود.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..core.database import get_db
from ..models.trading import Broker, BrokerCashMovement, PersonalTradingAccount
from ..models.finance import Currency

router = APIRouter()


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class BrokerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    website: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('نام بروکر نمی‌تواند خالی باشد')
        return v


class BrokerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    website: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError('نام بروکر نمی‌تواند خالی باشد')
        return v


class PersonalTradingAccountCreate(BaseModel):
    broker_id: int
    account_number: str = Field(..., min_length=1, max_length=100)
    account_label: Optional[str] = None
    currency: Currency = Currency.USDT
    initial_balance: float = Field(0.0, ge=0)
    current_balance: Optional[float] = Field(None, ge=0)  # اگر None باشد = initial_balance
    is_active: bool = True

    @field_validator('account_number')
    @classmethod
    def account_number_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('شماره حساب نمی‌تواند خالی باشد')
        return v


class PersonalTradingAccountUpdate(BaseModel):
    broker_id: Optional[int] = None
    account_number: Optional[str] = Field(None, min_length=1, max_length=100)
    account_label: Optional[str] = None
    currency: Optional[Currency] = None
    initial_balance: Optional[float] = Field(None, ge=0)
    current_balance: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator('account_number')
    @classmethod
    def account_number_not_blank(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError('شماره حساب نمی‌تواند خالی باشد')
        return v


def _serialize_broker(b: Broker) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "website": b.website,
        "notes": b.notes,
        "is_active": b.is_active,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _serialize_pta(a: PersonalTradingAccount) -> dict:
    return {
        "id": a.id,
        "broker_id": a.broker_id,
        "broker_name": a.broker.name if a.broker else None,
        "account_number": a.account_number,
        "account_label": a.account_label,
        "currency": a.currency.value if a.currency else None,
        "initial_balance": a.initial_balance,
        "current_balance": a.current_balance,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ═════════════════════════════════════════════
# Brokers
# ═════════════════════════════════════════════
@router.get("/brokers")
def list_brokers(db: Session = Depends(get_db)):
    rows = db.query(Broker).order_by(Broker.name.asc()).all()
    return [_serialize_broker(b) for b in rows]


@router.post("/brokers")
def create_broker(data: BrokerCreate, db: Session = Depends(get_db)):
    broker = Broker(**data.model_dump())
    db.add(broker)
    db.commit()
    db.refresh(broker)
    return {"id": broker.id, "message": "بروکر ساخته شد"}


@router.patch("/brokers/{broker_id}")
def update_broker(broker_id: int, data: BrokerUpdate, db: Session = Depends(get_db)):
    broker = db.query(Broker).filter(Broker.id == broker_id).first()
    if not broker:
        raise HTTPException(status_code=404, detail="بروکر پیدا نشد")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(broker, field, value)
    db.commit()
    db.refresh(broker)
    return {"message": "بروکر به‌روزرسانی شد", "broker": _serialize_broker(broker)}


@router.delete("/brokers/{broker_id}")
def delete_broker(broker_id: int, db: Session = Depends(get_db)):
    broker = db.query(Broker).filter(Broker.id == broker_id).first()
    if not broker:
        raise HTTPException(status_code=404, detail="بروکر پیدا نشد")
    # چک معاملات حساب‌های زیرمجموعه
    from ..models.strategy import Trade
    account_ids = [row.id for row in broker.accounts]
    if account_ids:
        trade_count = db.query(Trade).filter(
            Trade.personal_trading_account_id.in_(account_ids)
        ).count()
        if trade_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"حساب‌های این بروکر {trade_count} معامله دارند؛ ابتدا معاملات را حذف یا جابجا کن",
            )
    if account_ids and db.query(BrokerCashMovement.id).filter(
        BrokerCashMovement.personal_trading_account_id.in_(account_ids)
    ).first():
        raise HTTPException(status_code=400, detail="برای این بروکر گردش مالی ثبت شده؛ ابتدا تاریخچهٔ گردش‌ها را حذف کن")
    db.delete(broker)
    db.commit()
    return {"message": "بروکر حذف شد"}


# ═════════════════════════════════════════════
# Personal Trading Accounts
# ═════════════════════════════════════════════
@router.get("/accounts")
def list_accounts(broker_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(PersonalTradingAccount).options(selectinload(PersonalTradingAccount.broker))
    if broker_id:
        q = q.filter(PersonalTradingAccount.broker_id == broker_id)
    rows = q.order_by(PersonalTradingAccount.created_at.desc()).all()
    return [_serialize_pta(a) for a in rows]


@router.post("/accounts")
def create_account(data: PersonalTradingAccountCreate, db: Session = Depends(get_db)):
    broker = db.query(Broker).filter(Broker.id == data.broker_id).first()
    if not broker:
        raise HTTPException(status_code=404, detail="بروکر پیدا نشد")

    current = data.current_balance if data.current_balance is not None else data.initial_balance
    account = PersonalTradingAccount(
        broker_id=data.broker_id,
        account_number=data.account_number,
        account_label=data.account_label,
        currency=data.currency,
        initial_balance=data.initial_balance,
        current_balance=current,
        is_active=data.is_active,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"id": account.id, "message": "حساب معاملاتی ساخته شد"}


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, data: PersonalTradingAccountUpdate, db: Session = Depends(get_db)):
    account = db.query(PersonalTradingAccount).filter(PersonalTradingAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب معاملاتی پیدا نشد")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("broker_id") is not None:
        broker = db.query(Broker).filter(Broker.id == payload["broker_id"]).first()
        if not broker:
            raise HTTPException(status_code=404, detail="بروکر پیدا نشد")
    if payload.get("currency") is not None and payload["currency"] != account.currency:
        if db.query(BrokerCashMovement.id).filter(
            BrokerCashMovement.personal_trading_account_id == account.id
        ).first():
            raise HTTPException(status_code=400, detail="ارز حسابی که گردش مالی دارد قابل تغییر نیست")
    for field, value in payload.items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return {"message": "حساب معاملاتی به‌روزرسانی شد", "account": _serialize_pta(account)}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(PersonalTradingAccount).filter(PersonalTradingAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب معاملاتی پیدا نشد")
    # چک معاملات
    from ..models.strategy import Trade
    trade_count = db.query(Trade).filter(
        Trade.personal_trading_account_id == account.id
    ).count()
    if trade_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"این حساب {trade_count} معامله دارد؛ ابتدا معاملات را حذف یا جابجا کن",
        )
    if db.query(BrokerCashMovement.id).filter(
        BrokerCashMovement.personal_trading_account_id == account.id
    ).first():
        raise HTTPException(status_code=400, detail="برای این حساب گردش مالی ثبت شده؛ ابتدا تاریخچهٔ گردش‌ها را حذف کن")
    db.delete(account)
    db.commit()
    return {"message": "حساب معاملاتی حذف شد"}
