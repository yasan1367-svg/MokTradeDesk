from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import os
import hashlib

from ..core.database import get_db
from ..models.personal import (
    PersonalAccount, LedgerTransaction, JournalReview, Screenshot,
    TransactionType
)
from ..models.strategy import Trade

router = APIRouter()


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class PersonalAccountCreate(BaseModel):
    name: str
    broker_name: str
    account_number: Optional[str] = None
    currency: str = "USD"
    initial_balance: float = 0.0


class PersonalAccountUpdate(BaseModel):
    name: Optional[str] = None
    broker_name: Optional[str] = None
    account_number: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[int] = None


class LedgerTransactionCreate(BaseModel):
    transaction_type: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    personal_account_id: Optional[int] = None
    prop_account_id: Optional[int] = None
    transaction_date: Optional[str] = None


class JournalReviewCreate(BaseModel):
    trade_id: int
    setup_quality: Optional[int] = None
    execution_quality: Optional[int] = None
    rule_violations: Optional[str] = None
    notes: Optional[str] = None
    lessons: Optional[str] = None
    rating: Optional[int] = None


# ═════════════════════════════════════════════
# Personal Accounts
# ═════════════════════════════════════════════
@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    """لیست اکانت‌های شخصی"""
    accounts = db.query(PersonalAccount).all()
    result = []
    for a in accounts:
        # محاسبه‌ی موجودی فعلی از روی تراکنش‌ها
        transactions = db.query(LedgerTransaction).filter(
            LedgerTransaction.personal_account_id == a.id
        ).all()
        total_flow = sum(t.amount for t in transactions)
        current_balance = (a.initial_balance or 0) + total_flow

        # تعداد معاملات
        trades_count = db.query(Trade).filter(
            Trade.personal_account_id == a.id
        ).count()

        result.append({
            "id": a.id,
            "name": a.name,
            "broker_name": a.broker_name,
            "account_number": a.account_number,
            "currency": a.currency,
            "initial_balance": a.initial_balance,
            "current_balance": round(current_balance, 2),
            "is_active": a.is_active,
            "trades_count": trades_count,
            "created_at": a.created_at,
        })
    return result


@router.post("/accounts")
def create_account(account: PersonalAccountCreate, db: Session = Depends(get_db)):
    """ساخت اکانت شخصی جدید"""
    db_account = PersonalAccount(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return {"id": db_account.id, "message": "اکانت شخصی ساخته شد"}


@router.get("/accounts/{account_id}")
def get_account_detail(account_id: int, db: Session = Depends(get_db)):
    """جزئیات اکانت شخصی"""
    account = db.query(PersonalAccount).filter(PersonalAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="اکانت پیدا نشد")

    transactions = db.query(LedgerTransaction).filter(
        LedgerTransaction.personal_account_id == account_id
    ).order_by(LedgerTransaction.transaction_date.desc()).all()

    total_flow = sum(t.amount for t in transactions)
    current_balance = (account.initial_balance or 0) + total_flow

    return {
        "id": account.id,
        "name": account.name,
        "broker_name": account.broker_name,
        "account_number": account.account_number,
        "currency": account.currency,
        "initial_balance": account.initial_balance,
        "current_balance": round(current_balance, 2),
        "is_active": account.is_active,
        "transactions": [
            {
                "id": t.id,
                "transaction_type": t.transaction_type.value if t.transaction_type else None,
                "amount": t.amount,
                "currency": t.currency,
                "description": t.description,
                "transaction_date": t.transaction_date,
            }
            for t in transactions
        ],
    }


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, data: PersonalAccountUpdate, db: Session = Depends(get_db)):
    """ویرایش اکانت شخصی"""
    account = db.query(PersonalAccount).filter(PersonalAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="اکانت پیدا نشد")

    if data.name is not None:
        account.name = data.name
    if data.broker_name is not None:
        account.broker_name = data.broker_name
    if data.account_number is not None:
        account.account_number = data.account_number
    if data.currency is not None:
        account.currency = data.currency
    if data.is_active is not None:
        account.is_active = data.is_active

    db.commit()
    return {"message": "اکانت به‌روزرسانی شد"}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """حذف اکانت شخصی"""
    account = db.query(PersonalAccount).filter(PersonalAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="اکانت پیدا نشد")

    db.delete(account)
    db.commit()
    return {"message": "اکانت حذف شد"}


