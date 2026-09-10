from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import engine, get_db

# ساخت خودکار جداول دیتابیس در صورت عدم وجود
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MokTradeDesk API",
    description="سیستم مدیریت و ژورنال‌نویسی معاملات",
    version="1.0.0"
)

# تنظیمات CORS برای ارتباط با فرانت‌اند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Status"])
def read_root():
    return {
        "status": "online",
        "message": "MokTradeDesk API is running successfully",
        "docs_url": "http://127.0.0.1:8000/docs"
    }

@app.post("/api/trades/", response_model=schemas.TradeResponse, status_code=status.HTTP_201_CREATED, tags=["Trades"])
def create_trade(trade: schemas.TradeCreate, db: Session = Depends(get_db)):
    db_trade = models.Trade(**trade.model_dump())
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

@app.get("/api/trades/", response_model=List[schemas.TradeResponse], tags=["Trades"])
def get_trades(db: Session = Depends(get_db)):
    return db.query(models.Trade).order_by(models.Trade.created_at.desc()).all()

@app.delete("/api/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Trades"])
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    trade_query = db.query(models.Trade).filter(models.Trade.id == trade_id)
    if not trade_query.first():
        raise HTTPException(status_code=404, detail="معامله مورد نظر یافت نشد")
    trade_query.delete(synchronize_session=False)
    db.commit()
    return None
@app.put("/api/trades/{trade_id}/close", response_model=schemas.TradeResponse, tags=["Trades"])
def close_trade(trade_id: int, trade_close: schemas.TradeClose, db: Session = Depends(get_db)):
    db_trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail="معامله یافت نشد")
    
    db_trade.exit_price = trade_close.exit_price
    db_trade.status = "CLOSED"
    db.commit()
    db.refresh(db_trade)
    return db_trade