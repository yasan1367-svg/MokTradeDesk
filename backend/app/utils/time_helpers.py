"""Shared helpers for normalizing datetimes returned by SQLite."""
from datetime import datetime, timezone
from typing import Optional


def as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Return an aware UTC datetime, treating naive values as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Serialize a datetime as an offset-bearing UTC ISO string."""
    normalized = as_utc(dt)
    return normalized.isoformat() if normalized else None