# ═════════════════════════════════════════════
# Ledger Transactions
# ═════════════════════════════════════════════
@router.get("/ledger")
def get_ledger(
    personal_account_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """لیست تراکنش‌های دفتر کل با فیلتر"""
    query = db.query(LedgerTransaction)

    if personal_account_id:
        query = query.filter(LedgerTransaction.personal_account_id == personal_account_id)
    if transaction_type:
        query = query.filter(LedgerTransaction.transaction_type == transaction_type)
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            query = query.filter(LedgerTransaction.transaction_date >= from_dt)
        except:
            pass
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            query = query.filter(LedgerTransaction.transaction_date <= to_dt)
        except:
            pass

    transactions = query.order_by(LedgerTransaction.transaction_date.desc()).limit(limit).all()

    return [
        {
            "id": t.id,
            "transaction_type": t.transaction_type.value if t.transaction_type else None,
            "amount": t.amount,
            "currency": t.currency,
            "description": t.description,
            "personal_account_id": t.personal_account_id,
            "prop_account_id": t.prop_account_id,
            "transaction_date": t.transaction_date,
        }
        for t in transactions
    ]


@router.post("/ledger")
def create_transaction(data: LedgerTransactionCreate, db: Session = Depends(get_db)):
    """ثبت تراکنش جدید"""
    try:
        transaction_type = TransactionType(data.transaction_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="نوع تراکنش نامعتبر")

    transaction_date = datetime.utcnow()
    if data.transaction_date:
        try:
            transaction_date = datetime.fromisoformat(data.transaction_date)
        except:
            pass

    db_transaction = LedgerTransaction(
        transaction_type=transaction_type,
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        personal_account_id=data.personal_account_id,
        prop_account_id=data.prop_account_id,
        transaction_date=transaction_date,
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return {"id": db_transaction.id, "message": "تراکنش ثبت شد"}


@router.delete("/ledger/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """حذف تراکنش"""
    transaction = db.query(LedgerTransaction).filter(LedgerTransaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="تراکنش پیدا نشد")

    db.delete(transaction)
    db.commit()
    return {"message": "تراکنش حذف شد"}


# ═════════════════════════════════════════════
# Cash Flow Report
# ═════════════════════════════════════════════
@router.get("/cashflow")
def get_cashflow(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """گزارش جریان نقدی"""
    query = db.query(LedgerTransaction)

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            query = query.filter(LedgerTransaction.transaction_date >= from_dt)
        except:
            pass
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            query = query.filter(LedgerTransaction.transaction_date <= to_dt)
        except:
            pass

    transactions = query.order_by(LedgerTransaction.transaction_date).all()

    # گروه‌بندی بر اساس نوع تراکنش
    by_type = {}
    total_in = 0
    total_out = 0

    for t in transactions:
        t_type = t.transaction_type.value if t.transaction_type else "unknown"
        if t_type not in by_type:
            by_type[t_type] = {"count": 0, "total": 0}
        by_type[t_type]["count"] += 1
        by_type[t_type]["total"] += t.amount

        if t.amount > 0:
            total_in += t.amount
        else:
            total_out += abs(t.amount)

    return {
        "total_in": round(total_in, 2),
        "total_out": round(total_out, 2),
        "net": round(total_in - total_out, 2),
        "by_type": {k: {"count": v["count"], "total": round(v["total"], 2)} for k, v in by_type.items()},
        "transactions_count": len(transactions),
    }


# ═════════════════════════════════════════════
# Journal Review
# ═════════════════════════════════════════════
@router.post("/journal/review")
def create_review(data: JournalReviewCreate, db: Session = Depends(get_db)):
    """ثبت مرور معامله"""
    trade = db.query(Trade).filter(Trade.id == data.trade_id).first()
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

    content = await file.read()
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
        except:
            pass

    db.delete(screenshot)
    db.commit()
    return {"message": "اسکرین‌شات حذف شد"}


@router.get("/journal/reviews")
def get_reviews(db: Session = Depends(get_db)):
    """لیست همه‌ی مرورها"""
    reviews = db.query(JournalReview).order_by(JournalReview.created_at.desc()).all()
    result = []
    for r in reviews:
        trade = db.query(Trade).filter(Trade.id == r.trade_id).first()
        screenshots = db.query(Screenshot).filter(
            Screenshot.entity_type == "review",
            Screenshot.entity_id == r.id,
        ).all()
        result.append({
            "id": r.id,
            "trade_id": r.trade_id,
            "trade_symbol": trade.symbol if trade else "نامشخص",
            "trade_pnl": trade.pnl if trade else 0,
            "setup_quality": r.setup_quality,
            "execution_quality": r.execution_quality,
            "rule_violations": r.rule_violations,
            "notes": r.notes,
            "lessons": r.lessons,
            "rating": r.rating,
            "screenshots_count": len(screenshots),
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
            except:
                pass
        db.delete(screenshot)

    db.delete(review)
    db.commit()
    return {"message": "مرور حذف شد"}

@router.get("/prop-accounts-list")
def get_prop_accounts_for_ledger(db: Session = Depends(get_db)):
    """لیست اکانت‌های پراپ (برای انتخاب در دفتر کل)"""
    from ..models.prop import PropAccount, PropFirm
    accounts = db.query(PropAccount).all()
    result = []
    for a in accounts:
        firm = db.query(PropFirm).filter(PropFirm.id == a.prop_firm_id).first()
        result.append({
            "id": a.id,
            "label": a.account_label,
            "firm_name": firm.name if firm else "نامشخص",
            "display_name": f"🏢 {firm.name if firm else '?'} / {a.account_label}",
        })
    return result