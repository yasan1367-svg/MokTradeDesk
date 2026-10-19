from pydantic import BaseModel, Field, field_validator, model_validator, StrictInt
from typing import Optional, List
from datetime import datetime


# ═════════════════════════════════════════════
# CustomTimeInterval
# ═════════════════════════════════════════════
class CustomTimeIntervalCreate(BaseModel):
    name: str
    symbol: str
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    label: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    is_active: int = 1


class CustomTimeIntervalResponse(BaseModel):
    id: int
    name: str
    symbol: str
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    label: Optional[str]
    priority: Optional[int]
    description: Optional[str]
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════
# TimePoint
# ═════════════════════════════════════════════
class TimePointCreate(BaseModel):
    symbol: str
    hour: int
    minute: int
    label: Optional[str] = None
    is_active: int = 1


class TimePointResponse(BaseModel):
    id: int
    symbol: str
    hour: int
    minute: int
    label: Optional[str]
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════
# Comparison (فاز 48a — قرارداد جدید)
# ═════════════════════════════════════════════
class CompareRequest(BaseModel):
    version_ids: List[StrictInt] = Field(..., min_length=2, max_length=10)
    test_type: Optional[str] = "BACKTEST"
    symbol: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    @field_validator("version_ids")
    @classmethod
    def positive_unique_ids(cls, value):
        if any(item <= 0 for item in value):
            raise ValueError("شناسه نسخه باید عدد صحیح مثبت باشد")
        if len(set(value)) != len(value):
            raise ValueError("شناسه نسخه تکراری مجاز نیست")
        return value

    @field_validator("test_type")
    @classmethod
    def supported_test_type(cls, value):
        if value is None:
            return value
        normalized = value.strip().upper()
        supported = {"BACKTEST", "FORWARD", "REAL_PERSONAL", "REAL_PROP"}
        if normalized not in supported:
            raise ValueError("test_type باید یکی از BACKTEST, FORWARD, REAL_PERSONAL یا REAL_PROP باشد")
        return normalized

    @field_validator("date_from", "date_to")
    @classmethod
    def valid_iso_date_or_timestamp(cls, value):
        if value is None:
            return value
        from datetime import date, datetime
        raw = value.strip()
        try:
            if len(raw) == 10:
                date.fromisoformat(raw)
            else:
                datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError("تاریخ باید ISO معتبر و یک روز تقویمی واقعی یا timestamp باشد") from exc
        return raw

    @model_validator(mode="after")
    def validate_range(self):
        from datetime import datetime, timezone
        from app.api.analytics import _parse_bound
        start = _parse_bound(self.date_from, end=False)
        end = _parse_bound(self.date_to, end=True)
        if self.date_from is not None and start is None:
            raise ValueError("date_from نامعتبر است")
        if self.date_to is not None and end is None:
            raise ValueError("date_to نامعتبر است")
        if start is not None and end is not None:
            def normalized(value):
                return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
            if normalized(start) > normalized(end):
                raise ValueError("date_from نباید بعد از date_to باشد")
        return self