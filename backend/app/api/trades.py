from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import os
import hashlib

from ..core.database import get_db
from ..models.strategy import Trade, TradeSource, TestType, StrategyVersion
from ..models.personal import Screenshot
from ..models.prop import PropAccount, PropStage
from ..models.trading import PersonalTradingAccount
from ..models.finance import Currency
from ..utils.trade_metrics import calculate_r_multiple
from ..utils.trade_validator import TradeReferenceNotFound, TradeValidator
from ..utils.uploads import read_upload_limited
from ..utils.time_utils import to_utc
from ..utils.date_range import filter_by_range

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
    personal_trading_account_id: Optional[int] = None
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


def _parse_test_type(value: str) -> TestType:
    try:
        return TestType(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="نوع تست نامعتبر") from exc


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
    personal_trading_account_id: Optional[int] = None
    prop_stage_id: Optional[int] = None

    note: Optional[str] = None


class BatchDeleteRequest(BaseModel):
    """حذف گروهی معاملات (فاز ۲۵)

    - trade_ids: لیست شناسه‌های معاملات
    - hard: در حالت پیش‌فرض (False) حذف نرم است؛ اگر True باشد حذف کامل (فقط ادمین).
    """
    trade_ids: List[int]
    hard: bool = False


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def _parse_iso_datetime(
    value: Optional[str], field_name: str = "تاریخ", offset_minutes: int = 0
) -> Optional[datetime]:
    """تبدیل رشته‌ی ISO به datetime آگاه از UTC.

    فاز ۴۶.۲: اگر رشته بدون tz باشد، به‌عنوان **ساعت سرور** با `offset_minutes`
    تفسیر و به UTC تبدیل می‌شود (پیش‌تر بی‌قید UTC فرض می‌شد).
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        return to_utc(dt, offset_minutes)
    except Exception:
        raise HTTPException(status_code=400, detail=f"فرمت {field_name} نامعتبر است")


def _validate_trade_references(
    db: Session, version_id, personal_account_id, prop_stage_id
) -> None:
    try:
        TradeValidator.validate_fk(db, version_id, personal_account_id, prop_stage_id)
    except TradeReferenceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _commit_trade(db: Session) -> None:
    """Map persistence errors to stable API responses and leave the session usable."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Trade conflicts with existing data") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _resolve_trade_server_offset(
    db: Session, prop_stage_id: Optional[int], personal_trading_account_id: Optional[int]
) -> int:
    """فاز ۴۶.۲ — اختلاف ساعت سرور مقصد با UTC (دقیقه) برای ثبت دستی."""
    if prop_stage_id:
        stage = db.query(PropStage).filter(PropStage.id == prop_stage_id).first()
        account = stage.account if stage else None
        if account is not None:
            return int(account.server_utc_offset_minutes or 0)
    if personal_trading_account_id:
        acc = (
            db.query(PersonalTradingAccount)
            .filter(PersonalTradingAccount.id == personal_trading_account_id)
            .first()
        )
        broker = acc.broker if acc else None
        if broker is not None:
            return int(broker.server_utc_offset_minutes or 0)
    return 0


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

    pta = t.personal_trading_account
    personal_trading_account_name = None
    if pta:
        personal_trading_account_name = pta.account_label or pta.account_number

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
        "personal_trading_account_id": t.personal_trading_account_id,
        "personal_trading_account_name": personal_trading_account_name,
        "prop_stage_id": t.prop_stage_id,
        "screenshots_count": screenshots_count,
        "created_at": t.created_at,
    }


