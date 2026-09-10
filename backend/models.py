from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trades = relationship("Trade", back_populates="strategy")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    trade_type = Column(String)  # BUY or SELL
    quantity = Column(Float)     # Volume / Lot
    
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    
    stop_loss = Column(Float, nullable=True)
    initial_sl = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    profit = Column(Float, nullable=True)       # سود/زیان
    pips = Column(Float, nullable=True)         # مقدار پیپ
    drawdown = Column(Float, nullable=True)     # حداکثر دراوداون

    status = Column(String, default="OPEN")     # OPEN or CLOSED
    notes = Column(String, nullable=True)
    
    open_time = Column(DateTime, default=datetime.utcnow)
    close_time = Column(DateTime, nullable=True)

    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    strategy = relationship("Strategy", back_populates="trades")