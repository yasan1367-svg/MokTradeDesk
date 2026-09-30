"""فاز ۴۶.۵ — تبدیل بازهٔ تاریخی به بازهٔ زمانی نیمه‌باز.

مشکل قبلی: `date_to` فقط نیمه‌شب آن روز بود ⇒ معاملات/تراکنش‌های همان روز حذف
می‌شدند. اکنون `date_to` **شامل** کل روز است: بازهٔ `[from 00:00 , to+1day 00:00)`.
همهٔ زمان‌ها UTC هستند.
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple


def parse_date(value) -> Optional[date]:
    """تبدیل `date`/`datetime`/رشتهٔ ISO به `date` (None در صورت خالی/نامعتبر)."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except ValueError:
        return None


def date_range(date_from=None, date_to=None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """بازهٔ `(from_dt, to_dt)` نیمه‌باز با احترام به اینکه `date_to` شامل باشد.

    - `from_dt` = نیمه‌شب روز شروع (UTC)
    - `to_dt`   = نیمه‌شب **روز بعدِ** روز پایان (UTC) ⇒ فیلتر باید `< to_dt` باشد.
    """
    d_from = parse_date(date_from)
    d_to = parse_date(date_to)
    from_dt = (
        datetime.combine(d_from, time.min).replace(tzinfo=timezone.utc)
        if d_from else None
    )
    to_dt = (
        datetime.combine(d_to + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)
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