def _serialize_trade_detail(t: Trade, screenshots: List[Screenshot]) -> dict:
    """خروجی کامل یک معامله"""
    pta = t.personal_trading_account
    personal_trading_account_name = None
    if pta:
        personal_trading_account_name = pta.account_label or pta.account_number

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
        "personal_trading_account_id": t.personal_trading_account_id,
        "personal_trading_account_name": personal_trading_account_name,
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
    personal_trading_account_id: Optional[int] = None,
    prop_stage_id: Optional[int] = None,
    symbol: Optional[str] = None,
    test_type: Optional[str] = None,
    currency: Optional[Currency] = None,
    source: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
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

    # فاز ۲۵: معاملات حذف‌شده (Soft Delete) در لیست نمایش داده نمی‌شوند
    query = query.filter(Trade.is_deleted == False)

    if currency is not None:
        query = (
            query.outerjoin(PersonalTradingAccount, Trade.personal_trading_account_id == PersonalTradingAccount.id)
            .outerjoin(PropStage, Trade.prop_stage_id == PropStage.id)
            .outerjoin(PropAccount, PropStage.prop_account_id == PropAccount.id)
            .filter(or_(
                and_(Trade.test_type == TestType.REAL_PERSONAL, PersonalTradingAccount.currency == currency),
                and_(Trade.test_type == TestType.REAL_PROP, PropAccount.currency == currency),
                and_(Trade.test_type.in_([TestType.BACKTEST, TestType.FORWARD]), currency == Currency.USDT),
            ))
        )

    if version_id:
        query = query.filter(Trade.version_id == version_id)
    if strategy_id:
        query = query.join(StrategyVersion, Trade.version_id == StrategyVersion.id).filter(
            StrategyVersion.strategy_id == strategy_id
        )
    if personal_trading_account_id:
        query = query.filter(Trade.personal_trading_account_id == personal_trading_account_id)
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
    if status == "open":
        query = query.filter(Trade.close_time == None)
    elif status == "closed":
        query = query.filter(Trade.close_time != None)
    if search:
        query = query.filter(Trade.note.like(f"%{search}%"))
    # فاز ۴۶.۵: date_to شامل آخرین روز است (نیمه‌باز تا نیمه‌شب روز بعد)
    query = filter_by_range(query, Trade.open_time, date_from, date_to)
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
            joinedload(Trade.personal_trading_account),
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
            joinedload(Trade.personal_trading_account),
        )
        .filter(Trade.id == trade_id, Trade.is_deleted == False)
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
    # فاز ۲۵: معامله‌ی حذف‌شده قابل ویرایش نیست
    trade = db.query(Trade).filter(
        Trade.id == trade_id, Trade.is_deleted == False
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    payload = data.model_dump(exclude_unset=True)
    for required_field in ("test_type", "version_id", "symbol", "direction", "open_time", "open_price", "size"):
        if required_field in payload and payload[required_field] is None:
            raise HTTPException(status_code=400, detail=f"{required_field} cannot be null")

    # Explicit null is the API's instruction to clear nullable values. A target
    # unrelated to a newly selected trade type is cleared automatically.
    new_test_type = payload.get("test_type", trade.test_type.value if trade.test_type else "backtest")
    if new_test_type is None:
        new_test_type = trade.test_type.value if trade.test_type else "backtest"
    new_version_id = payload.get("version_id", trade.version_id)
    new_personal_trading_account_id = payload.get(
        "personal_trading_account_id", trade.personal_trading_account_id
    )
    new_prop_stage_id = payload.get("prop_stage_id", trade.prop_stage_id)
    previous_test_type = trade.test_type.value if trade.test_type else "backtest"
    if new_test_type != previous_test_type:
        if new_test_type in ("backtest", "forward"):
            if "personal_trading_account_id" not in payload:
                new_personal_trading_account_id = None
            if "prop_stage_id" not in payload:
                new_prop_stage_id = None
        elif new_test_type == "real_personal" and "prop_stage_id" not in payload:
            new_prop_stage_id = None
        elif new_test_type == "real_prop" and "personal_trading_account_id" not in payload:
            new_personal_trading_account_id = None

    # ── ۲. validation Classification ──
    is_valid, error_message = TradeValidator.validate_classification(
        new_test_type,
        new_version_id,
        new_personal_trading_account_id,
        new_prop_stage_id,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    _validate_trade_references(
        db, new_version_id, new_personal_trading_account_id, new_prop_stage_id
    )

    # ── ۳. validation اعداد (اگه تغییر کردن) ──
    is_valid, error_message = TradeValidator.validate_numbers(
        size=payload.get("size", trade.size),
        open_price=payload.get("open_price", trade.open_price),
        close_price=payload.get("close_price", trade.close_price),
        sl=payload.get("sl", trade.sl),
        tp=payload.get("tp", trade.tp),
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # ── ۴. validation تاریخ‌ها ──
    new_open_time = trade.open_time
    new_close_time = trade.close_time
    if "open_time" in payload:
        new_open_time = _parse_iso_datetime(payload["open_time"], "زمان باز شدن")
    if "close_time" in payload:
        new_close_time = _parse_iso_datetime(payload["close_time"], "زمان بسته شدن")

    is_valid, error_message = TradeValidator.validate_dates(new_open_time, new_close_time)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    if "direction" in payload and (
        payload["direction"] is None or payload["direction"].lower() not in ("buy", "sell")
    ):
        raise HTTPException(status_code=400, detail="جهت باید buy یا sell باشد")

    # ── ۵. اعمال فقط فیلدهای ارسال‌شده (null صریح برای nullable معتبر است) ──
    if "test_type" in payload:
        trade.test_type = _parse_test_type(new_test_type)
    trade.version_id = new_version_id
    trade.personal_trading_account_id = new_personal_trading_account_id
    trade.prop_stage_id = new_prop_stage_id

    for field in (
        "note", "symbol", "open_price", "close_price", "size", "sl", "tp",
        "pnl", "commission", "swap",
    ):
        if field in payload:
            setattr(trade, field, payload[field])
    if "direction" in payload:
        trade.direction = payload["direction"].lower()
    if "open_time" in payload:
        trade.open_time = new_open_time
    if "close_time" in payload:
        trade.close_time = new_close_time

    # ✅ محاسبه‌ی مجدد R-Multiple اگه SL/قیمت‌ها تغییر کرده
    if any(field in payload for field in ("sl", "open_price", "close_price", "direction")):
        trade.r_multiple = calculate_r_multiple(
            trade.direction,
            trade.open_price,
            trade.close_price,
            trade.sl,
        )

    # فاز ۴۰.۵: تغییرات باید persist شوند.
    # پیش‌تر `db.commit()` گم شده بود و `db.refresh()` زیر، تغییرات commit‌نشده را
    # دور می‌ریخت ⇒ PATCH هیچ‌وقت ذخیره نمی‌شد (باگ کشف‌شده در رگرسیون فاز ۴۰).
    _commit_trade(db)
    db.refresh(trade)

    # فاز ۲۸: پل خودکار معامله→حسابداری حذف شد (فقط حساب معاملاتی).
    if trade.close_time is not None and trade.personal_trading_account_id:
        from ..services.finance_sync_service import FinanceSyncService
        FinanceSyncService(db).sync_closed_trades(trade_ids=[trade.id])

    return {"message": "معامله به‌روزرسانی شد"}


# ═════════════════════════════════════════════
# Delete Trade (soft delete — Phase 25)
# ═════════════════════════════════════════════
def _hard_delete_trade(db: Session, trade: Trade) -> None:
    """حذف کامل معامله + اسکرین‌شات‌ها (فقط برای ادمین).

    این تابع فایل‌های فیزیکی اسکرین‌شات را هم پاک می‌کند و بازگشت‌پذیر نیست.
    """
    screenshots = db.query(Screenshot).filter(
        Screenshot.entity_type == "trade",
        Screenshot.entity_id == trade.id,
    ).all()
    for s in screenshots:
        if s.file_path and os.path.exists(s.file_path):
            try:
                os.remove(s.file_path)
            except Exception:
                pass
        db.delete(s)

    db.delete(trade)


@router.delete("/{trade_id}")
def delete_trade(
    trade_id: int,
    hard: bool = False,
    db: Session = Depends(get_db),
):
    """حذف معامله (همه‌ی منابع) — پیش‌فرض: Soft Delete.

    فاز ۲۵:
    - محدودیت `source == manual` برداشته شد؛ همه‌ی معاملات قابل حذف‌اند.
    - پیش‌فرض حذف نرم است (`is_deleted = True`) و داده حفظ می‌شود.
    - با `?hard=true` حذف کامل (بازگشت‌ناپذیر) انجام می‌شود — فقط ادمین.
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    if hard:
        _hard_delete_trade(db, trade)
        db.commit()
        return {"message": "معامله برای همیشه حذف شد", "hard": True, "count": 1}

    # ── Soft Delete ──
    if trade.is_deleted:
        # قبلاً حذف شده؛ پاسخ idempotent
        return {"message": "این معامله قبلاً حذف شده بود", "hard": False, "count": 0}

    trade.is_deleted = True
    db.commit()
    return {"message": "معامله حذف شد", "hard": False, "count": 1}


# ═════════════════════════════════════════════
# Batch Delete Trades (Phase 25)
# ═════════════════════════════════════════════
@router.post("/batch-delete")
def batch_delete_trades(data: BatchDeleteRequest, db: Session = Depends(get_db)):
    """حذف گروهی معاملات — پیش‌فرض: Soft Delete.

    - همه‌ی `trade_ids` بدون توجه به `source` قابل حذف‌اند.
    - با `hard=true` حذف کامل انجام می‌شود (بازگشت‌ناپذیر).
    - شناسه‌های ناموجود یا قبلاً حذف‌شده در پاسخ با `skipped` گزارش می‌شوند.
    """
    if not data.trade_ids:
        raise HTTPException(status_code=400, detail="لیست معاملات خالی است")

    # حفظ ترتیب و حذف تکراری‌ها
    unique_ids = list(dict.fromkeys(data.trade_ids))

    trades = (
        db.query(Trade)
        .filter(Trade.id.in_(unique_ids))
        .all()
    )
    found_ids = {t.id for t in trades}
    skipped = [tid for tid in unique_ids if tid not in found_ids]

    deleted_count = 0
    for trade in trades:
        if data.hard:
            _hard_delete_trade(db, trade)
            deleted_count += 1
        else:
            if trade.is_deleted:
                skipped.append(trade.id)
            else:
                trade.is_deleted = True
                deleted_count += 1

    db.commit()
    return {
        "message": f"{deleted_count} معامله حذف شد",
        "deleted": deleted_count,
        "skipped": skipped,
        "hard": data.hard,
    }


# ═════════════════════════════════════════════
# Create Manual Trade
# ═════════════════════════════════════════════
@router.post("/manual")
def create_manual_trade(data: ManualTradeCreate, db: Session = Depends(get_db)):
    """افزودن معامله‌ی دستی"""
    # فاز ۴۶.۲: زمان‌های بدون tz بر اساس ساعت سرور مقصد تفسیر می‌شوند
    offset = _resolve_trade_server_offset(
        db, data.prop_stage_id, data.personal_trading_account_id
    )
    open_time = _parse_iso_datetime(data.open_time, "زمان باز شدن", offset)
    if not open_time:
        raise HTTPException(status_code=400, detail="زمان باز شدن الزامی است")

    close_time = _parse_iso_datetime(data.close_time, "زمان بسته شدن", offset)

    direction = data.direction.lower()
    if direction not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="جهت باید buy یا sell باشد")

    test_type = _parse_test_type(data.test_type)

    _validate_trade_references(
        db, data.version_id, data.personal_trading_account_id, data.prop_stage_id
    )

    # ✅ Validation Classification
    is_valid, error_message = TradeValidator.validate_classification(
        test_type.value,
        data.version_id,
        data.personal_trading_account_id,
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
        personal_trading_account_id=data.personal_trading_account_id,
        prop_stage_id=data.prop_stage_id,
        source=TradeSource.MANUAL,
        test_type=test_type,
        note=data.note,
        entry_sequence=1,
    )

    db.add(trade)
    _commit_trade(db)
    db.refresh(trade)

    # فاز ۲۸: پل خودکار معامله→حسابداری حذف شد (فقط حساب معاملاتی).
    if trade.close_time is not None and trade.personal_trading_account_id:
        from ..services.finance_sync_service import FinanceSyncService
        FinanceSyncService(db).sync_closed_trades(trade_ids=[trade.id])

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
    # فاز ۲۵: برای معامله‌ی حذف‌شده نمی‌توان اسکرین‌شات آپلود کرد
    trade = db.query(Trade).filter(
        Trade.id == trade_id, Trade.is_deleted == False
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    allowed_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="فرمت فایل پشتیبانی نمی‌شود")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"trade_{trade_id}_{timestamp}{ext}"
    file_path = f"storage/screenshots/{file_name}"

    content = await read_upload_limited(file)
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
