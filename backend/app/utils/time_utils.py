"""فاز ۴۶.۲ — ابزار مشترک زمان (Time helpers).

قرارداد:
- تمام زمان‌های ذخیره‌شده در دیتابیس **UTC aware** هستند.
- زمان‌های «بدون tz» به‌عنوان ساعت **سرور بروکر/پراپ** تفسیر می‌شوند و با
  `server_utc_offset_minutes` به UTC تبدیل می‌گردند (فاز ۴۶.۱).
- تصمیم D3 کاربر: ساعت MT4 = GMT+0 ⇒ offset پیش‌فرض 0.
"""
from datetime import datetime, timedelta, timezone


def to_utc(dt: datetime, offset_minutes: int = 0) -> datetime:
    """Convert a source-local datetime to UTC.

    - tz-aware: convert to UTC directly.
    - naive + offset=0: treat as UTC (legacy behavior preserved).
    - naive + offset!=0: interpret as local with the offset.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        if offset_minutes == 0:
            return dt.replace(tzinfo=timezone.utc)
        tz = timezone(timedelta(minutes=offset_minutes))
        return dt.replace(tzinfo=tz).astimezone(timezone.utc)
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

