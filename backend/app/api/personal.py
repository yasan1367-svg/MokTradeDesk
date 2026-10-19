import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import os
import hashlib

from ..core.database import get_db
from ..models.personal import JournalReview, Screenshot
from ..models.strategy import Trade
from ..utils.uploads import read_upload_limited

logger = logging.getLogger("moktrade")
router = APIRouter()


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class JournalReviewCreate(BaseModel):
    trade_id: int
    setup_quality: Optional[int] = None
    execution_quality: Optional[int] = None
    rule_violations: Optional[str] = None
    notes: Optional[str] = None
    lessons: Optional[str] = None
    rating: Optional[int] = None


# ═════════════════════════════════════════════
# Journal Review
# ═════════════════════════════════════════════
@router.post("/journal/review")
def create_review(data: JournalReviewCreate, db: Session = Depends(get_db)):
    """ثبت مرور معامله"""
    # فاز ۲۵: برای معامله‌ی حذف‌شده نمی‌توان مرور ثبت کرد
    trade = db.query(Trade).filter(
        Trade.id == data.trade_id
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    review = JournalReview(**data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)

    return {"id": review.id, "message": "مرور ثبت شد"}


@router.post("/journal/reviews/{review_id}/screenshots")
async def upload_review_screenshot(
    review_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """آپلود اسکرین‌شات برای یک مرور معامله"""
    review = db.query(JournalReview).filter(JournalReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="مرور پیدا نشد")

    allowed_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="فرمت فایل پشتیبانی نمی‌شود")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"review_{review_id}_{timestamp}{ext}"
    file_path = f"storage/screenshots/{file_name}"

    content = await read_upload_limited(file)
    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = hashlib.md5(content).hexdigest()
    screenshot = Screenshot(
        entity_type="review",
        entity_id=review_id,
        review_id=review_id,
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
        "message": "اسکرین‌شات مرور آپلود شد",
    }


@router.get("/journal/reviews/{review_id}/screenshots")
def get_review_screenshots(review_id: int, db: Session = Depends(get_db)):
    """لیست اسکرین‌شات‌های یک مرور"""
    screenshots = db.query(Screenshot).filter(
        Screenshot.entity_type == "review",
        Screenshot.entity_id == review_id,
    ).all()
    return [
        {
            "id": s.id,
            "file_path": s.file_path,
            "description": s.description,
            "uploaded_at": s.uploaded_at,
        }
        for s in screenshots
    ]


@router.delete("/journal/reviews/screenshots/{screenshot_id}")
def delete_review_screenshot(screenshot_id: int, db: Session = Depends(get_db)):
    """حذف اسکرین‌شات مرور"""
    screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
    if not screenshot:
        raise HTTPException(status_code=404, detail="اسکرین‌شات پیدا نشد")

    if os.path.exists(screenshot.file_path):
        try:
            os.remove(screenshot.file_path)
        except OSError as exc:
            logger.warning("Could not remove review screenshot %s: %s", screenshot.file_path, exc)

    db.delete(screenshot)
    db.commit()
    return {"message": "اسکرین‌شات حذف شد"}


@router.get("/journal/reviews")
def get_reviews(db: Session = Depends(get_db)):
    """لیست همه‌ی مرورها"""
    # selectinload: trade و screenshots هر کدام در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    reviews = (
        db.query(JournalReview)
        .options(selectinload(JournalReview.trade), selectinload(JournalReview.screenshots))
        .order_by(JournalReview.created_at.desc())
        .all()
    )
    result = []
    for r in reviews:
        trade = r.trade
        result.append({
            "id": r.id,
            "trade_id": r.trade_id,
            "trade_symbol": trade.symbol if trade else "نامشخص",
            "trade_pnl": trade.pnl if trade else 0,
            "trade_net_pnl": trade.net_pnl if trade else 0,
            "setup_quality": r.setup_quality,
            "execution_quality": r.execution_quality,
            "rule_violations": r.rule_violations,
            "notes": r.notes,
            "lessons": r.lessons,
            "rating": r.rating,
            "screenshots_count": len(r.screenshots),
            "created_at": r.created_at,
        })
    return result


@router.delete("/journal/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    """حذف مرور"""
    review = db.query(JournalReview).filter(JournalReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="مرور پیدا نشد")

    screenshots = db.query(Screenshot).filter(
        Screenshot.entity_type == "review",
        Screenshot.entity_id == review_id,
    ).all()
    for screenshot in screenshots:
        if os.path.exists(screenshot.file_path):
            try:
                os.remove(screenshot.file_path)
            except OSError as exc:
                logger.warning("Could not remove review screenshot %s: %s", screenshot.file_path, exc)
        db.delete(screenshot)

    db.delete(review)
    db.commit()
    return {"message": "مرور حذف شد"}


@router.get("/prop-accounts-list")
def get_prop_accounts_for_ledger(db: Session = Depends(get_db)):
    """لیست اکانت‌های پراپ (برای انتخاب در دفتر کل)"""
    from ..models.prop import PropAccount
    # selectinload: firm در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    accounts = db.query(PropAccount).options(selectinload(PropAccount.firm)).all()
    result = []
    for a in accounts:
        firm = a.firm
        result.append({
            "id": a.id,
            "label": a.account_label,
            "firm_name": firm.name if firm else "نامشخص",
            "display_name": f"🏢 {firm.name if firm else '?'} / {a.account_label}",
        })
    return result
