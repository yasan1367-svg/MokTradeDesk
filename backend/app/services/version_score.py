"""فاز 52 — Score جدید برای رتبه‌بندی Versionها (فرمول بازنگری‌شده).

مشکلات فرمول قدیم (فاز 48a):
- PnL دلاری ⇒ سقف سریع می‌خورد و اندازهٔ حساب را نمی‌دید.
- بدون درصد بازده / بدون ریسک هر معامله.
- بدون توجه به تعداد معاملات (نمونه).
- DD جریمهٔ محدود داشت.
- Win Rate تنها معیار «کیفیت» بود.

فرمول جدید (بر پایهٔ معیارهای قابل‌فهم):
    expectancy_score = clamp(expectancy_r / 1.0, 0, 1) * 100   وزن ۴۰٪  (مهم‌ترین)
    win_rate_score   = clamp(win_rate, 0, 100)                 وزن ۲۰٪
    pf_score         = clamp(profit_factor / 5 * 100, 0, 100)  وزن ۲۰٪
    dd_score         = clamp(100 - dd_percent * 5, 0, 100)     وزن ۲۰٪  (کمتر بهتر)
    score = (Σ وزن‌دار) − sample_penalty                        کلمپ ۰..۱۰۰

وضعیت نمونه:
    n < 10  ⇒ «خیلی کم»   (جریمه ۳۰)
    n < 30  ⇒ «ناکافی»    (جریمه ۱۵)
    n ≥ 30  ⇒ «کافی»      (بدون جریمه)

توجه: اندازهٔ حساب در دیتابیس موجود نیست؛ برای درصد Drawdown از یک حساب
فرضی ثابت (`ASSUMED_ACCOUNT_SIZE`) استفاده می‌شود. اگر متریک `max_dd_percent`
مستقیماً موجود باشد، همان اولویت دارد.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

# اندازهٔ حساب فرضی (USDT) برای تبدیل Drawdown مطلق به درصد — گام ۲ (گزینهٔ الف)
ASSUMED_ACCOUNT_SIZE = 10000.0

# آستانه‌های نمونه
SAMPLE_VERY_LOW = 10
SAMPLE_ENOUGH = 30

# وزن اجزا
W_EXPECTANCY = 0.40
W_WIN_RATE = 0.20
W_PROFIT_FACTOR = 0.20
W_DRAWDOWN = 0.20


def _as_float(value: Any, default: float = 0.0) -> float:
    """تبدیل ایمن به float (None/نامعتبر ⇒ default)."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _dd_percent(metrics: Mapping[str, Any]) -> float:
    """درصد حداکثر افت سرمایه.

    اگر `max_dd_percent` موجود باشد همان؛ وگرنه `max_dd / ASSUMED_ACCOUNT_SIZE`.
    """
    explicit = metrics.get("max_dd_percent")
    if explicit is not None:
        return _as_float(explicit, 0.0)
    max_dd = _as_float(metrics.get("max_dd"), 0.0)
    if ASSUMED_ACCOUNT_SIZE:
        return max_dd / ASSUMED_ACCOUNT_SIZE * 100.0
    return 0.0


def calculate_version_score(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    """امتیاز یک نسخه از روی متریک‌هایش + وضعیت نمونه + هشدارها.

    Returns:
        {
            "score": float,           # 0..100
            "sample_status": str,     # «کافی» / «ناکافی» / «خیلی کم»
            "warnings": list[str],
            "components": {expectancy_score, win_rate_score, pf_score,
                           dd_score, sample_penalty},
        }
    """
    # ── ۱. تعداد معاملات (نمونه) ──
    n = int(_as_float(metrics.get("total_trades"), 0.0))

    if n < SAMPLE_VERY_LOW:
        sample_status = "خیلی کم"
        sample_penalty = 30.0
    elif n < SAMPLE_ENOUGH:
        sample_status = "ناکافی"
        sample_penalty = 15.0
    else:
        sample_status = "کافی"
        sample_penalty = 0.0

    # ── ۲. اجزای امتیاز ──

    # الف) Expectancy بر حسب R (مهم‌ترین): 0.5R خوب، 1R عالی
    expectancy_r = _as_float(metrics.get("expectancy_r"), 0.0)
    expectancy_score = min(max(expectancy_r / 1.0, 0.0), 1.0) * 100.0

    # ب) Win Rate (وزن کمتر)
    win_rate = _as_float(metrics.get("win_rate"), 0.0)
    win_rate_score = min(max(win_rate, 0.0), 100.0)

    # ج) Profit Factor (سقف ۵)
    pf = _as_float(metrics.get("profit_factor"), 0.0)
    pf_score = min(max(pf / 5.0 * 100.0, 0.0), 100.0)

    # د) Drawdown درصدی (کمتر بهتر): 0% ⇒ 100 ، 20% ⇒ 0
    dd_percent = _dd_percent(metrics)
    dd_score = max(0.0, 100.0 - dd_percent * 5.0)

    score = (
        expectancy_score * W_EXPECTANCY
        + win_rate_score * W_WIN_RATE
        + pf_score * W_PROFIT_FACTOR
        + dd_score * W_DRAWDOWN
    ) - sample_penalty
    score = max(0.0, min(score, 100.0))

    # ── ۳. هشدارها ──
    warnings: List[str] = []
    if n < SAMPLE_ENOUGH:
        warnings.append(f"نمونه کم: {n} معامله (حداقل {SAMPLE_ENOUGH})")
    if dd_percent > 15:
        warnings.append(f"Drawdown بالا: {dd_percent:.1f}%")
    if expectancy_r < 0.2:
        warnings.append(f"Expectancy ضعیف: {expectancy_r:.2f}R")

    return {
        "score": round(score, 2),
        "sample_status": sample_status,
        "warnings": warnings,
        "components": {
            "expectancy_score": round(expectancy_score, 2),
            "win_rate_score": round(win_rate_score, 2),
            "pf_score": round(pf_score, 2),
            "dd_score": round(dd_score, 2),
            "sample_penalty": sample_penalty,
        },
    }
