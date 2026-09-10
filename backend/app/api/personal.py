from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.services.personal_service import (
    PersonalService,
    TransactionCategory,
    TransactionType,
    PersonalAccount
)

router = APIRouter(prefix="/api/personal", tags=["Personal Ledger"])


class AccountCreateRequest(BaseModel):
    name: str
    initial_balance: float = 0.0
    currency: str = "USD"


class ManualTransactionRequest(BaseModel):
    account_id: int
    category: TransactionCategory
    type: TransactionType
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    timestamp: Optional[datetime] = None


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_personal_account(payload: AccountCreateRequest):
    acc_id = len(PersonalService.accounts_db) + 1
    acc = PersonalAccount(
        id=acc_id,
        name=payload.name,
        balance=payload.initial_balance,
        currency=payload.currency
    )
    PersonalService.accounts_db[acc_id] = acc
    return {"message": "حساب شخصی جدید ایجاد شد", "account": acc}


@router.get("/accounts")
async def list_personal_accounts():
    return list(PersonalService.accounts_db.values())


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
async def add_manual_transaction(payload: ManualTransactionRequest):
    try:
        tx = PersonalService.add_transaction(
            account_id=payload.account_id,
            category=payload.category,
            tx_type=payload.type,
            amount=payload.amount,
            description=payload.description,
            tx_timestamp=payload.timestamp
        )
        return {"message": "تراکنش دفتر کل با موفقیت ثبت شد", "transaction": tx}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/transactions")
async def list_transactions(account_id: Optional[int] = None):
    txs = list(PersonalService.transactions_db.values())
    if account_id:
        txs = [t for t in txs if t.account_id == account_id]
    return txs


@router.get("/cash-flow")
async def get_cash_flow_report(
    account_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """
    گزارش جریان نقدی دفتر کل با فیلتر بازه زمانی
    """
    return PersonalService.get_cash_flow_report(
        account_id=account_id,
        start_date=start_date,
        end_date=end_date
    )