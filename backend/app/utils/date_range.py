"""فاز ۴۶.۵ — تبدیل بازهٔ تاریخی به بازهٔ زمانی نیمه‌باز.

مشکل قبلی: `date_to` فقط نیمه‌شب آن روز بود ⇒ معاملات/تراکنش‌های همان روز حذف
می‌شدند. اکنون `date_to` **شامل** کل روز است: بازهٔ `[from 00:00 , to+1day 00:00)`.
همهٔ زمان‌ها UTC هستند.
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

from .time_utils import TEHRAN


def parse_date(value) -> Optional[date]:
    """تبدیل `date`/`datetime`/رشتهٔ ISO به `date` (None در صورت خالی/نامعتبر)."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        # Aware timestamps represent an instant; date-only filtering is against
        # the canonical Tehran calendar. Naive timestamps retain legacy UTC.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(TEHRAN).date()
    if isinstance(value, date):
        return value
    try:
        raw = str(value).strip()
        if len(raw) == 10:
            return date.fromisoformat(raw)
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(TEHRAN).date()
    except ValueError:
        return None


def date_range(date_from=None, date_to=None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Half-open UTC bounds for inclusive Tehran calendar dates.

    Date-only inputs use Tehran midnight. Explicit timestamp inputs are first
    interpreted as absolute instants (naive means UTC), then their Tehran date
    selects the full calendar day. Use timestamp bounds directly in endpoints
    that need precise instant semantics.
    """
    d_from = parse_date(date_from)
    d_to = parse_date(date_to)
    from_dt = (
        datetime.combine(d_from, time.min, tzinfo=TEHRAN).astimezone(timezone.utc)
        if d_from else None
    )
    to_dt = (
        datetime.combine(d_to + timedelta(days=1), time.min, tzinfo=TEHRAN).astimezone(timezone.utc)
        if d_to else None
    )
    return from_dt, to_dt


def filter_by_range(query, column, date_from=None, date_to=None):
    """اعمال فیلتر بازهٔ تاریخی (شامل آخرین روز) روی یک کوئری SQLAlchemy."""
    from_dt, to_dt = date_range(date_from, date_to)
    if from_dt is not None:
        query = query.filter(column >= from_dt)
    if to_dt is not None:
        query = query.filter(column < to_dt)
    return query
