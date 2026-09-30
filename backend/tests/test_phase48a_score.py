"""تست‌های Phase 48a.4 — Score ساده (`app/services/version_score.py`).

فرمول:
    win_score  = min(win_rate, 100)
    pf_score   = min(profit_factor * 20, 100)
    pnl_score  = min(max(net_pnl / 10, 0), 100)
    dd_penalty = min(max_dd / 10, 50)
    score      = win*0.35 + pf*0.35 + pnl*0.30 − dd*0.20   (کلمپ 0..100)
"""
from app.services.version_score import calculate_version_score


def test_score_perfect_metrics():
    """متریک‌های ایدئال ⇒ امتیاز ۱۰۰."""
    score = calculate_version_score({
        "win_rate": 100.0,
        "profit_factor": 5.0,
        "net_pnl": 1000.0,
        "max_dd": 0.0,
    })
    assert score == 100.0


def test_score_zero_metrics():
    """همه‌چیز صفر ⇒ امتیاز ۰."""
    assert calculate_version_score({}) == 0.0
    assert calculate_version_score({
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "net_pnl": 0.0,
        "max_dd": 0.0,
    }) == 0.0


def test_score_with_high_dd_penalty():
    """افت سرمایه زیاد باید امتیاز را پایین بیاورد (بدون افت = ۲۷.۵)."""
    base = {
        "win_rate": 50.0,
        "profit_factor": 1.0,
        "net_pnl": 100.0,
    }
    # win 50→17.5 ، pf 1→20→7 ، pnl 100→10→3  ⇒ 27.5
    assert calculate_version_score({**base, "max_dd": 0.0}) == 27.5

    # max_dd=500 ⇒ dd_penalty = min(50, 50) = 50 ⇒ 27.5 − 10 = 17.5
    high_dd = calculate_version_score({**base, "max_dd": 500.0})
    assert high_dd == 17.5
    assert high_dd < calculate_version_score({**base, "max_dd": 0.0})


def test_score_is_clamped_between_0_and_100():
    """امتیاز هرگز از بازهٔ ۰..۱۰۰ بیرون نمی‌زند."""
    assert calculate_version_score({
        "win_rate": 999.0,
        "profit_factor": 99.0,
        "net_pnl": 10_000_000.0,
        "max_dd": 0.0,
    }) == 100.0

    assert calculate_version_score({
        "win_rate": -50.0,
        "profit_factor": -3.0,
        "net_pnl": -5000.0,
        "max_dd": 10_000.0,
    }) == 0.0
