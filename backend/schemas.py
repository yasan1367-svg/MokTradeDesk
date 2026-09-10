from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TradeBase(BaseModel):
    symbol: str
    trade_type: str
    entry_price: float
    quantity: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    status: Optional[str] = "OPEN"
    notes: Optional[str] = None

class TradeCreate(TradeBase):
    pass

class TradeResponse(TradeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        class TradeClose(BaseModel):
    exit_price: float