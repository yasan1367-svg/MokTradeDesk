from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io
import csv

import models
import schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MokTradeDesk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_contract_size(symbol: str) -> float:
    sym = symbol.upper()
    if "XAU" in sym or "GOLD" in sym:
        return 100.0
    elif "DJI" in sym or "US30" in sym or "WS30" in sym:
        return 10.0
    elif "XAG" in sym or "SILVER" in sym:
        return 5000.0
    elif "BTC" in sym or "ETH" in sym:
        return 1.0
    else:
        return 100000.0  # فارکس استاندارد

def calculate_pips(symbol: str, price_diff: float) -> float:
    sym = symbol.upper()
    if "XAU" in sym or "GOLD" in sym or "JPY" in sym:
        return round(price_diff * 100, 1)
    elif "DJI" in sym or "US30" in sym or "WS30" in sym:
        return round(price_diff, 1)
    else:
        return round(price_diff * 10000, 1)

@app.get("/")
def read_root():
    return {"status": "online", "message": "MokTradeDesk API is running"}

# --- Strategy Endpoints ---
@app.post("/api/strategies/", response_model=schemas.StrategyResponse, status_code=status.HTTP_201_CREATED, tags=["Strategies"])
def create_strategy(strategy: schemas.StrategyCreate, db: Session = Depends(get_db)):
    db_strat = db.query(models.Strategy).filter(models.Strategy.name == strategy.name).first()
    if db_strat:
        raise HTTPException(status_code=400, detail="استراتژی با این نام قبلاً ثبت شده است")
    new_strat = models.Strategy(**strategy.model_dump())
    db.add(new_strat)
    db.commit()
    db.refresh(new_strat)
    return new_strat

@app.get("/api/strategies/", response_model=List[schemas.StrategyResponse], tags=["Strategies"])
def get_strategies(db: Session = Depends(get_db)):
    return db.query(models.Strategy).all()

@app.delete("/api/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Strategies"])
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strat = db.query(models.Strategy).filter(models.Strategy.id == strategy_id)
    if not strat.first():
        raise HTTPException(status_code=404, detail="استراتژی یافت نشد")
    strat.delete(synchronize_session=False)
    db.commit()
    return None

# --- Trade Endpoints ---
@app.post("/api/trades/", response_model=schemas.TradeResponse, status_code=status.HTTP_201_CREATED, tags=["Trades"])
def create_trade(trade: schemas.TradeCreate, db: Session = Depends(get_db)):
    trade_data = trade.model_dump()
    if not trade_data.get("initial_sl") and trade_data.get("stop_loss"):
        trade_data["initial_sl"] = trade_data["stop_loss"]
    db_trade = models.Trade(**trade_data)
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

@app.get("/api/trades/", response_model=List[schemas.TradeResponse], tags=["Trades"])
def get_trades(db: Session = Depends(get_db)):
    return db.query(models.Trade).order_by(models.Trade.open_time.desc()).all()

@app.put("/api/trades/{trade_id}/close", response_model=schemas.TradeResponse, tags=["Trades"])
def close_trade(trade_id: int, trade_close: schemas.TradeClose, db: Session = Depends(get_db)):
    db_trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail="معامله یافت نشد")
    
    db_trade.exit_price = trade_close.exit_price
    db_trade.commission = trade_close.commission
    db_trade.swap = trade_close.swap
    db_trade.close_time = datetime.utcnow()
    db_trade.status = "CLOSED"
    
    # محاسبه اختلاف قیمت بر اساس نوع پوزیشن
    price_diff = db_trade.exit_price - db_trade.entry_price if db_trade.trade_type == "BUY" else db_trade.entry_price - db_trade.exit_price
    
    # محاسبه پیپ
    db_trade.pips = calculate_pips(db_trade.symbol, price_diff)

    # محاسبه سود به دلار ($)
    if trade_close.profit is not None:
        db_trade.profit = trade_close.profit
    else:
        contract_size = get_contract_size(db_trade.symbol)
        db_trade.profit = round(price_diff * db_trade.quantity * contract_size, 2)

    db.commit()
    db.refresh(db_trade)
    return db_trade

@app.delete("/api/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Trades"])
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    trade_query = db.query(models.Trade).filter(models.Trade.id == trade_id)
    if not trade_query.first():
        raise HTTPException(status_code=404, detail="معامله یافت نشد")
    trade_query.delete(synchronize_session=False)
    db.commit()
    return None
from fastapi import UploadFile, File
import io
import csv

@app.post("/api/trades/import-csv", tags=["Trades"])
async def import_trades_csv(file: UploadFile = File(...), strategy_id: Optional[int] = None, db: Session = Depends(get_db)):
    content = await file.read()
    decoded_content = content.decode('utf-8-sig', errors='ignore')
    
    # تشخیص جداکننده (Tab یا Comma)
    dialect = csv.Sniffer().sniff(decoded_content[:2000]) if len(decoded_content) > 10 else csv.excel
    reader = csv.DictReader(io.StringIO(decoded_content), dialect=dialect)
    
    imported_count = 0
    
    for row in reader:
        # استانداردسازی نام کلیدها (حذف فواصل اضافه)
        clean_row = {k.strip(): v.strip() if v else '' for k, v in row.items() if k}
        
        symbol = clean_row.get('Symbol') or clean_row.get('Item') or clean_row.get('symbol', 'XAUUSD')
        trade_type = clean_row.get('Type') or clean_row.get('type', 'BUY')
        
        # فقط خطوط مربوط به معامله (BUY / SELL) پردازش شوند
        if trade_type.upper() not in ['BUY', 'SELL']:
            continue
            
        try:
            quantity = float(clean_row.get('Volume') or clean_row.get('Size') or 0.01)
            entry_price = float(clean_row.get('Price') or clean_row.get('Open Price') or 0.0)
            exit_price = float(clean_row.get('Price.1') or clean_row.get('Close Price') or entry_price)
            
            sl = float(clean_row.get('S / L') or clean_row.get('SL') or 0.0) if clean_row.get('S / L') or clean_row.get('SL') else None
            tp = float(clean_row.get('T / P') or clean_row.get('TP') or 0.0) if clean_row.get('T / P') or clean_row.get('TP') else None
            
            commission = float(clean_row.get('Commission') or 0.0)
            swap = float(clean_row.get('Swap') or 0.0)
            profit = float(clean_row.get('Profit') or clean_row.get('P/L') or 0.0)
            
            price_diff = exit_price - entry_price if trade_type.upper() == 'BUY' else entry_price - exit_price
            pips = calculate_pips(symbol, price_diff)

            new_trade = models.Trade(
                symbol=symbol.upper(),
                trade_type=trade_type.upper(),
                quantity=quantity,
                entry_price=entry_price,
                exit_price=exit_price,
                stop_loss=sl,
                take_profit=tp,
                commission=commission,
                swap=swap,
                profit=profit,
                pips=pips,
                status="CLOSED",
                strategy_id=strategy_id
            )
            db.add(new_trade)
            imported_count += 1
        except Exception as e:
            continue
            
    db.commit()
    return {"status": "success", "imported_trades": imported_count}