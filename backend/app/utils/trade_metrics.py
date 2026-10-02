"""
توابع کمکی مشترک برای محاسبات معامله (R-Multiple و ...)
این‌ها هم توی ایمپورترها (Soft4X, MT4) و هم توی ثبت دستی معامله استفاده می‌شن
تا فرمول محاسبه همه‌جا یکسان باشه.
"""
from typing import Optional


def calculate_r_multiple(
    direction: str,
    open_price: Optional[float],
    close_price: Optional[float],
    sl: Optional[float],
    initial_sl: Optional[float] = None,
) -> Optional[float]:
    """
    محاسبه‌ی R-Multiple بر پایه‌ی فاصله‌ی قیمتی (مستقل از حجم و نوع نماد).

    R = فاصله‌ی سود/زیان / فاصله‌ی ریسک (استاپ‌لاس)

    - فاز ۵۳.۳: اگر **استاپِ اولیه** (`initial_sl`) موجود باشد، ریسک بر پایه‌ی آن
      محاسبه می‌شود (چون SL ممکن است در طول معامله جابجا شده باشد)، وگرنه `sl`.
    - اگه استاپ‌لاس ثبت نشده باشه، R قابل‌محاسبه نیست → None برمی‌گرده
      (این عمداً silent-zero نمی‌کنه، چون معامله‌ی بدون SL با R=0 اشتباه گرفته می‌شه)
    - اگه استاپ‌لاس در جهت اشتباه ثبت شده باشه (فاصله‌ی ریسک <= 0)، همینطور None
    """
    effective_sl = initial_sl if initial_sl is not None else sl
    if effective_sl is None or open_price is None or close_price is None:
        return None

    direction = (direction or "").lower()

    if direction == "buy":
        risk_distance = open_price - effective_sl
        move_distance = close_price - open_price
    elif direction == "sell":
        risk_distance = effective_sl - open_price
        move_distance = open_price - close_price
    else:
        return None

    if risk_distance <= 0:
        return None

    return round(move_distance / risk_distance, 3)
