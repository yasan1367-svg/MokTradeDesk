"""فاز ۴۶.۲ — ابزار مشترک زمان (Time helpers).

قرارداد:
- تمام زمان‌های ذخیره‌شده در دیتابیس **UTC aware** هستند.
- زمان‌های «بدون tz» به‌عنوان ساعت **سرور بروکر/پراپ** تفسیر می‌شوند و با
  `server_utc_offset_minutes` به UTC تبدیل می‌گردند (فاز ۴۶.۱).
- تصمیم D3 کاربر: ساعت MT4 = GMT+0 ⇒ offset پیش‌فرض 0.
"""
from datetime import datetime, timedelta, timezone

from .time_helpers import as_utc


def to_utc(dt: datetime, offset_minutes: int = 0) -> datetime:
    """تبدیل زمان local (با offset) به UTC.

    - اگر `dt` آگاه از tz باشد ⇒ فقط به UTC منتقل می‌شود.
    - اگر naive باشد ⇒ مطابق قرارداد مشترک، UTC فرض می‌شود (offset نادیده گرفته می‌شود).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return as_utc(dt)
    return dt.astimezone(timezone.utc)


def from_utc(dt: datetime, offset_minutes: int = 0) -> datetime:
    """تبدیل UTC به local با offset داده‌شده."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone(timedelta(minutes=offset_minutes or 0)))


def now_utc() -> datetime:
    """الان UTC (aware)."""
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════
# فاز ۴۶.۴ — منطقهٔ زمانی تهران (برای تاریخ شمسی)
# ═════════════════════════════════════════════
try:  # pragma: no cover - بستگی به وجود tzdata دارد
    from zoneinfo import ZoneInfo

    TEHRAN = ZoneInfo("Asia/Tehran")
except Exception:  # pragma: no cover
    # fallback: ایران از ۲۰۲۲ DST ندارد ⇒ UTC+03:30 ثابت
    TEHRAN = timezone(timedelta(hours=3, minutes=30))


def to_tehran(dt: datetime) -> datetime:
    """تبدیل زمان (UTC یا naive-UTC) به وقت تهران."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TEHRAN)


def tehran_date(dt: datetime):
    """تاریخ تقویمی تهران برای یک لحظه (برای گروه‌بندی روز/ماه شمسی)."""
    return to_tehran(dt).date()

