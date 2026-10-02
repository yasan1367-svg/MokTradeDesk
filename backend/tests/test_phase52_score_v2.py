"""تست‌های فاز ۵۲ — Score جدید Versionها (`app/services/version_score.py`).

فرمول (خروجی dict):
    expectancy_score = clamp(expectancy_r, 0..1) * 100       وزن ۴۰٪
    win_rate_score   = clamp(win_rate, 0..100)               وزن ۲۰٪
    pf_score         = clamp(profit_factor / 5 * 100, ..100) وزن ۲۰٪
    dd_score         = clamp(100 - dd_percent * 5, 0..100)   وزن ۲۰٪
    score            = (Σ وزن‌دار) − sample_penalty           کلمپ ۰..۱۰۰

`dd_percent = max_dd / ASSUMED_ACCOUNT_SIZE (10000) * 100` (اگر max_dd_percent نباشد).
"""
from app.services.version_score import calculate_version_score


def _m(**kw):
    """متریک پایه با نمونهٔ کافی (n=50)."""
    base = {
        "total_trades": 50,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "expectancy_r": 0.0,
        "max_dd": 0.0,
    }
    base.update(kw)
    return base


def test_score_v2_perfect_metrics():
    """متریک ایدئال + نمونهٔ کافی ⇒ ۱۰۰ بدون هشدار."""
    r = calculate_version_score(_m(
        win_rate=100.0, profit_factor=5.0, expectancy_r=1.0, max_dd=0.0,
    ))
    assert r["score"] == 100.0
    assert r["sample_status"] == "کافی"
    assert r["warnings"] == []
    assert r["components"]["sample_penalty"] == 0.0


def test_score_v2_low_sample_penalty():
    """نمونهٔ ناکافی (۱۵) ⇒ ۱۵ امتیاز جریمه و وضعیت «ناکافی»."""
    r = calculate_version_score(_m(
        total_trades=15, win_rate=100.0, profit_factor=5.0, expectancy_r=1.0, max_dd=0.0,
    ))
    # بدنهٔ کامل = 100 ⇒ منهای جریمهٔ ۱۵
    assert r["score"] == 85.0
    assert r["sample_status"] == "ناکافی"
    assert r["components"]["sample_penalty"] == 15.0
    assert any("نمونه کم" in w for w in r["warnings"])


def test_score_v2_high_dd_penalty():
    """Drawdown ۲۰٪ (2000/10000) ⇒ dd_score صفر و افت ۲۰ امتیازی."""
    r = calculate_version_score(_m(
        win_rate=100.0, profit_factor=5.0, expectancy_r=1.0, max_dd=2000.0,
    ))
    assert r["components"]["dd_score"] == 0.0
    assert r["score"] == 80.0
    assert any("Drawdown بالا" in w for w in r["warnings"])


def test_score_v2_expectancy_priority():
    """Expectancy (وزن ۴۰٪) باید بر Win Rate (وزن ۲۰٪) اولویت داشته باشد."""
    high_expectancy = calculate_version_score(_m(
        win_rate=50.0, profit_factor=1.0, expectancy_r=1.0, max_dd=0.0,
    ))["score"]  # 40 + 10 + 4 + 20 = 74
    high_win_rate = calculate_version_score(_m(
        win_rate=100.0, profit_factor=1.0, expectancy_r=0.1, max_dd=0.0,
    ))["score"]  # 4 + 20 + 4 + 20 = 48
    assert high_expectancy == 74.0
    assert high_expectancy > high_win_rate


def test_sample_status_very_low():
    assert calculate_version_score(_m(total_trades=5))["sample_status"] == "خیلی کم"


def test_sample_status_low():
    assert calculate_version_score(_m(total_trades=20))["sample_status"] == "ناکافی"


def test_sample_status_enough():
    assert calculate_version_score(_m(total_trades=30))["sample_status"] == "کافی"


def test_warnings_high_dd():
    r = calculate_version_score(_m(max_dd=3000.0))  # 30% ⇒ هشدار
    assert any("Drawdown بالا" in w for w in r["warnings"])


def test_warnings_low_expectancy():
    r = calculate_version_score(_m(expectancy_r=0.1))
    assert any("Expectancy ضعیف" in w for w in r["warnings"])


def test_score_clamped_0_100():
    """امتیاز همیشه در بازهٔ ۰..۱۰۰ می‌ماند."""
    extreme_high = calculate_version_score(_m(
        win_rate=999.0, profit_factor=99.0, expectancy_r=999.0, max_dd=0.0,
    ))["score"]
    extreme_low = calculate_version_score(_m(
        total_trades=0, win_rate=-99.0, profit_factor=-9.0,
        expectancy_r=-9.0, max_dd=1_000_000.0,
    ))["score"]
    assert extreme_high == 100.0
    assert extreme_low == 0.0
    assert 0.0 <= extreme_high <= 100.0
    assert 0.0 <= extreme_low <= 100.0
