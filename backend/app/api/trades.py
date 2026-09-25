from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import os
import hashlib

from ..core.database import get_db
from ..models.strategy import Trade, TradeSource, TestType, StrategyVersion, Strategy
from ..models.personal import Screenshot
from ..models.prop import PropStage
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
    """ویرایش کنترل‌شده‌ی معامله (Classification + اطلاعات اصلی + note)"""
    note: Optional[str] = None

    # Classification
    test_type: Optional[str] = None
    version_id: Optional[int] = None
    finance_account_id: Optional[int] = None
    prop_stage_id: Optional[int] = None

    # Execution
    symbol: Optional[str] = None
    direction: Optional[str] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    size: Optional[float] = None

    # Risk
    sl: Optional[float] = None
    tp: Optional[float] = None

    # Financial
    pnl: Optional[float] = None
    commission: Optional[float] = None
    swap: Optional[float] = None


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

    # Classification
    test_type: str = "backtest"
    version_id: Optional[int] = None
    finance_account_id: Optional[int] = None
    prop_stage_id: Optional[int] = None

    note: Optional[str] = None


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def _parse_iso_datetime(value: Optional[str], field_name: str = "تاریخ") -> Optional[datetime]:
    """تبدیل رشته‌ی ISO به datetime با timezone-aware (UTC اگه بدون tz بود)"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        # اگه naive بود، UTC فرض کن
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        raise HTTPException(status_code=400, detail=f"فرمت {field_name} نامعتبر است")


def _get_screenshots_count_map(db: Session, trade_ids: List[int]) -> dict:
    """تعداد اسکرین‌شات هر trade رو در یه query جمع می‌کنه (حل N+1)"""
    if not trade_ids:
        return {}
    rows = (
        db.query(Screenshot.entity_id, func.count(Screenshot.id))
        .filter(
            Screenshot.entity_type == "trade",
            Screenshot.entity_id.in_(trade_ids),
        )
        .group_by(Screenshot.entity_id)
        .all()
    )
    return {entity_id: count for entity_id, count in rows}


def _serialize_trade_summary(t: Trade, screenshots_count: int) -> dict:
    """خروجی خلاصه برای لیست"""
    version_name = None
    strategy_name = None
    if t.version:
        version_name = t.version.version_name
        if t.version.strategy:
            strategy_name = t.version.strategy.name

    finance_account_name = t.finance_account.name if t.finance_account else None

    return {
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
        "finance_account_id": t.finance_account_id,
        "finance_account_name": finance_account_name,
        "prop_stage_id": t.prop_stage_id,
        "screenshots_count": screenshots_count,
        "created_at": t.created_at,
    }


def _serialize_trade_detail(t: Trade, screenshots: List[Screenshot]) -> dict:
    """خروجی کامل یک معامله"""
    finance_account_name = t.finance_account.name if t.finance_account else None

    return {
        "id": t.id,
        "symbol": t.symbol,
        "direction": t.direction,
        "open_time": t.open_time,
        "close_time": t.close_time,
        "open_price": t.open_price,
        "close_price": t.close_price,
        "size": t.size,
        "sl": t.sl,
        "tp": t.tp,
        "pnl": t.pnl,
        "commission": t.commission,
        "swap": t.swap,
        "r_multiple": t.r_multiple,
        "source": t.source.value if t.source else None,
        "test_type": t.test_type.value if t.test_type else None,
        "note": t.note,
        "version_id": t.version_id,
        "finance_account_id": t.finance_account_id,
        "finance_account_name": finance_account_name,
        "prop_stage_id": t.prop_stage_id,
        "raw_data": t.raw_data,
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
# List & Filter Trades
# ═════════════════════════════════════════════
@router.get("/")
def get_trades(
    version_id: Optional[int] = None,
    strategy_id: Optional[int] = None,
    finance_account_id: Optional[int] = None,
    prop_stage_id: Optional[int] = None,
    symbol: Optional[str] = None,
    test_type: Optional[str] = None,
    source: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    pnl_min: Optional[float] = None,
    pnl_max: Optional[float] = None,
    page: int = 1,
    page_size: int = 50,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    sort_by: str = "close_time",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    """لیست معاملات با فیلترهای پیشرفته و صفحه‌بندی"""
    query = db.query(Trade)

    if version_id:
        query = query.filter(Trade.version_id == version_id)
    if strategy_id:
        query = query.join(StrategyVersion, Trade.version_id == StrategyVersion.id).filter(
            StrategyVersion.strategy_id == strategy_id
        )
    if finance_account_id:
        query = query.filter(Trade.finance_account_id == finance_account_id)
    if prop_stage_id:
        query = query.filter(Trade.prop_stage_id == prop_stage_id)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    if test_type:
        query = query.filter(Trade.test_type == test_type)
    if source:
        query = query.filter(Trade.source == source)
    if direction:
        query = query.filter(Trade.direction == direction)
    if search:
        query = query.filter(Trade.note.like(f"%{search}%"))
    if date_from:
        dt_from = _parse_iso_datetime(date_from, "تاریخ شروع")
        if dt_from:
            query = query.filter(Trade.open_time >= dt_from)
    if date_to:
        dt_to = _parse_iso_datetime(date_to, "تاریخ پایان")
        if dt_to:
            query = query.filter(Trade.open_time <= dt_to)
    if pnl_min is not None:
        query = query.filter(Trade.pnl >= pnl_min)
    if pnl_max is not None:
        query = query.filter(Trade.pnl <= pnl_max)

    total = query.count()

    # ── صفحه‌بندی: backward compatibility با limit/offset ──
    if limit is not None:
        # حالت قدیمی: limit/offset مستقیم
        effective_limit = limit
        effective_offset = offset or 0
        resp_page = 1
        resp_page_size = limit
    else:
        # حالت جدید: page/page_size
        resp_page = max(page, 1)
        resp_page_size = min(max(page_size, 1), 200)  # حداکثر ۲۰۰ تا در هر صفحه
        effective_offset = (resp_page - 1) * resp_page_size
        effective_limit = resp_page_size

    total_pages = max((total + resp_page_size - 1) // resp_page_size, 1) if limit is None else 1

    # ── مرتب‌سازی ──
    sort_column = getattr(Trade, sort_by, Trade.close_time)
    if sort_order == "asc":
        order = sort_column.asc()
    else:
        order = sort_column.desc().nullslast()

    # ✅ حل N+1: eager load روابط
    trades = (
        query
        .options(
            joinedload(Trade.version).joinedload(StrategyVersion.strategy),
            joinedload(Trade.finance_account),
        )
        .order_by(order)
        .offset(effective_offset)
        .limit(effective_limit)
        .all()
    )

    # ✅ حل N+1: یه query برای همه‌ی screenshots_count ها
    trade_ids = [t.id for t in trades]
    screenshots_count_map = _get_screenshots_count_map(db, trade_ids)

    result = [
        _serialize_trade_summary(t, screenshots_count_map.get(t.id, 0))
        for t in trades
    ]

    return {
        "total": total,
        "page": resp_page,
        "page_size": resp_page_size,
        "total_pages": total_pages,
        "trades": result,
    }


# ═════════════════════════════════════════════
# Get Single Trade
# ═════════════════════════════════════════════
@router.get("/{trade_id}")
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """جزئیات یک معامله"""
    trade = (
        db.query(Trade)
        .options(
            joinedload(Trade.version).joinedload(StrategyVersion.strategy),
            joinedload(Trade.finance_account),
        )
        .filter(Trade.id == trade_id)
        .first()
    )
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    screenshots = db.query(Screenshot).filter(
        Screenshot.entity_type == "trade",
        Screenshot.entity_id == trade_id,
    ).all()

    return _serialize_trade_detail(trade, screenshots)


# ═════════════════════════════════════════════
# Update Trade (controlled edit)
# ═════════════════════════════════════════════
@router.patch("/{trade_id}")
def update_trade(trade_id: int, data: TradeUpdate, db: Session = Depends(get_db)):
    """ویرایش کنترل‌شده‌ی معامله (Classification + Execution + note)"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    # ── ۱. تعیین مقادیر نهایی برای validation ──
    new_test_type = data.test_type if data.test_type is not None else (
        trade.test_type.value if trade.test_type else "backtest"
    )
    new_version_id = data.version_id if data.version_id is not None else trade.version_id
    new_finance_account_id = (
        data.finance_account_id if data.finance_account_id is not None else trade.finance_account_id
    )
    new_prop_stage_id = (
        data.prop_stage_id if data.prop_stage_id is not None else trade.prop_stage_id
    )

    # ── ۲. validation Classification ──
    is_valid, error_message = TradeValidator.validate_classification(
        new_test_type,
        new_version_id,
        new_finance_account_id,
        new_prop_stage_id,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # ── ۳. validation اعداد (اگه تغییر کردن) ──
    is_valid, error_message = TradeValidator.validate_numbers(
        size=data.size if data.size is not None else trade.size,
        open_price=data.open_price if data.open_price is not None else trade.open_price,
        close_price=data.close_price if data.close_price is not None else trade.close_price,
        sl=data.sl if data.sl is not None else trade.sl,
        tp=data.tp if data.tp is not None else trade.tp,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # ── ۴. validation تاریخ‌ها ──
    new_open_time = trade.open_time
    new_close_time = trade.close_time
    if data.open_time is not None:
        new_open_time = _parse_iso_datetime(data.open_time, "زمان باز شدن")
    if data.close_time is not None:
        new_close_time = _parse_iso_datetime(data.close_time, "زمان بسته شدن")

    is_valid, error_message = TradeValidator.validate_dates(new_open_time, new_close_time)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # ── ۵. اعمال تغییرات ──
    if data.note is not None:
        trade.note = data.note

    # Classification
    if data.test_type is not None:
        test_type_map = {
            "backtest": TestType.BACKTEST,
            "forward": TestType.FORWARD,
            "real": TestType.REAL,
        }
        new_tt = test_type_map.get(data.test_type)
        if not new_tt:
            raise HTTPException(status_code=400, detail="نوع تست نامعتبر")
        trade.test_type = new_tt
    if data.version_id is not None:
        trade.version_id = data.version_id
    if data.finance_account_id is not None:
        trade.finance_account_id = data.finance_account_id or None
    if data.prop_stage_id is not None:
        trade.prop_stage_id = data.prop_stage_id or None

    # Execution
    if data.symbol is not None:
        trade.symbol = data.symbol
    if data.direction is not None:
        direction = data.direction.lower()
        if direction not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="جهت باید buy یا sell باشد")
        trade.direction = direction
    if data.open_time is not None:
        trade.open_time = new_open_time
    if data.close_time is not None:
        trade.close_time = new_close_time
    if data.open_price is not None:
        trade.open_price = data.open_price
    if data.close_price is not None:
        trade.close_price = data.close_price
    if data.size is not None:
        trade.size = data.size

    # Risk
    if data.sl is not None:
        trade.sl = data.sl
    if data.tp is not None:
        trade.tp = data.tp

    # Financial
    if data.pnl is not None:
        trade.pnl = data.pnl
    if data.commission is not None:
        trade.commission = data.commission
    if data.swap is not None:
        trade.swap = data.swap

    # ✅ محاسبه‌ی مجدد R-Multiple اگه SL/قیمت‌ها تغییر کرده
    if any(x is not None for x in [data.sl, data.open_price, data.close_price, data.direction]):
        trade.r_multiple = calculate_r_multiple(
            trade.direction,
            trade.open_price,
            trade.close_price,
            trade.sl,
        )

    db.commit()
    db.refresh(trade)
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
            except Exception:
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
    open_time = _parse_iso_datetime(data.open_time, "زمان باز شدن")
    if not open_time:
        raise HTTPException(status_code=400, detail="زمان باز شدن الزامی است")

    close_time = _parse_iso_datetime(data.close_time, "زمان بسته شدن")

    direction = data.direction.lower()
    if direction not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="جهت باید buy یا sell باشد")

    test_type_map = {
        "backtest": TestType.BACKTEST,
        "forward": TestType.FORWARD,
        "real": TestType.REAL,
    }
    test_type = test_type_map.get(data.test_type)
    if not test_type:
        raise HTTPException(status_code=400, detail="نوع تست نامعتبر")

    # ✅ Validation Classification
    is_valid, error_message = TradeValidator.validate_classification(
        test_type.value,
        data.version_id,
        data.finance_account_id,
        data.prop_stage_id,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # ✅ Validation اعداد
    is_valid, error_message = TradeValidator.validate_numbers(
        size=data.size,
        open_price=data.open_price,
        close_price=data.close_price,
        sl=data.sl,
        tp=data.tp,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # ✅ Validation تاریخ‌ها
    is_valid, error_message = TradeValidator.validate_dates(open_time, close_time)
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
        finance_account_id=data.finance_account_id,
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
        except Exception:
            pass

    db.delete(screenshot)
    db.commit()
    return {"message": "اسکرین‌شات حذف شد"}