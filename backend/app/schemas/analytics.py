from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ═════════════════════════════════════════════
# CustomTimeInterval
# ═════════════════════════════════════════════
class CustomTimeIntervalCreate(BaseModel):
    name: str
    symbol: str
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    label: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    is_active: int = 1


class CustomTimeIntervalResponse(BaseModel):
    id: int
    name: str
    symbol: str
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    label: Optional[str]
    priority: Optional[int]
    description: Optional[str]
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════
# TimePoint
# ═════════════════════════════════════════════
class TimePointCreate(BaseModel):
    symbol: str
    hour: int
    minute: int
    label: Optional[str] = None
    is_active: int = 1


class TimePointResponse(BaseModel):
    id: int
    symbol: str
    hour: int
    minute: int
    label: Optional[str]
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════
# Comparison (فاز 48a — قرارداد جدید)
# ═════════════════════════════════════════════
class CompareRequest(BaseModel):
    version_ids: List[int] = Field(..., min_length=2, max_length=10)
    test_type: str = "BACKTEST"
    symbol: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None