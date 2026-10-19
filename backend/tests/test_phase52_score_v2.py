"""تست‌های فاز ۵۲ — Score جدید Versionها (`app/services/version_score.py`).

فرمول (خروجی dict):
    expectancy_score = clamp(expectancy_r, 0..1) * 100       وزن ۴۰٪
    win_rate_score   = clamp(win_rate, 0..100)               وزن ۲۰٪
    pf_score         = clamp(profit_factor / 5 * 100, ..100) وزن ۲۰٪
    dd_score         = clamp(100 - dd_percent * 5, 0..100)   وزن ۲۰٪
    score            = (Σ وزن‌دار) − sample_penalty           کلمپ ۰..۱۰۰

DD فقط با `max_dd_percent` صریح امتیازدهی می‌شود؛ مقدار پولی بدون سرمایهٔ مبنا کافی نیست.
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
        "max_dd_percent": 0.0,
        "r_valid_count": 50,
        "r_coverage_percent": 100.0,
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
        win_rate=100.0, profit_factor=5.0, expectancy_r=1.0, max_dd_percent=20.0,
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
    r = calculate_version_score(_m(max_dd_percent=30.0))
    assert any("Drawdown بالا" in w for w in r["warnings"])


def test_warnings_low_expectancy():
    r = calculate_version_score(_m(expectancy_r=0.1))
    assert any("Expectancy ضعیف" in w for w in r["warnings"])


def test_score_clamped_0_100():
    """امتیاز همیشه در بازهٔ ۰..۱۰۰ می‌ماند."""
    extreme_high = calculate_version_score(_m(
        win_rate=999.0, profit_factor=99.0, expectancy_r=999.0, max_dd_percent=0.0,
    ))["score"]
    extreme_low = calculate_version_score(_m(
        total_trades=0, win_rate=-99.0, profit_factor=-9.0,
        expectancy_r=-9.0, max_dd_percent=100.0,
    ))["score"]
    assert extreme_high == 100.0
    assert extreme_low == 0.0
    assert 0.0 <= extreme_high <= 100.0
    assert 0.0 <= extreme_low <= 100.0


def test_missing_dd_basis_is_neutral_not_assumed_percent():
    data = _m(max_dd=2000.0)
    data.pop("max_dd_percent")
    r = calculate_version_score(data)
    assert r["components"]["dd_score"] == 50.0
    assert r["components"]["dd_available"] is False
    assert not any("Drawdown بالا" in warning for warning in r["warnings"])


def test_invalid_dd_values_are_unavailable_and_neutral():
    for value in ("bad", float("nan"), float("inf"), float("-inf"), -0.01):
        result = calculate_version_score(_m(max_dd_percent=value))
        assert result["components"]["dd_available"] is False
        assert result["components"]["dd_fallback"] is True
        assert result["components"]["dd_score"] == 50.0


def test_zero_dd_is_available_and_scores_full_points():
    result = calculate_version_score(_m(max_dd_percent=0))
    assert result["components"]["dd_available"] is True
    assert result["components"]["dd_score"] == 100.0


def test_missing_r_is_neutral_not_bad_performance():
    r = calculate_version_score(_m(expectancy_r=None, r_valid_count=None, r_coverage_percent=None))
    assert r["components"]["r_eligible"] is False
    assert r["components"]["expectancy_score"] == 50.0
    assert r["components"]["r_penalty"] == 0.0
    assert not any("Expectancy ضعیف" in warning for warning in r["warnings"])


def test_partial_r_coverage_disqualifies_expectancy_and_penalizes_coverage():
    r = calculate_version_score(_m(expectancy_r=1.0, r_valid_count=10, r_coverage_percent=20.0))
    assert r["components"]["r_eligible"] is False
    assert r["components"]["expectancy_score"] == 50.0
    assert r["components"]["r_penalty"] == 10.71
    assert any("پوشش R" in warning for warning in r["warnings"])


def test_r_valid_count_can_supply_coverage_when_percent_is_absent():
    r = calculate_version_score(_m(r_valid_count=50, r_coverage_percent=None))
    assert r["components"]["r_eligible"] is True


def test_r_coverage_threshold_and_penalty_boundaries():
    below = calculate_version_score(_m(r_valid_count=50, r_coverage_percent=69.99))
    at = calculate_version_score(_m(r_coverage_percent=70.0))
    absent_count = calculate_version_score(_m(r_valid_count=0, r_coverage_percent=100.0))
    assert below["components"]["r_eligible"] is False
    assert below["components"]["r_penalty_exact"] > 0
    assert below["components"]["r_coverage_percent"] == 69.99
    assert at["components"]["r_eligible"] is True
    assert at["components"]["r_penalty"] == 0.0
    assert absent_count["components"]["r_eligible"] is False
    assert absent_count["components"]["r_fallback"] is True


def test_profit_factor_status_scoring_does_not_trust_legacy_sentinels():
    without_losses = calculate_version_score(_m(profit_factor=999, profit_factor_status="no_losses"))
    legacy_numeric_only = calculate_version_score(_m(profit_factor=999))
    no_pnl = calculate_version_score(_m(profit_factor=None, profit_factor_status="no_usable_pnl"))
    finite_999 = calculate_version_score(_m(profit_factor=999, profit_factor_status="finite"))
    assert without_losses["components"]["pf_score"] == 100
    assert legacy_numeric_only["components"]["pf_score"] == 100
    assert no_pnl["components"]["pf_score"] == 0
    assert finite_999["components"]["pf_score"] == 100


def test_legacy_finite_pf_two_is_not_no_losses_or_zero():
    score = calculate_version_score(_m(profit_factor=2.0))
    assert score["components"]["pf_status"] == "finite"
    assert score["components"]["pf_score"] == 40.0


def test_unknown_pf_without_numeric_value_is_explicit_and_neutral():
    score = calculate_version_score(_m(profit_factor=None, profit_factor_status="unavailable"))
    assert score["components"]["pf_status"] == "unavailable"
    assert score["components"]["pf_score"] == 50.0
