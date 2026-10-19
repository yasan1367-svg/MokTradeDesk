"""Shared helpers for normalizing datetimes returned by SQLite."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo


def as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Return an aware UTC datetime, treating naive values as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def tehran_day_bounds(now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return the current Tehran calendar day's start/end as UTC datetimes."""
    if now is None:
        now = datetime.now(timezone.utc)
    tehran = ZoneInfo("Asia/Tehran")
    local = now.astimezone(tehran)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Serialize a datetime as an offset-bearing UTC ISO string."""
    normalized = as_utc(dt)
    return normalized.isoformat() if normalized else None