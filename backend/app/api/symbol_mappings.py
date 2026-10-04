from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ..core.database import get_db
from ..models.strategy import SymbolMapping

router = APIRouter()


class SymbolMappingCreate(BaseModel):
    original_symbol: str
    canonical_symbol: str
    description: Optional[str] = None


class SymbolMappingUpdate(BaseModel):
    original_symbol: Optional[str] = None
    canonical_symbol: Optional[str] = None
    description: Optional[str] = None


@router.get("/")
def get_mappings(db: Session = Depends(get_db)):
    """لیست همه‌ی Symbol Mappingها"""
    mappings = db.query(SymbolMapping).order_by(SymbolMapping.original_symbol).all()
    return [
        {
            "id": m.id,
            "original_symbol": m.original_symbol,
            "canonical_symbol": m.canonical_symbol,
            "description": m.description,
            "created_at": m.created_at,
        }
        for m in mappings
    ]


@router.post("/")
def create_mapping(data: SymbolMappingCreate, db: Session = Depends(get_db)):
    """ساخت Symbol Mapping جدید"""
    existing = db.query(SymbolMapping).filter(
        SymbolMapping.original_symbol == data.original_symbol
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"نماد «{data.original_symbol}» قبلاً تعریف شده است"
        )

    mapping = SymbolMapping(
        original_symbol=data.original_symbol,
        canonical_symbol=data.canonical_symbol,
        description=data.description,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return {"id": mapping.id, "message": "Symbol Mapping ساخته شد"}


@router.patch("/{mapping_id}")
def update_mapping(mapping_id: int, data: SymbolMappingUpdate, db: Session = Depends(get_db)):
    """ویرایش Symbol Mapping"""
    mapping = db.query(SymbolMapping).filter(SymbolMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping پیدا نشد")

    if data.original_symbol is not None:
        mapping.original_symbol = data.original_symbol
    if data.canonical_symbol is not None:
        mapping.canonical_symbol = data.canonical_symbol
    if data.description is not None:
        mapping.description = data.description

    db.commit()
    return {"message": "Symbol Mapping به‌روزرسانی شد"}


@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """حذف Symbol Mapping"""
    mapping = db.query(SymbolMapping).filter(SymbolMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping پیدا نشد")

    db.delete(mapping)
    db.commit()
    return {"message": "Symbol Mapping حذف شد"}


@router.post("/seed-defaults")
def seed_defaults(db: Session = Depends(get_db)):
    """وارد کردن Symbol Mappingهای پیش‌فرض — گسترانده برای پوشش همه‌ی suffixهای رایج بروکر.

    امن برای اجرای مجدد (upsert): فقط مپینگ‌های غایب را اضافه می‌کند،
    مپینگ‌های تعریف‌شده توسط کاربر را دست‌نمی‌زند.
    """
    from sqlalchemy.exc import IntegrityError

    defaults = [
        # ── XAUUSD (طلا) ──
        {"original_symbol": "XAUUSD",   "canonical_symbol": "XAUUSD", "description": "طلا - نماد اصلی"},
        {"original_symbol": "XAUUSD.x", "canonical_symbol": "XAUUSD", "description": "طلا - فرمت متاتریدر جدید"},
        {"original_symbol": "XAUUSD.a", "canonical_symbol": "XAUUSD", "description": "طلا - فرمت بروکر"},
        {"original_symbol": "XAUUSD.pro", "canonical_symbol": "XAUUSD", "description": "طلا - فرمت حرفه‌ای بروکر"},
        {"original_symbol": "GOLD",      "canonical_symbol": "XAUUSD", "description": "طلا - نام رایج"},
        {"original_symbol": "GOLD.x",    "canonical_symbol": "XAUUSD", "description": "طلا - فرمت متاتریدر جدید"},
        {"original_symbol": "GOLD.a",    "canonical_symbol": "XAUUSD", "description": "طلا - فرمت بروکر"},

        # ── DJIUSD (داوجونز) ──
        {"original_symbol": "DJIUSD",   "canonical_symbol": "DJIUSD", "description": "داوجونز - نماد اصلی"},
        {"original_symbol": "DJIUSD.x", "canonical_symbol": "DJIUSD", "description": "داوجونز - فرمت متاتریدر جدید"},
        {"original_symbol": "DJIUSD.a", "canonical_symbol": "DJIUSD", "description": "داوجونز - فرمت بروکر"},
        {"original_symbol": "US30",     "canonical_symbol": "DJIUSD", "description": "داوجونز - نام رایج"},
        {"original_symbol": "US30.x",   "canonical_symbol": "DJIUSD", "description": "داوجونز - فرمت متاتریدر جدید"},
    ]
    created = []
    for data in defaults:
        try:
            # savepoint برای ایزوله‌سازی هر ردیف: خطای unique در یک ردیف
            # بقیهٔ ردیف‌ها را خراب نمی‌کند (upsert واقعی).
            with db.begin_nested():
                mapping = SymbolMapping(**data)
                db.add(mapping)
            created.append(data["original_symbol"])
        except IntegrityError:
            # مپینگ قبلاً موجود است — ردیف رد می‌شود بدون اثر جانبی
            pass
    db.commit()
    return {"message": f"{len(created)} Mapping اضافه شد", "created": created}