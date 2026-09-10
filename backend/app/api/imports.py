from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.import_service import ImportService
from app.models.strategy import StrategyVersion
from app.models.prop import PropStage
from app.models.personal import PersonalAccount

router = APIRouter(prefix="/imports", tags=["Data Imports"])


# --- Pydantic Schemas ---

class ImportSummaryResponse(BaseModel):
    imported: int
    skipped: int
    failed: int
    errors: List[str]


class ManualTradeCreate(BaseModel):
    version_id: int
    prop_stage_id: Optional[int] = None
    personal_account_id: Optional[int] = None
    symbol: str = Field(..., example="EURUSD")
    direction: str = Field(..., example="buy")
    open_time: datetime
    close_time: Optional[datetime] = None
    open_price: float
    close_price: Optional[float] = None
    size: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    pnl: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0
    entry_sequence: Optional[int] = None
    note: Optional[str] = None
    news_event: Optional[str] = None


class ManualTradeResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    open_time: datetime
    open_price: float
    size: float
    pnl: Optional[float]
    r_multiple: Optional[float]
    trade_hash: str
    message: str


class RollbackResponse(BaseModel):
    source: str
    deleted_count: int
    message: str


# --- Helper Validation ---

def validate_references(
    db: Session,
    version_id: int,
    prop_stage_id: Optional[int] = None,
    personal_account_id: Optional[int] = None
):
    version = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"نسخه استراتژی با شناسه {version_id} یافت نشد."
        )

    if prop_stage_id:
        stage = db.query(PropStage).filter(PropStage.id == prop_stage_id).first()
        if not stage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"مرحله پراپ با شناسه {prop_stage_id} یافت نشد."
            )

    if personal_account_id:
        account = db.query(PersonalAccount).filter(PersonalAccount.id == personal_account_id).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"حساب شخصی با شناسه {personal_account_id} یافت نشد."
            )


# --- Endpoints ---

@router.post("/soft4x", response_model=ImportSummaryResponse, status_code=status.HTTP_201_CREATED)
async def import_soft4x_excel(
    file: UploadFile = File(...),
    version_id: int = Form(...),
    prop_stage_id: Optional[int] = Form(None),
    personal_account_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    مسیر وارد کردن معاملات از فایل اکسل Soft4X Simulator
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فرمت فایل نامعتبر است. لطفاً فایل اکسل (.xlsx یا .xls) آپلود کنید."
        )

    validate_references(db, version_id, prop_stage_id, personal_account_id)

    try:
        contents = await file.read()
        service = ImportService(db)
        summary = service.parse_soft4x_excel(
            file_bytes=contents,
            version_id=version_id,
            prop_stage_id=prop_stage_id,
            personal_account_id=personal_account_id
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطای غیرمنتظره در پردازش فایل: {str(e)}"
        )


@router.post("/mt4", response_model=ImportSummaryResponse, status_code=status.HTTP_201_CREATED)
async def import_mt4_html(
    file: UploadFile = File(...),
    version_id: int = Form(...),
    prop_stage_id: Optional[int] = Form(None),
    personal_account_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    مسیر وارد کردن معاملات از گزارش HTML متاتریدر ۴ (MT4 Detailed Report)
    """
    if not file.filename.endswith((".html", ".htm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فرمت فایل نامعتبر است. لطفاً فایل HTML (.html یا .htm) آپلود کنید."
        )

    validate_references(db, version_id, prop_stage_id, personal_account_id)

    try:
        contents = await file.read()
        service = ImportService(db)
        summary = service.parse_mt4_html(
            file_bytes=contents,
            version_id=version_id,
            prop_stage_id=prop_stage_id,
            personal_account_id=personal_account_id
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطای غیرمنتظره در پردازش فایل MT4: {str(e)}"
        )


@router.post("/manual", response_model=ManualTradeResponse, status_code=status.HTTP_201_CREATED)
def import_manual_trade(
    trade_in: ManualTradeCreate,
    db: Session = Depends(get_db)
):
    """
    مسیر ثبت دستی معامله
    """
    validate_references(db, trade_in.version_id, trade_in.prop_stage_id, trade_in.personal_account_id)

    service = ImportService(db)
    trade, message = service.manual_trade_entry(trade_in.model_dump())

    if not trade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return ManualTradeResponse(
        id=trade.id,
        symbol=trade.symbol,
        direction=trade.direction,
        open_time=trade.open_time,
        open_price=trade.open_price,
        size=trade.size,
        pnl=trade.pnl,
        r_multiple=trade.r_multiple,
        trade_hash=trade.trade_hash,
        message=message
    )


@router.delete("/rollback/{source}", response_model=RollbackResponse)
def rollback_imports(
    source: str,
    version_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    پاک‌سازی یا رول‌بک معاملات ایمپورت‌شده بر اساس source و version_id
    """
    if source not in ["soft4x", "mt4", "manual"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="منبع نامعتبر است. گزینه‌های مجاز: soft4x, mt4, manual"
        )

    service = ImportService(db)
    deleted_count = service.cleanup_imported_trades(source=source, version_id=version_id)

    return RollbackResponse(
        source=source,
        deleted_count=deleted_count,
        message=f"تعداد {deleted_count} معامله مربوط به منبع '{source}' پاک‌سازی شد."
    )