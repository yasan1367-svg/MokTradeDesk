"""فاز ۴۶.۳ — تبدیل تاریخ میلادی ↔ شمسی (منبع واحد).

پیش از این، الگوریتم تبدیل در دو جا کپی شده بود (`api/finance.py` و `api/analytics.py`).
اکنون تنها مرجع همین ماژول است. (پیاده‌سازی داخلی، بدون وابستگی اضافه.)

قرارداد:
- `gregorian_to_jalali_parts(gy, gm, gd) -> (jy, jm, jd)`
- `jalali_to_gregorian_parts(jy, jm, jd) -> (gy, gm, gd)`
- `gregorian_to_jalali(dt) -> "YYYY/MM/DD"`
- `jalali_to_gregorian(jalali_str) -> datetime.date`
"""
from datetime import date, datetime

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def jalali_to_gregorian_parts(jy: int, jm: int, jd: int):
    """تبدیل تاریخ شمسی به میلادی (بازگشت: (year, month, day))."""
    jy += 1595
    days = -355668 + (365 * jy) + (jy // 33) * 8 + ((jy % 33 + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += (jm - 7) * 30 + 186

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    sal_a = [0, 31, 29 if (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0 else 28,
             31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    for gm in range(13):
        if gd <= sal_a[gm]:
            break
        gd -= sal_a[gm]
    return gy, gm, gd


def gregorian_to_jalali_parts(gy: int, gm: int, gd: int):
    """تبدیل تاریخ میلادی به شمسی (بازگشت: (year, month, day))."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    jy = 0 if gy <= 1600 else 979
    gy -= 621 if gy <= 1600 else 1600
    gy2 = gy + 1 if gm > 2 else gy
    days = ((365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
            + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1])
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def gregorian_to_jalali(dt) -> str:
    """میلادی ← شمسی (YYYY/MM/DD)."""
    d = dt.date() if isinstance(dt, datetime) else dt
    jy, jm, jd = gregorian_to_jalali_parts(d.year, d.month, d.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def jalali_to_gregorian(jalali_str: str) -> date:
    """شمسی («YYYY/MM/DD») ← میلادی."""
    y, m, d = (int(p) for p in str(jalali_str).split("/"))
    gy, gm, gd = jalali_to_gregorian_parts(y, m, d)
    return date(gy, gm, gd)
