from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PropFirmCreate(BaseModel):
    name: str
    default_profit_share: Optional[float] = 80.0
    website: Optional[str] = None
    notes: Optional[str] = None

class PropFirmResponse(BaseModel):
    id: int
    name: str
    default_profit_share: float
    website: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True