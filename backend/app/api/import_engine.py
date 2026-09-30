"""API موتور ایمپورت (فاز ۳۰/۳۱).

Pipeline: File ← Parse ← Normalize ← Validate ← Duplicate ← Preview
          ← User Confirm ← Atomic Commit

Endpointها:
- `POST /api/imports/preview`            : آپلود + Preview (بدون هیچ تغییری در معاملات)
- `POST /api/imports/commit/{batch_id}`  : تأیید کاربر → Commit اتمیک
- `POST /api/imports/batches/{id}/cancel`: لغو Preview
- `GET  /api/imports/batches`            : تاریخچه‌ی ایمپورت‌ها
- `GET  /api/imports/batches/{id}`       : جزئیات یک Import (+ ردیف‌ها)
- CRUD `/api/imports/profiles`           : پروفایل‌های ایمپورت
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.rate_limit import IMPORT_RATE_LIMIT, limiter
from ..models.imports import ImportBatch, ImportProfile, ImportSourceFormat, ImportStatus
from ..models.trading import Broker
from ..services import import_engine as engine_service
from ..services.import_engine import (
    MAPPABLE_COLUMNS,
    ImportContext,
    ImportEngine,
    ImportEngineError,
    build_context,
    normalize_source_format,
    parse_source,
)
from ..utils.uploads import read_upload_limited

router = APIRouter()

HTML_ENCODINGS = ("utf-8", "utf-16", "windows-1256", "iso-8859-1", "cp1252")


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class ImportCommitRequest(BaseModel):
    """تأیید کاربر برای ذخیره‌ی یک ImportBatch."""
    allow_possible_duplicates: bool = False
    user_id: Optional[int] = None


class ImportProfileCreate(BaseModel):
    name: str
    broker_id: Optional[int] = None
    source_format: ImportSourceFormat
    symbol_mapping: Optional[Dict[str, str]] = None
    column_mapping: Optional[Dict[str, Any]] = None
    default_context: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    is_active: bool = True


class ImportProfileUpdate(BaseModel):
    name: Optional[str] = None
    broker_id: Optional[int] = None
    source_format: Optional[ImportSourceFormat] = None
    symbol_mapping: Optional[Dict[str, str]] = None
    column_mapping: Optional[Dict[str, Any]] = None
    default_context: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def raise_http(error: ImportEngineError) -> HTTPException:
    """ImportEngineError → HTTPException (کد و پیام همان است)."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


def infer_source_format(file_name: Optional[str]) -> ImportSourceFormat:
    """تشخیص قالب از پسوند فایل (xlsx → Soft4X، html → MT4)."""
    name = (file_name or "").strip().lower()
    if name.endswith(".xlsx"):
        return ImportSourceFormat.SOFT4X_XLSX
    if name.endswith(".html") or name.endswith(".htm"):
        return ImportSourceFormat.MT4_HTML
    raise ImportEngineError("پسوند فایل پشتیبانی نمی‌شود (xlsx یا html لازم است)", 400)


def ensure_extension(source_format: ImportSourceFormat, file_name: Optional[str]) -> None:
    """سازگاری با پیام‌های فاز قبل برای پسوند نامعتبر."""
    name = (file_name or "").strip().lower()
    if source_format == ImportSourceFormat.SOFT4X_XLSX and not name.endswith(".xlsx"):
        raise ImportEngineError("فایل باید با فرمت xlsx باشد", 400)
    if source_format == ImportSourceFormat.MT4_HTML and not (
        name.endswith(".html") or name.endswith(".htm")
    ):
        raise ImportEngineError("فایل باید با فرمت html باشد", 400)


def parse_json_form(value: Optional[str], field_name: str) -> Optional[Dict[str, Any]]:
    """فیلد Form حاوی JSON → dict (خطای ۴۰۰ در صورت JSON نامعتبر)."""
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"فرمت {field_name} نامعتبر است (JSON لازم است)")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail=f"{field_name} باید یک object باشد")
    return parsed


def decode_html(content: bytes) -> str:
    """رمزگشایی HTML با چند انکودینگ رایج (سازگاری فاز قبل)."""
    for encoding in HTML_ENCODINGS:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ImportEngineError("نمی‌توان فایل را خواند", 400)


