"""
API اخبار اقتصادی — تقویم Forex Factory.

GET /api/news/upcoming?limit=3
GET /api/news/refresh (dev only, 30-minute attempt minimum)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.news_service import (
    ensure_today_events,
    get_today_events,
    get_upcoming,
    is_stale,
    refresh_force,
)
from ..utils.time_helpers import as_utc, to_utc_iso

logger = logging.getLogger("moktrade.api.news")
router = APIRouter()


def news_now() -> datetime:
    """Injectable UTC clock for news endpoints."""
    return datetime.now(timezone.utc)


def _serialize_events(events, now=None):
    """Serialize stored events with explicit UTC offsets."""
    current = as_utc(now or datetime.now(timezone.utc))
    results = []
    for event in events:
        event_time = as_utc(event.event_time)
        minutes_until = int((event_time - current).total_seconds() // 60)
        results.append({
            "id": event.id,
            "title": event.title,
            "currency": event.currency,
            "impact": event.impact,
            "event_time": to_utc_iso(event.event_time),
            "forecast": event.forecast,
            "previous": event.previous,
            "minutes_until": minutes_until,
        })
    return results


@router.get("/upcoming")
def news_upcoming(
    limit: int = Query(3, ge=1, le=50),
    scope: str | None = Query(None, pattern="^today$"),
    db: Session = Depends(get_db),
    now: datetime = Depends(news_now),
):
    """بازگرداندن N رویداد اقتصادی بعدی از هفت روز آینده.

    ابتدا کش امروز را تأمین می‌کند (در صورت نیاز fetch). سپس رویدادهای آینده را
    تا سقف `limit` برمی‌گرداند.
    """
    ensure_today_events(db, now=now)

    events = (
        get_today_events(db, limit=limit, now=now)
        if scope == "today"
        else get_upcoming(db, limit=limit, now=now)
    )
    results = _serialize_events(events, now=now)

    return {
        "events": results,
        "count": len(results),
        "stale": is_stale(db, now=now),
    }


@router.get("/refresh")
def news_refresh(
    db: Session = Depends(get_db),
):
    """درخواست fetch جدید با رعایت حداقل فاصلهٔ ۳۰ دقیقه — فقط برای توسعه.

    Returns:
        رویدادهای High/Medium دلار.
    """
    now = datetime.now(timezone.utc)
    refresh_force(db, now=now)
    events = get_upcoming(db, limit=50, now=now)
    results = _serialize_events(events, now=now)

    return {
        "events": results,
        "count": len(results),
        "stale": is_stale(db, now=now),
        "note": "force-refresh (30-minute attempt minimum)",
    }