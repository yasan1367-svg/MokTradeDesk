"""
News Service — دریافت و کش رویدادهای اقتصادی از تقویم Forex Factory.

وابستگی‌ها:
- HTTP client: `httpx` (ترجیح) یا `requests` (fallback).
- تجزیهٔ JSON با `json` (stdlib).
"""
import json
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models.economic_event import EconomicEvent
from ..utils.time_helpers import as_utc

logger = logging.getLogger("moktrade.news")

FOREX_FACTORY_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
TEHRAN = ZoneInfo("Asia/Tehran")
FETCH_COOLDOWN = timedelta(minutes=30)

_last_attempt: Optional[datetime] = None
_last_success: Optional[datetime] = None
_last_failed = False
_fetch_lock = threading.Lock()

try:
    import httpx
    _HTTP_AVAILABLE = True
    _USING_HTTPX = True

    def _http_get(url: str) -> tuple[int, str, Optional[str]]:
        """GET with httpx using the feed's required timeout and headers."""
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=HEADERS)
            return response.status_code, response.text, response.headers.get("Retry-After")

except ImportError:
    try:
        import requests
        _HTTP_AVAILABLE = True
        _USING_HTTPX = False

        def _http_get(url: str) -> tuple[int, str, Optional[str]]:
            """GET with requests using the feed's required timeout and headers."""
            response = requests.get(url, timeout=10.0, headers=HEADERS)
            return response.status_code, response.text, response.headers.get("Retry-After")

    except ImportError:
        _HTTP_AVAILABLE = False
        _USING_HTTPX = False

        def _http_get(url: str) -> tuple[int, str, Optional[str]]:
            raise RuntimeError("No HTTP client (httpx or requests) is installed")

logger.info(
    "News HTTP client: %s",
    "httpx" if _USING_HTTPX else "requests" if _HTTP_AVAILABLE else "NONE",
)


def reset_fetch_state() -> None:
    """Reset process-local scheduling state (primarily for isolated tests)."""
    global _last_attempt, _last_success, _last_failed
    _last_attempt = None
    _last_success = None
    _last_failed = False


def _utc_now(now: Optional[datetime]) -> datetime:
    value = as_utc(now or datetime.now(timezone.utc))
    if value is None:  # pragma: no cover - guarded by the expression above
        raise ValueError("now is required")
    return value


def _tehran_date(value: Optional[datetime]) -> Optional[date]:
    normalized = as_utc(value)
    return normalized.astimezone(TEHRAN).date() if normalized else None


def fetch_forex_factory() -> list[dict]:
    """Fetch and parse USD High/Medium events from the Forex Factory JSON feed."""
    status, body, retry_after = _http_get(FOREX_FACTORY_URL)
    logger.info(
        "News fetch | %s | HTTP %s | retry-after: %s",
        FOREX_FACTORY_URL, status, retry_after or "none",
    )
    if status >= 400:
        raise RuntimeError(f"Forex Factory returned HTTP {status}")

    data = json.loads(body)
    if not isinstance(data, list):
        raise ValueError("Forex Factory JSON payload is not a list")

    events: list[dict] = []
    seen: set[tuple[str, datetime]] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        currency = str(item.get("country") or "").strip().upper()
        impact = str(item.get("impact") or "").strip().capitalize()
        date_str = str(item.get("date") or "").strip()

        if currency != "USD" or impact not in ("High", "Medium"):
            continue
        if not title or not date_str:
            continue

        try:
            event_time = datetime.fromisoformat(date_str).astimezone(timezone.utc)
        except (TypeError, ValueError):
            logger.warning("Failed to parse event date: %s", date_str)
            continue

        key = (title, event_time)
        if key in seen:
            continue
        seen.add(key)
        events.append({
            "title": title,
            "currency": currency,
            "impact": impact,
            "event_time": event_time,
            "forecast": item.get("forecast") or None,
            "previous": item.get("previous") or None,
        })

    events.sort(key=lambda event: event["event_time"])
    logger.info(
        "Parsed %d USD High/Medium events from %d total JSON events",
        len(events), len(data),
    )
    return events