def parse_uploaded_file(
    db: Session,
    source_format: ImportSourceFormat,
    content: bytes,
    ctx: ImportContext,
) -> List[Dict[str, Any]]:
    """مرحله Parse روی محتوای آپلودشده (فایل موقت برای xlsx)."""
    if source_format == ImportSourceFormat.SOFT4X_XLSX:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            return parse_source(
                db,
                source_format,
                file_path=tmp_path,
                symbol=ctx.symbol,
                test_type=ctx.test_type,
                column_mapping=ctx.column_mapping,
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return parse_source(
        db,
        source_format,
        html_content=decode_html(content),
        test_type=ctx.test_type,
        column_mapping=ctx.column_mapping,
    )


def build_context_from_form(
    db: Session,
    *,
    source_format: Optional[str],
    profile_id: Optional[int],
    test_type: Optional[str],
    version_id: Optional[int],
    prop_stage_id: Optional[int],
    personal_trading_account_id: Optional[int],
    symbol: Optional[str],
    column_mapping: Optional[str],
    symbol_mapping: Optional[str],
    file_name: Optional[str],
):
    """ساخت ImportContext از فرم multipart (با پیش‌فرض‌های ImportProfile)."""
    fmt = (
        normalize_source_format(source_format)
        if source_format
        else infer_source_format(file_name)
    )
    ctx = build_context(
        db,
        source_format=fmt,
        test_type=test_type,
        version_id=version_id,
        prop_stage_id=prop_stage_id,
        personal_trading_account_id=personal_trading_account_id,
        symbol=symbol,
        profile_id=profile_id,
        column_mapping=parse_json_form(column_mapping, "column_mapping"),
        symbol_mapping=parse_json_form(symbol_mapping, "symbol_mapping"),
    )
    return ctx, fmt


# ═════════════════════════════════════════════
# Preview / Commit
# ═════════════════════════════════════════════
@router.post("/preview")
@limiter.limit(IMPORT_RATE_LIMIT)
async def preview_import(
    request: Request,
    file: UploadFile = File(...),
    source_format: Optional[str] = Form(None),
    profile_id: Optional[int] = Form(None),
    test_type: Optional[str] = Form(None),
    version_id: Optional[int] = Form(None),
    prop_stage_id: Optional[int] = Form(None),
    personal_trading_account_id: Optional[int] = Form(None),
    symbol: Optional[str] = Form(None),
    column_mapping: Optional[str] = Form(None),
    symbol_mapping: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    """Preview یک فایل بدون هیچ تغییری در معاملات (خروجی برای تأیید کاربر)."""
    try:
        ctx, fmt = build_context_from_form(
            db,
            source_format=source_format,
            profile_id=profile_id,
            test_type=test_type,
            version_id=version_id,
            prop_stage_id=prop_stage_id,
            personal_trading_account_id=personal_trading_account_id,
            symbol=symbol,
            column_mapping=column_mapping,
            symbol_mapping=symbol_mapping,
            file_name=file.filename,
        )
        ensure_extension(fmt, file.filename)

        content = await read_upload_limited(file)
        raw_rows = parse_uploaded_file(db, fmt, content, ctx)

        engine = ImportEngine(db)
        _, summary = engine.create_preview(
            ctx=ctx,
            raw_rows=raw_rows,
            file_name=file.filename,
            user_id=user_id,
        )
        return summary
    except ImportEngineError as error:
        raise raise_http(error)


@router.post("/commit/{batch_id}")
def commit_import(
    batch_id: int,
    payload: Optional[ImportCommitRequest] = None,
    db: Session = Depends(get_db),
):
    """تأیید کاربر → Commit اتمیک ردیف‌های staging‌شده."""
    allow_possible = bool(payload.allow_possible_duplicates) if payload else False
    try:
        engine = ImportEngine(db)
        result = engine.commit(batch_id, allow_possible_duplicates=allow_possible)
        return result
    except ImportEngineError as error:
        raise raise_http(error)


@router.post("/batches/{batch_id}/cancel")
def cancel_import(batch_id: int, db: Session = Depends(get_db)):
    """لغو یک Preview (بدون هیچ تغییری روی معاملات)."""
    try:
        return ImportEngine(db).cancel(batch_id)
    except ImportEngineError as error:
        raise raise_http(error)


@router.get("/batches")
def list_import_batches(
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """تاریخچه‌ی ایمپورت‌ها (جدیدترین اول)."""
    parsed_status = None
    if status:
        try:
            parsed_status = ImportStatus(status.strip().lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"وضعیت نامعتبر: {status}")
    return ImportEngine(db).list_batches(limit=max(1, min(limit, 200)), status=parsed_status)


@router.get("/batches/{batch_id}")
def get_import_batch(
    batch_id: int,
    include_rows: bool = True,
    rows_limit: int = 50,
    db: Session = Depends(get_db),
):
    """جزئیات یک ImportBatch (+ ردیف‌های staging)."""
    try:
        batch = ImportEngine(db).get_batch(batch_id)
        return engine_service.serialize_batch(
            batch, include_rows=include_rows, rows_limit=max(1, min(rows_limit, 500))
        )
    except ImportEngineError as error:
        raise raise_http(error)


# ═════════════════════════════════════════════
# ImportProfile CRUD (فاز ۳۰)
# ═════════════════════════════════════════════
def serialize_profile(profile: ImportProfile) -> Dict[str, Any]:
    return {
        "id": profile.id,
        "name": profile.name,
        "broker_id": profile.broker_id,
        "broker_name": profile.broker.name if profile.broker else None,
        "source_format": profile.source_format.value if profile.source_format else None,
        "symbol_mapping": profile.symbol_mapping or {},
        "column_mapping": profile.column_mapping or {},
        "default_context": profile.default_context or {},
        "notes": profile.notes,
        "is_active": profile.is_active,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


def validate_profile_payload(
    db: Session,
    *,
    broker_id: Optional[int],
    column_mapping: Optional[Dict[str, Any]],
    default_context: Optional[Dict[str, Any]],
) -> None:
    """اعتبارسنجی شکل پروفایل (Broker / ستون‌ها / نوع تست پیش‌فرض)."""
    if broker_id is not None:
        broker = db.query(Broker).filter(Broker.id == broker_id).first()
        if not broker:
            raise HTTPException(status_code=404, detail="بروکر پیدا نشد")

    if column_mapping:
        unknown = [key for key in column_mapping if key not in MAPPABLE_COLUMNS]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"فیلد نامعتبر در column_mapping: {', '.join(unknown)} "
                f"(مجاز: {', '.join(MAPPABLE_COLUMNS)})",
            )

    if default_context and default_context.get("test_type") is not None:
        try:
            engine_service.normalize_test_type(default_context.get("test_type"))
        except ImportEngineError as error:
            raise raise_http(error)


@router.get("/profiles")
def list_import_profiles(
    include_inactive: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(ImportProfile)
    if not include_inactive:
        query = query.filter(ImportProfile.is_active == True)  # noqa: E712
    rows = query.order_by(ImportProfile.name.asc()).all()
    return [serialize_profile(profile) for profile in rows]


@router.get("/profiles/{profile_id}")
def get_import_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(ImportProfile).filter(ImportProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="پروفایل ایمپورت پیدا نشد")
    return serialize_profile(profile)


@router.post("/profiles")
def create_import_profile(data: ImportProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(ImportProfile).filter(ImportProfile.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"پروفایل «{data.name}» قبلاً ساخته شده است")

    validate_profile_payload(
        db,
        broker_id=data.broker_id,
        column_mapping=data.column_mapping,
        default_context=data.default_context,
    )

    profile = ImportProfile(
        name=data.name,
        broker_id=data.broker_id,
        source_format=data.source_format,
        symbol_mapping=data.symbol_mapping,
        column_mapping=data.column_mapping,
        default_context=data.default_context,
        notes=data.notes,
        is_active=data.is_active,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {
        "id": profile.id,
        "message": "پروفایل ایمپورت ساخته شد",
        "profile": serialize_profile(profile),
    }


@router.patch("/profiles/{profile_id}")
def update_import_profile(
    profile_id: int,
    data: ImportProfileUpdate,
    db: Session = Depends(get_db),
):
    profile = db.query(ImportProfile).filter(ImportProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="پروفایل ایمپورت پیدا نشد")

    payload = data.model_dump(exclude_unset=True)

    new_name = payload.get("name")
    if new_name and new_name != profile.name:
        duplicate = db.query(ImportProfile).filter(ImportProfile.name == new_name).first()
        if duplicate:
            raise HTTPException(status_code=400, detail=f"پروفایل «{new_name}» قبلاً ساخته شده است")

    validate_profile_payload(
        db,
        broker_id=payload.get("broker_id"),
        column_mapping=payload.get("column_mapping"),
        default_context=payload.get("default_context"),
    )

    for field, value in payload.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return {"message": "پروفایل ایمپورت به‌روزرسانی شد", "profile": serialize_profile(profile)}


@router.delete("/profiles/{profile_id}")
def delete_import_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(ImportProfile).filter(ImportProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="پروفایل ایمپورت پیدا نشد")
    # فاز ۴۲.۸: اکنون FK روشن است؛ ارجاع ImportBatch به این پروفایل باید آزاد شود.
    # تاریخچهٔ ایمپورت حذف نمی‌شود — فقط ارجاع پروفایل NULL می‌شود.
    db.query(ImportBatch).filter(ImportBatch.profile_id == profile_id).update(
        {ImportBatch.profile_id: None}, synchronize_session=False
    )
    db.delete(profile)
    db.commit()
    return {"message": "پروفایل ایمپورت حذف شد"}



