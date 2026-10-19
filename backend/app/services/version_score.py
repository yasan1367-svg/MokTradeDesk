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

Drawdown پولی بدون سرمایهٔ مبنا درصد افت واقعی نیست. Score فقط از درصد
صریح `max_dd_percent` استفاده می‌کند؛ در نبود آن DD خنثی است (۵۰/۱۰۰) و
در خروجی با وضعیت unavailable مشخص می‌شود.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping

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


def _dd_percent(metrics: Mapping[str, Any]) -> float | None:
    """فقط DD درصدی صریح و متکی بر مبنای سرمایهٔ واقعی/تعریف‌شده معتبر است."""
    explicit = metrics.get("max_dd_percent")
    if explicit is None:
        return None
    try:
        value = float(explicit)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value >= 0 else None


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

    # P1 #6: پوشش R
    r_valid_count = metrics.get("r_valid_count")
    r_coverage_raw = metrics.get("r_coverage_percent")
    r_coverage = _as_float(r_coverage_raw, 0.0)
    r_metadata_available = r_valid_count is not None or r_coverage_raw is not None
    if r_coverage_raw is None and r_valid_count is not None:
        r_coverage = (
            _as_float(r_valid_count, 0.0) / max(n, 1) * 100.0
        )
    r_coverage = min(max(r_coverage, 0.0), 100.0)
    r_penalty = 0.0
    if r_metadata_available and r_coverage < 70:
        r_penalty = (70 - r_coverage) / 70 * 15  # حداکثر ۱۵ نمره
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
    r_eligible = r_metadata_available and _as_float(r_valid_count, 1.0) > 0 and r_coverage >= 70
    expectancy_score = (
        min(max(expectancy_r / 1.0, 0.0), 1.0) * 100.0 if r_eligible else 50.0
    )

    # ب) Win Rate (وزن کمتر)
    win_rate = _as_float(metrics.get("win_rate"), 0.0)
    win_rate_score = min(max(win_rate, 0.0), 100.0)

    # ج) Profit Factor (سقف ۵)
    pf_status = metrics.get("profit_factor_status")
    pf_value = metrics.get("profit_factor")
    if pf_status is None:
        # No metadata means unknown; numeric 100/999 may be genuine finite ratios.
        pf_status = "finite" if pf_value is not None else (
            "unavailable" if metrics.get("total_trades") else "no_usable_pnl"
        )
    if pf_status == "finite":
        pf_score = min(max(_as_float(pf_value, 0.0) / 5.0 * 100.0, 0.0), 100.0)
    elif pf_status == "no_losses":
        pf_score = 100.0
    elif pf_status == "unavailable":
        pf_score = 50.0
    elif pf_status == "no_usable_pnl":
        pf_score = 0.0
    else:
        pf_score = 0.0

    # د) Drawdown درصدی (کمتر بهتر): 0% ⇒ 100 ، 20% ⇒ 0
    dd_percent = _dd_percent(metrics)
    dd_available = dd_percent is not None
    dd_score = min(max(100.0 - dd_percent * 5.0, 0.0), 100.0) if dd_available else 50.0

    score = (
        expectancy_score * W_EXPECTANCY
        + win_rate_score * W_WIN_RATE
        + pf_score * W_PROFIT_FACTOR
        + dd_score * W_DRAWDOWN
    ) - sample_penalty - r_penalty
    score = max(0.0, min(score, 100.0))

    # ── ۳. هشدارها ──
    warnings: List[str] = []
    if n < SAMPLE_ENOUGH:
        warnings.append(f"نمونه کم: {n} معامله (حداقل {SAMPLE_ENOUGH})")
    if r_metadata_available and r_coverage < 70:
        warnings.append(f"پوشش R کمتر از ۷۰٪ (فقط {r_coverage:.0f}٪)")
    if dd_available and dd_percent > 15:
        warnings.append(f"Drawdown بالا: {dd_percent:.1f}%")
    if r_eligible and expectancy_r < 0.2:
        warnings.append(f"Expectancy ضعیف: {expectancy_r:.2f}R")

    return {
        "score": round(score, 2),
        "sample_status": sample_status,
        "warnings": warnings,
        "components": {
            "expectancy_score": round(expectancy_score, 2),
            "win_rate_score": round(win_rate_score, 2),
            "pf_score": round(pf_score, 2),
            "pf_status": pf_status,
            "dd_score": round(dd_score, 2),
            "sample_penalty": sample_penalty,
            "r_penalty": round(r_penalty, 2),
            "r_penalty_exact": round(r_penalty, 8),
            "r_eligible": r_eligible,
            "dd_available": dd_available,
            "dd_fallback": not dd_available,
            "r_fallback": not r_eligible,
            "r_valid_count": _as_float(r_valid_count, 0.0) if r_valid_count is not None else None,
            "r_coverage_percent": round(r_coverage, 2) if r_metadata_available else None,
            "r_metadata_available": r_metadata_available,
            "r_measure": "gross_price_r",
        },
    }
