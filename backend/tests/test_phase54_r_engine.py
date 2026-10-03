import pytest

from app.domain.risk.r_engine import (
    calculate_expectancy_r,
    calculate_r_distribution,
    calculate_r_multiple,
)


def test_r_buy_win():
    assert calculate_r_multiple("buy", 100.0, 120.0, 90.0) == pytest.approx(2.0)


def test_r_buy_loss():
    assert calculate_r_multiple("buy", 100.0, 90.0, 90.0) == pytest.approx(-1.0)


def test_r_sell_win():
    assert calculate_r_multiple("sell", 100.0, 85.0, 110.0) == pytest.approx(1.5)


def test_r_sell_loss():
    assert calculate_r_multiple("sell", 100.0, 110.0, 110.0) == pytest.approx(-1.0)


def test_r_zero_kept():
    assert calculate_r_multiple("buy", 100.0, 100.0, 90.0) == 0.0
    assert calculate_expectancy_r([1.0, 0.0, -1.0]) == pytest.approx(0.0)


def test_r_missing_none():
    assert calculate_expectancy_r([1.0, None, -1.0]) == pytest.approx(0.0)
    distribution = calculate_r_distribution([0.0, None])
    assert sum(bucket["count"] for bucket in distribution) == 1
    assert distribution[3] == {"range": "0..1R", "count": 1}


def test_r_invalid_sl():
    assert calculate_r_multiple("buy", 100.0, 110.0, 100.0) is None
    assert calculate_r_multiple("sell", 100.0, 90.0, 100.0) is None
    assert calculate_r_multiple("hold", 100.0, 110.0, 90.0) is None


def test_expectancy_r():
    assert calculate_expectancy_r([2.0, -1.0, 0.5, None]) == pytest.approx(0.5)
    assert calculate_expectancy_r([None, None]) == 0.0


def test_r_distribution():
    distribution = calculate_r_distribution([-2.5, -1.5, -0.5, 0.0, 1.5, 2.5, 3.0, None])

    assert distribution == [
        {"range": "< -2R", "count": 1},
        {"range": "-2..-1R", "count": 1},
        {"range": "-1..0R", "count": 1},
        {"range": "0..1R", "count": 1},
        {"range": "1..2R", "count": 1},
        {"range": "2..3R", "count": 1},
        {"range": "> 3R", "count": 1},
    ]


def test_r_distribution_boundaries():
    distribution = calculate_r_distribution([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0])

    assert [bucket["count"] for bucket in distribution] == [0, 1, 1, 1, 1, 1, 1]


def test_r_distribution_empty():
    assert calculate_r_distribution([None]) == [
        {"range": label, "count": 0}
        for label in ["< -2R", "-2..-1R", "-1..0R", "0..1R", "1..2R", "2..3R", "> 3R"]
    ]