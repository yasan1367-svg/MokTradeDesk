from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None

class StrategyCreate(StrategyBase):
    pass

class StrategyResponse(StrategyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TradeBase(BaseModel):
    symbol: str
    trade_type: str
    entry_price: float
    quantity: float
    stop_loss: Optional[float] = None
    initial_sl: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    commission: Optional[float] = 0.0
    swap: Optional[float] = 0.0
    profit: Optional[float] = None
    pips: Optional[float] = None
    drawdown: Optional[float] = None
    status: Optional[str] = "OPEN"
    notes: Optional[str] = None
    strategy_id: Optional[int] = None

class TradeCreate(TradeBase):
    pass

class TradeClose(BaseModel):
    exit_price: float
    commission: Optional[float] = 0.0
    swap: Optional[float] = 0.0
    profit: Optional[float] = None

class TradeResponse(TradeBase):
    id: int
    open_time: datetime
    close_time: Optional[datetime] = None
    strategy: Optional[StrategyResponse] = None

    class Config:
        from_attributes = True