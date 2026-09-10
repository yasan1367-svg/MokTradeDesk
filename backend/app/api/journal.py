from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from typing import Optional

from app.services.personal_service import (
    PersonalService,
    ExecutionQuality,
    EmotionalState
)

router = APIRouter(prefix="/api/journal", tags=["Trading Journal"])


class JournalReviewRequest(BaseModel):
    trade_id: str
    execution_quality: ExecutionQuality
    emotional_state: EmotionalState
    notes: Optional[str] = None
    lessons_learned: Optional[str] = None


@router.post("/review")
async def create_or_update_journal_review(payload: JournalReviewRequest):
    """
    ثبت یا ویرایش تحلیل، روان‌شناسی و کیفیت اجرای معامله در ژورنال
    """
    entry = PersonalService.upsert_journal_entry(
        trade_id=payload.trade_id,
        execution_quality=payload.execution_quality,
        emotional_state=payload.emotional_state,
        notes=payload.notes,
        lessons_learned=payload.lessons_learned
    )
    return {"message": "ژورنال معامله با موفقیت به روزرسانی شد", "journal_entry": entry}


@router.post("/screenshot")
async def upload_journal_screenshot(
    trade_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    آپلود اسکرین‌شات معامله و ذخیره آن در پوشه uploads/screenshots/
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فایل ارسالی باید تصویر (Image) باشد."
        )

    file_bytes = await file.read()
    file_path = PersonalService.save_journal_screenshot(
        trade_id=trade_id,
        file_bytes=file_bytes,
        filename=file.filename
    )

    return {
        "message": "تصویر با موفقیت ذخیره و به ژورنال پیوند داده شد",
        "trade_id": trade_id,
        "saved_path": file_path
    }


@router.get("/{trade_id}")
async def get_journal_entry(trade_id: str):
    entry = PersonalService.journal_db.get(trade_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ژورنالی برای معامله {trade_id} یافت نشد."
        )
    return entry