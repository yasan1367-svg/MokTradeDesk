from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.prop_service import PropService, PropFirmRules, PropStageType

router = APIRouter(prefix="/api/prop", tags=["Prop Desk"])


# DTO Schemas
class CreatePropFirmRequest(BaseModel):
    name: str
    rules: PropFirmRules


class CreatePropAccountRequest(BaseModel):
    firm_id: int
    account_number: str
    account_size: float = Field(..., gt=0)


class FailStageRequest(BaseModel):
    reason: str


class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0)


class UpdateEquityRequest(BaseModel):
    current_equity: float
    day_start_equity: float


# Endpoints
@router.post("/firms", status_code=status.HTTP_201_CREATED)
async def create_firm(payload: CreatePropFirmRequest):
    firm = PropService.create_firm(payload.name, payload.rules)
    return {"message": "شرکت پراپ با موفقیت ثبت شد", "firm": firm}


@router.get("/firms")
async def list_firms():
    return list(PropService.firms_db.values())


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_account(payload: CreatePropAccountRequest):
    try:
        account = PropService.create_account(
            firm_id=payload.firm_id,
            account_number=payload.account_number,
            account_size=payload.account_size
        )
        return {"message": "حساب پراپ و Stage 1 با موفقیت ساخته شد", "account": account}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/accounts")
async def list_accounts():
    return list(PropService.accounts_db.values())


@router.get("/accounts/{account_id}")
async def get_account_detail(account_id: int):
    account = PropService.accounts_db.get(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="حساب یافت نشد.")
    
    stages = [s for s in PropService.stages_db.values() if s.account_id == account_id]
    return {"account": account, "stages": stages}


@router.post("/stages/{stage_id}/update-equity")
async def update_stage_equity(stage_id: int, payload: UpdateEquityRequest):
    try:
        res = PropService.update_stage_equity(
            stage_id=stage_id,
            current_equity=payload.current_equity,
            day_start_equity=payload.day_start_equity
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/stages/{stage_id}/pass")
async def pass_stage(stage_id: int):
    try:
        updated_stage = PropService.pass_stage(stage_id)
        return {"message": "استیج با موفقیت پاس شد و حساب به مرحله بعد منتقل گردید.", "stage": updated_stage}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/stages/{stage_id}/fail")
async def fail_stage(stage_id: int, payload: FailStageRequest):
    try:
        failed_stage = PropService.fail_stage(stage_id, reason=payload.reason)
        return {"message": "حساب با موفقیت فیل و بسته شد.", "stage": failed_stage}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/stages/{account_id}/withdraw")
async def request_withdrawal(account_id: int, payload: WithdrawRequest):
    try:
        withdrawal = PropService.process_withdrawal(account_id, payload.amount)
        return {"message": "درخواست برداشت ثبت و اعمال گردید.", "withdrawal": withdrawal}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/analytics")
async def get_prop_desk_analytics():
    return PropService.get_desk_analytics()