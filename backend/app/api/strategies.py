from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


class StrategyVersionCreate(BaseModel):
    strategy_id: int
    version_name: str
    description: Optional[str] = None


@router.get("/")
async def list_strategies():
    """
    لیست استراتژی‌های ثبت‌شده در آزمایشگاه
    """
    return [
        {"id": 1, "name": "Gold ORB Strategy", "versions": [101, 102]},
        {"id": 2, "name": "US30 Scalper Pro", "versions": [201]}
    ]


@router.post("/versions")
async def create_strategy_version(payload: StrategyVersionCreate):
    """
    ایجاد نسخه جدید برای یک استراتژی جهت شروع ارزیابی analytics
    """
    return {
        "status": "success",
        "version_id": 301,
        "strategy_id": payload.strategy_id,
        "version_name": payload.version_name
    }