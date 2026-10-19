from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Literal, Optional
from pydantic import BaseModel

from ..core.database import get_db
from ..models.settings import UserSettings

router = APIRouter()


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None
    font_size: Optional[int] = None
    timezone: Optional[str] = None
    currency: Optional[Literal["IRR", "USDT"]] = None
    calendar: Optional[str] = None
    default_risk_percent: Optional[int] = None
    default_profit_share: Optional[int] = None


def get_or_create_settings(db: Session) -> UserSettings:
    settings = db.query(UserSettings).first()
    if not settings:
        settings = UserSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    s = get_or_create_settings(db)
    return {
        "id": s.id,
        "theme": s.theme,
        "font_size": s.font_size,
        "timezone": s.timezone,
        "currency": s.currency,
        "calendar": s.calendar,
        "default_risk_percent": s.default_risk_percent,
        "default_profit_share": s.default_profit_share,
        "updated_at": s.updated_at,
    }


@router.patch("/")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    s = get_or_create_settings(db)

    if data.theme is not None:
        s.theme = data.theme
    if data.font_size is not None:
        s.font_size = data.font_size
    if data.timezone is not None:
        s.timezone = data.timezone
    if data.currency is not None:
        s.currency = data.currency
    if data.calendar is not None:
        s.calendar = data.calendar
    if data.default_risk_percent is not None:
        s.default_risk_percent = data.default_risk_percent
    if data.default_profit_share is not None:
        s.default_profit_share = data.default_profit_share

    db.commit()
    db.refresh(s)
    return {"message": "تنظیمات ذخیره شد"}