def _upsert_events(db: Session, events: list[dict], fetched_date: date) -> int:
    """Update or insert events using title and normalized UTC time as identity."""
    try:
        existing = {
            (row.title, as_utc(row.event_time)): row
            for row in db.query(EconomicEvent).all()
        }
        inserted = 0
        for item in events:
            key = (item["title"], as_utc(item["event_time"]))
            row = existing.get(key)
            if row is None:
                row = EconomicEvent(
                    title=item["title"],
                    currency=item["currency"],
                    event_time=item["event_time"],
                )
                db.add(row)
                existing[key] = row
                inserted += 1
            row.forecast = item.get("forecast")
            row.previous = item.get("previous")
            row.impact = item["impact"]
            row.fetched_date = fetched_date
        db.flush()
        return inserted
    except Exception:
        db.rollback()
        raise


def _already_fetched_today(db: Session, tehran_today: date) -> bool:
    in_database = db.query(EconomicEvent.id).filter(
        EconomicEvent.fetched_date == tehran_today
    ).first() is not None
    return in_database or _tehran_date(_last_success) == tehran_today


def _attempt_throttled(now: datetime) -> bool:
    return (
        _last_attempt is not None
        and _tehran_date(_last_attempt) == now.astimezone(TEHRAN).date()
        and now - as_utc(_last_attempt) < FETCH_COOLDOWN
    )


def _fetch_and_store(db: Session, now: datetime, force: bool = False) -> bool:
    """Run one scheduled fetch synchronously; return whether it succeeded."""
    global _last_attempt, _last_success, _last_failed
    tehran_today = now.astimezone(TEHRAN).date()

    with _fetch_lock:
        if (not force and _already_fetched_today(db, tehran_today)) or _attempt_throttled(now):
            return False

        _last_attempt = now
        try:
            events = fetch_forex_factory()
            inserted = _upsert_events(db, events, tehran_today)
            cutoff = (now - timedelta(days=7)).replace(tzinfo=None)
            deleted = db.query(EconomicEvent).filter(
                EconomicEvent.event_time < cutoff
            ).delete(synchronize_session=False)
            db.commit()
            _last_success = now
            _last_failed = False
            logger.info(
                "Fetched %d news events, inserted %d, cleaned %d stale rows",
                len(events), inserted, deleted,
            )
            return True
        except Exception as exc:
            db.rollback()
            _last_failed = True
            logger.warning(
                "Failed to fetch/store Forex Factory calendar; keeping cached data: %s",
                exc,
            )
            return False


def ensure_today_events(db: Session, now: Optional[datetime] = None) -> None:
    """Ensure one successful fetch per Asia/Tehran calendar day."""
    _fetch_and_store(db, _utc_now(now))


def refresh_force(db: Session, now: Optional[datetime] = None) -> None:
    """Force a fetch unless an attempt occurred during the last 30 minutes."""
    _fetch_and_store(db, _utc_now(now), force=True)


def is_stale(db: Session, now: Optional[datetime] = None) -> bool:
    """Return whether news may be stale for the current Tehran calendar day."""
    current = _utc_now(now)
    today = current.astimezone(TEHRAN).date()
    return _last_failed or not _already_fetched_today(db, today)


def get_upcoming(
    db: Session,
    limit: int = 3,
    now: Optional[datetime] = None,
) -> List[EconomicEvent]:
    """Return the next N events from now through the next seven days."""
    current = _utc_now(now)
    end = current + timedelta(days=7)
    query_now = current.replace(tzinfo=None)
    query_end = end.replace(tzinfo=None)
    return (
        db.query(EconomicEvent)
        .filter(
            EconomicEvent.event_time >= query_now,
            EconomicEvent.event_time <= query_end,
        )
        .order_by(EconomicEvent.event_time.asc())
        .limit(limit)
        .all()
    )


def get_today_events(
    db: Session,
    limit: int = 20,
    now: Optional[datetime] = None,
) -> List[EconomicEvent]:
    """Return events from the last hour through the end of the Tehran day."""
    current = _utc_now(now)
    tehran_now = current.astimezone(TEHRAN)
    next_tehran_day = datetime.combine(
        tehran_now.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=TEHRAN,
    )
    query_start = (current - timedelta(minutes=60)).replace(tzinfo=None)
    query_end = next_tehran_day.astimezone(timezone.utc).replace(tzinfo=None)
    return (
        db.query(EconomicEvent)
        .filter(
            EconomicEvent.event_time >= query_start,
            EconomicEvent.event_time < query_end,
        )
        .order_by(EconomicEvent.event_time.asc())
        .limit(limit)
        .all()
    )