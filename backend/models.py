from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    trade_type = Column(String)  # BUY or SELL
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    quantity = Column(Float)
    status = Column(String, default="OPEN")  # OPEN or CLOSED
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)