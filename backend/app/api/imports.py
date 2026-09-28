"""Endpointهای ایمپورت فایل (سازگاری فاز قبل) — فاز ۳۰: روی موتور جدید.

این دو endpoint همان رابط قدیمی را نگه می‌دارند (UI فعلی بدون تغییر کار می‌کند)،
اما Pipeline واقعی این است:
    File ← Parse ← Normalize ← Validate ← Duplicate ← Preview ← Atomic Commit

نکته: این مسیر «Preview خودکار + Commit» است و ردیف‌های مشکوک به تکرار
(POSSIBLE_DUPLICATE) را — مثل رفتار فاز قبل — وارد می‌کند و فقط تکرارهای قطعی
را رد می‌کند. مسیر انتخابی کاربر (`/api/imports/preview` + `/commit`) سخت‌گیرانه است.
"""
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.rate_limit import limiter, IMPORT_RATE_LIMIT
from ..models.imports import ImportSourceFormat
from ..services.import_engine import ImportEngine, ImportEngineError, validate_contract
from ..utils.uploads import read_upload_limited
from .import_engine import (
    build_context_from_form,
    decode_html,
    ensure_extension,
    raise_http,
)

router = APIRouter()


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def _target_label(test_type, prop_stage_id, personal_trading_account_id) -> str:
    """برچسب مقصد برای پیام کاربر (سازگاری با UI فاز قبل)."""
    if prop_stage_id:
        return "پراپ"
    if personal_trading_account_id:
        return "حساب شخصی"
    return "استراتژی"
def _legacy_response(result: dict, raw_rows: list, target_label: str = "") -> dict:
    """پاسخ سازگار با UI فاز قبل (+ batch_id و شمارنده‌های فاز ۳۰/۳۱)."""
    imported = result.get("imported", 0)
    duplicates = result.get("duplicate", 0)
    counts = result.get("counts", {})

    if counts.get("possible_duplicate"):
        message = (
            f"{imported} معامله ذخیره شد — {duplicates} تکراری نادیده گرفته شد "
            f"({counts.get('possible_duplicate')} مورد مشکوک به تکرار وارد شد)"
        )
    elif duplicates:
        message = f"{imported} معامله ذخیره شد — {duplicates} معامله تکراری نادیده گرفته شد"
    else:
        message = f"{imported} معامله با موفقیت وارد شد"

    return {
        "message": message,
        "batch_id": result.get("batch_id"),
        "batch_status": result.get("status"),
        "total_trades": result.get("total", len(raw_rows)),
        "saved_trades": imported,
        "duplicates_count": duplicates,
        "possible_duplicates_count": counts.get("possible_duplicate", 0),
        "invalid_count": counts.get("invalid", 0),
        "preview": raw_rows[:3],
    }


def _run_legacy_import(
    db: Session,
    *,
    source_format: ImportSourceFormat,
    file_name: str,
    target_label: str,
    kwargs: dict,
    html_content: Optional[str] = None,
    file_path: Optional[str] = None,
):
    """Preview + Commit با موتور جدید و نگاشت خطاها به رفتار فاز قبل."""
    try:
        ctx, fmt = build_context_from_form(
            db,
            source_format=source_format.value,
            file_name=file_name,
            **kwargs,
        )
        ensure_extension(fmt, file_name)
        # قرارداد معامله قبل از Parse بررسی می‌شود (پیام خطای دقیق‌تر به کاربر)
        validate_contract(ctx)

        from ..services.import_engine import parse_source

        if file_path is not None:
            raw_rows = parse_source(
                db,
                fmt,
                file_path=file_path,
                symbol=ctx.symbol,
                test_type=ctx.test_type,
                column_mapping=ctx.column_mapping,
            )
        else:
            raw_rows = parse_source(
                db,
                fmt,
                html_content=html_content,
                test_type=ctx.test_type,
                column_mapping=ctx.column_mapping,
            )

        if not raw_rows:
            raise HTTPException(status_code=400, detail="هیچ معامله‌ای در فایل یافت نشد")

        engine = ImportEngine(db)
        result = engine.import_rows(
            ctx=ctx,
            raw_rows=raw_rows,
            file_name=file_name,
            allow_possible_duplicates=True,
        )
        response = _legacy_response(result, raw_rows, target_label)
        if target_label:
            response["message"] = "{} ({})".format(response["message"], target_label)
        return response
    except ImportEngineError as error:
        raise raise_http(error)


@router.post("/soft4x")
@limiter.limit(IMPORT_RATE_LIMIT)
async def import_soft4x(
    request: Request,
    file: UploadFile = File(...),
    version_id: Optional[int] = Form(None),
    prop_stage_id: Optional[int] = Form(None),
    symbol: Optional[str] = Form("XAUUSD"),
    personal_trading_account_id: Optional[int] = Form(None),
    test_type: Optional[str] = Form("backtest"),
    profile_id: Optional[int] = Form(None),
    column_mapping: Optional[str] = Form(None),
    symbol_mapping: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """ایمپورت فایل اکسل Soft4X (Preview خودکار + Commit اتمیک)."""
    if not (file.filename or "").endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="فایل باید با فرمت xlsx باشد")

    content = await read_upload_limited(file)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        return _run_legacy_import(
            db,
            source_format=ImportSourceFormat.SOFT4X_XLSX,
            file_name=file.filename,
            target_label=_target_label(test_type, prop_stage_id, personal_trading_account_id),
            file_path=tmp_path,
            kwargs=dict(
                profile_id=profile_id,
                test_type=test_type,
                version_id=version_id,
                prop_stage_id=prop_stage_id,
                personal_trading_account_id=personal_trading_account_id,
                symbol=symbol,
                column_mapping=column_mapping,
                symbol_mapping=symbol_mapping,
            ),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — سازگاری با پیام خطای فاز قبل
        raise HTTPException(status_code=500, detail=f"خطا در پردازش فایل: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/mt4")
@limiter.limit(IMPORT_RATE_LIMIT)
async def import_mt4(
    request: Request,
    file: UploadFile = File(...),
    version_id: Optional[int] = Form(None),
    personal_trading_account_id: Optional[int] = Form(None),
    prop_stage_id: Optional[int] = Form(None),
    test_type: Optional[str] = Form("backtest"),
    profile_id: Optional[int] = Form(None),
    column_mapping: Optional[str] = Form(None),
    symbol_mapping: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """ایمپورت گزارش HTML متاتریدر (Preview خودکار + Commit اتمیک)."""
    if not (file.filename or "").endswith(".html"):
        raise HTTPException(status_code=400, detail="فایل باید با فرمت html باشد")

    try:
        content = await read_upload_limited(file)
        return _run_legacy_import(
            db,
            source_format=ImportSourceFormat.MT4_HTML,
            file_name=file.filename,
            target_label=_target_label(test_type, prop_stage_id, personal_trading_account_id),
            html_content=decode_html(content),
            kwargs=dict(
                profile_id=profile_id,
                test_type=test_type,
                version_id=version_id,
                prop_stage_id=prop_stage_id,
                personal_trading_account_id=personal_trading_account_id,
                symbol=None,
                column_mapping=column_mapping,
                symbol_mapping=symbol_mapping,
            ),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — سازگاری با پیام خطای فاز قبل
        raise HTTPException(status_code=500, detail=f"خطا در پردازش فایل: {exc}")
