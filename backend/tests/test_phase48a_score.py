"""تست‌های Phase 48a.4 — Score (`app/services/version_score.py`) — به‌روزشده در فاز ۵۲.

فرمول فاز ۵۲ (خروجی dict):
    expectancy_score = clamp(expectancy_r, 0..1) * 100      وزن ۴۰٪
    win_rate_score   = clamp(win_rate, 0..100)              وزن ۲۰٪
    pf_score         = clamp(profit_factor / 5 * 100, 0..100) وزن ۲۰٪
    dd_score         = clamp(100 - dd_percent * 5, 0..100)  وزن ۲۰٪
    score            = (Σ وزن‌دار) − sample_penalty          کلمپ ۰..۱۰۰
"""
from app.services.version_score import calculate_version_score


def _m(**kw):
    """متریک پایه با نمونهٔ کافی (n=50) — قابل بازنویسی با kw."""
    base = {
        "total_trades": 50,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "expectancy_r": 0.0,
        "max_dd": 0.0,
    }
    base.update(kw)
    return base


def test_score_perfect_metrics():
    """متریک‌های ایدئال ⇒ امتیاز ۱۰۰ و نمونهٔ کافی."""
    r = calculate_version_score(_m(
        win_rate=100.0,
        profit_factor=5.0,
        expectancy_r=1.0,
        max_dd=0.0,
    ))
    assert r["score"] == 100.0
    assert r["sample_status"] == "کافی"
    assert r["warnings"] == []


def test_score_zero_metrics():
    """متریک خالی ⇒ امتیاز ۰ (جریمهٔ نمونهٔ ۳۰ آن را صفر می‌کند).

    توجه: نسخهٔ با نمونهٔ کافی ولی بدون هیچ برد/باخت (و بدون Drawdown)
    فقط پاداش نبودِ Drawdown را می‌گیرد = ۲۰.
    """
    r = calculate_version_score({})
    assert r["score"] == 0.0
    assert r["sample_status"] == "خیلی کم"

    r2 = calculate_version_score({
        "total_trades": 50,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "expectancy_r": 0.0,
        "max_dd": 0.0,
    })
    assert r2["score"] == 20.0


def test_score_with_high_dd_penalty():
    """افت سرمایه زیاد باید امتیاز را پایین بیاورد (بدون افت = ۵۴)."""
    base = dict(win_rate=50.0, profit_factor=1.0, expectancy_r=0.5)
    # exp .5→20 ، wr 50→10 ، pf 1→4 ، dd 0→20  ⇒ 54
    no_dd = calculate_version_score(_m(**base, max_dd=0.0))["score"]
    assert no_dd == 54.0

    # max_dd=2000 ⇒ dd_percent=20 ⇒ dd_score=0 ⇒ 54 − 20 = 34
    high_dd = calculate_version_score(_m(**base, max_dd=2000.0))["score"]
    assert high_dd == 34.0
    assert high_dd < no_dd


def test_score_is_clamped_between_0_and_100():
    """امتیاز هرگز از بازهٔ ۰..۱۰۰ بیرون نمی‌زند."""
    assert calculate_version_score(_m(
        win_rate=999.0,
        profit_factor=99.0,
        expectancy_r=999.0,
        max_dd=0.0,
    ))["score"] == 100.0

    assert calculate_version_score(_m(
        win_rate=-50.0,
        profit_factor=-3.0,
        expectancy_r=-5.0,
        max_dd=10_000.0,
    ))["score"] == 0.0

