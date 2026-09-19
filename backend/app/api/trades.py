from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import os
import hashlib

from ..core.database import get_db
from ..models.strategy import Trade, TradeSource, TestType, StrategyVersion, Strategy
from ..models.personal import Screenshot
from ..utils.trade_metrics import calculate_r_multiple
from ..utils.trade_validator import TradeValidator

router = APIRouter()

# مسیر ذخیره‌ی اسکرین‌شات‌ها
SCREENSHOTS_DIR = "storage/screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class TradeUpdate(BaseModel):
    note: Optional[str] = None


class ManualTradeCreate(BaseModel):
    symbol: str
    direction: str
    open_time: str
    close_time: Optional[str] = None
    open_price: float
    close_price: Optional[float] = None
    size: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    pnl: Optional[float] = None
    r_multiple: Optional[float] = None  # اگه خالی بمونه و SL وارد شده باشه، خودکار محاسبه می‌شه
    commission: Optional[float] = 0.0
    swap: Optional[float] = 0.0
    version_id: Optional[int] = None
    personal_account_id: Optional[int] = None
    prop_stage_id: Optional[int] = None
    test_type: str = "backtest"
    note: Optional[str] = None


# ═════════════════════════════════════════════
# List & Filter Trades
# ═════════════════════════════════════════════
@router.get("/")
def get_trades(
    version_id: Optional[int] = None,
    prop_stage_id: Optional[int] = None,
    symbol: Optional[str] = None,
    test_type: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """لیست معاملات با فیلتر"""
    query = db.query(Trade)

    if version_id:
        query = query.filter(Trade.version_id == version_id)
    if prop_stage_id:
        query = query.filter(Trade.prop_stage_id == prop_stage_id)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    if test_type:
        query = query.filter(Trade.test_type == test_type)
    if source:
        query = query.filter(Trade.source == source)
    if search:
        query = query.filter(Trade.note.like(f"%{search}%"))

    total = query.count()
    trades = query.order_by(Trade.close_time.desc()).offset(offset).limit(limit).all()

    result = []
    for t in trades:
        screenshots_count = db.query(Screenshot).filter(
            Screenshot.entity_type == "trade",
            Screenshot.entity_id == t.id,
        ).count()

        version_name = None
        strategy_name = None
        personal_account_name = None
        if t.version_id:
            version = db.query(StrategyVersion).filter(StrategyVersion.id == t.version_id).first()
            if version:
                version_name = version.version_name
                strategy = db.query(Strategy).filter(Strategy.id == version.strategy_id).first()
                strategy_name = strategy.name if strategy else None
        if t.personal_account_id:
            personal_account = db.query(Trade.__table__.metadata.tables['personal_accounts']).filter_by(id=t.personal_account_id).first() if False else None
            # fallback to ORM relationship when available
            personal_account = t.personal_account
            personal_account_name = personal_account.name if personal_account else None

        result.append({
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction,
            "open_time": t.open_time,
            "close_time": t.close_time,
            "open_price": t.open_price,
            "close_price": t.close_price,
            "size": t.size,
            "pnl": t.pnl,
            "commission": t.commission,
            "swap": t.swap,
            "source": t.source.value if t.source else None,
            "test_type": t.test_type.value if t.test_type else None,
            "note": t.note,
            "version_id": t.version_id,
            "version_name": version_name,
            "strategy_name": strategy_name,
            "personal_account_id": t.personal_account_id,
            "personal_account_name": personal_account_name,
            "prop_stage_id": t.prop_stage_id,
            "screenshots_count": screenshots_count,
            "created_at": t.created_at,
        })

    return {"total": total, "trades": result}


# ═════════════════════════════════════════════
# Get Single Trade
# ═════════════════════════════════════════════
@router.get("/{trade_id}")
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """جزئیات یک معامله"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    screenshots = db.query(Screenshot).filter(
        Screenshot.entity_type == "trade",
        Screenshot.entity_id == trade_id,
    ).all()

    personal_account_name = trade.personal_account.name if trade.personal_account else None

    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "direction": trade.direction,
        "open_time": trade.open_time,
        "close_time": trade.close_time,
        "open_price": trade.open_price,
        "close_price": trade.close_price,
        "size": trade.size,
        "sl": trade.sl,
        "tp": trade.tp,
        "pnl": trade.pnl,
        "commission": trade.commission,
        "swap": trade.swap,
        "source": trade.source.value if trade.source else None,
        "test_type": trade.test_type.value if trade.test_type else None,
        "note": trade.note,
        "version_id": trade.version_id,
        "personal_account_id": trade.personal_account_id,
        "personal_account_name": personal_account_name,
        "prop_stage_id": trade.prop_stage_id,
        "raw_data": trade.raw_data,
        "screenshots": [
            {
                "id": s.id,
                "file_path": s.file_path,
                "description": s.description,
                "uploaded_at": s.uploaded_at,
            }
            for s in screenshots
        ],
    }


# ═════════════════════════════════════════════
# Update Trade (only note)
# ═════════════════════════════════════════════
@router.patch("/{trade_id}")
def update_trade(trade_id: int, data: TradeUpdate, db: Session = Depends(get_db)):
    """ویرایش یادداشت معامله"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    if data.note is not None:
        trade.note = data.note

    db.commit()
    return {"message": "معامله به‌روزرسانی شد"}


# ═════════════════════════════════════════════
# Delete Trade (only manual)
# ═════════════════════════════════════════════
@router.delete("/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """حذف معامله (فقط معاملات دستی)"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    if trade.source != TradeSource.MANUAL:
        raise HTTPException(
            status_code=400,
            detail="فقط معاملات دستی قابل حذف هستند"
        )

    screenshots = db.query(Screenshot).filter(
        Screenshot.entity_type == "trade",
        Screenshot.entity_id == trade_id,
    ).all()
    for s in screenshots:
        if os.path.exists(s.file_path):
            try:
                os.remove(s.file_path)
            except:
                pass
        db.delete(s)

    db.delete(trade)
    db.commit()
    return {"message": "معامله حذف شد"}


# ═════════════════════════════════════════════
# Create Manual Trade
# ═════════════════════════════════════════════
@router.post("/manual")
def create_manual_trade(data: ManualTradeCreate, db: Session = Depends(get_db)):
    """افزودن معامله‌ی دستی"""
    try:
        open_time = datetime.fromisoformat(data.open_time)
    except:
        raise HTTPException(status_code=400, detail="فرمت تاریخ نامعتبر")

    close_time = None
    if data.close_time:
        try:
            close_time = datetime.fromisoformat(data.close_time)
        except:
            raise HTTPException(status_code=400, detail="فرمت تاریخ بسته شدن نامعتبر")

    direction = data.direction.lower()
    if direction not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="جهت باید buy یا sell باشد")

    test_type_map = {
        "backtest": TestType.BACKTEST,
        "forward": TestType.FORWARD,
        "real": TestType.REAL,
    }
    test_type = test_type_map.get(data.test_type, TestType.BACKTEST)

    is_valid, error_message = TradeValidator.validate_classification(
        test_type.value if hasattr(test_type, 'value') else str(test_type),
        data.version_id,
        data.personal_account_id,
        data.prop_stage_id,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    r_multiple = data.r_multiple
    if r_multiple is None:
        r_multiple = calculate_r_multiple(direction, data.open_price, data.close_price, data.sl)

    trade = Trade(
        symbol=data.symbol,
        direction=direction,
        open_time=open_time,
        close_time=close_time,
        open_price=data.open_price,
        close_price=data.close_price,
        size=data.size,
        sl=data.sl,
        tp=data.tp,
        pnl=data.pnl,
        r_multiple=r_multiple,
        commission=data.commission or 0,
        swap=data.swap or 0,
        version_id=data.version_id,
        personal_account_id=data.personal_account_id,
        prop_stage_id=data.prop_stage_id,
        source=TradeSource.MANUAL,
        test_type=test_type,
        note=data.note,
        entry_sequence=1,
    )

    db.add(trade)
    db.commit()
    db.refresh(trade)

    return {"id": trade.id, "message": "معامله‌ی دستی ثبت شد"}


# ═════════════════════════════════════════════
# Screenshots
# ═════════════════════════════════════════════
@router.post("/{trade_id}/screenshots")
async def upload_screenshot(
    trade_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """آپلود اسکرین‌شات برای معامله"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    allowed_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="فرمت فایل پشتیبانی نمی‌شود")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"trade_{trade_id}_{timestamp}{ext}"
    file_path = f"storage/screenshots/{file_name}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = hashlib.md5(content).hexdigest()

    screenshot = Screenshot(
    entity_type="trade",
    entity_id=trade_id,
    file_path=file_path,
    file_hash=file_hash,
    description=description,
)
    db.add(screenshot)
    db.commit()
    db.refresh(screenshot)

    return {
        "id": screenshot.id,
        "file_path": screenshot.file_path,
        "message": "اسکرین‌شات آپلود شد",
    }


@router.get("/{trade_id}/screenshots")
def get_screenshots(trade_id: int, db: Session = Depends(get_db)):
    """لیست اسکرین‌شات‌های معامله"""
    screenshots = db.query(Screenshot).filter(
        Screenshot.entity_type == "trade",
        Screenshot.entity_id == trade_id,
    ).all()

    return [
        {
            "id": s.id,
            "file_path": s.file_path,
            "file_name": os.path.basename(s.file_path),
            "description": s.description,
            "uploaded_at": s.uploaded_at,
        }
        for s in screenshots
    ]


@router.delete("/screenshots/{screenshot_id}")
def delete_screenshot(screenshot_id: int, db: Session = Depends(get_db)):
    """حذف اسکرین‌شات"""
    screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
    if not screenshot:
        raise HTTPException(status_code=404, detail="اسکرین‌شات پیدا نشد")

    if os.path.exists(screenshot.file_path):
        try:
            os.remove(screenshot.file_path)
        except:
            pass

    db.delete(screenshot)
    db.commit()
    return {"message": "اسکرین‌شات حذف شد"}