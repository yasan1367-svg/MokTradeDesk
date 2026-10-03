from datetime import datetime, timedelta, timezone

import pytest

from app.domain.risk.drawdown_engine import (
    calculate_drawdown_duration,
    calculate_peak_to_trough_dd,
    calculate_static_dd,
)


def _point(day, equity):
    return {"date": datetime(2026, 1, day, tzinfo=timezone.utc), "equity": equity}


def test_static_dd():
    curve = [{"date": None, "equity": 10000.0}, _point(1, 10500.0), _point(2, 9200.0)]

    assert calculate_static_dd(10000.0, curve) == {
        "dd": 800.0,
        "dd_percent": 8.0,
        "min_equity": 9200.0,
    }


def test_peak_to_trough_dd():
    curve = [
        {"date": None, "equity": 10000.0},
        _point(1, 12000.0),
        _point(2, 9000.0),
        _point(3, 11000.0),
        _point(4, 8000.0),
    ]

    assert calculate_peak_to_trough_dd(curve) == {
        "dd": 4000.0,
        "dd_percent": pytest.approx(33.3333333333),
        "peak": 12000.0,
    }


def test_drawdown_duration_days():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    curve = [
        {"date": None, "equity": 10000.0},
        {"date": start, "equity": 11000.0},
        {"date": start + timedelta(days=1), "equity": 10500.0},
        {"date": start + timedelta(days=4), "equity": 10800.0},
        {"date": start + timedelta(days=6), "equity": 11000.0},
    ]

    result = calculate_drawdown_duration(curve)
    assert result["duration_days"] == pytest.approx(5.0)
    assert result["start_date"] == start + timedelta(days=1)
    assert result["end_date"] == start + timedelta(days=6)


def test_unrecovered_drawdown_duration():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    curve = [
        {"date": None, "equity": 10000.0},
        {"date": start, "equity": 10000.0},
        {"date": start + timedelta(days=2), "equity": 9500.0},
        {"date": start + timedelta(days=5), "equity": 9200.0},
    ]

    result = calculate_drawdown_duration(curve)
    assert result["duration_days"] == pytest.approx(3.0)
    assert result["start_date"] == start + timedelta(days=2)
    assert result["end_date"] == start + timedelta(days=5)


def test_empty_drawdown_inputs():
    assert calculate_static_dd(10000.0, []) == {
        "dd": 0.0,
        "dd_percent": 0.0,
        "min_equity": 10000.0,
    }
    assert calculate_peak_to_trough_dd([]) == {"dd": 0.0, "dd_percent": 0.0, "peak": 0.0}
    assert calculate_drawdown_duration([]) == {
        "duration_days": 0.0,
        "start_date": None,
        "end_date": None,
    }