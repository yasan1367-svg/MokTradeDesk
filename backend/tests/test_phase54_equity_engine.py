from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.domain.risk.equity_engine import (
    calculate_equity_curve,
    calculate_equity_with_floating,
)


def _trade(close_time, pnl, *, commission=0.0, swap=0.0, is_deleted=False):
    return SimpleNamespace(
        close_time=close_time,
        pnl=pnl,
        commission=commission,
        swap=swap,
        is_deleted=is_deleted,
    )


def _date(day):
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def test_equity_from_initial_10000():
    curve = calculate_equity_curve(
        10000.0,
        [_trade(_date(2), 100.0), _trade(_date(1), 50.0)],
    )

    assert curve == [
        {"date": None, "balance": 10000.0, "equity": 10000.0, "pnl": 0},
        {"date": _date(1), "balance": 10050.0, "equity": 10050.0, "pnl": 50.0},
        {"date": _date(2), "balance": 10150.0, "equity": 10150.0, "pnl": 100.0},
    ]


def test_equity_10000_100_50_not_50_percent_drawdown():
    curve = calculate_equity_curve(
        10000.0,
        [_trade(_date(1), 100.0), _trade(_date(2), -50.0)],
    )

    assert [point["balance"] for point in curve] == [10000.0, 10100.0, 10050.0]
    assert curve[-1]["equity"] == pytest.approx(10050.0)
    assert curve[-1]["equity"] / 10000.0 * 100 == pytest.approx(100.5)


def test_equity_with_floating():
    curve = calculate_equity_with_floating(
        10000.0,
        [_trade(_date(1), 100.0, commission=-2.0)],
        [
            _trade(None, 40.0, commission=-1.0, swap=-2.0),
            _trade(None, -10.0),
        ],
    )

    assert curve[-1]["balance"] == pytest.approx(10098.0)
    assert curve[-1]["floating_pnl"] == pytest.approx(27.0)
    assert curve[-1]["equity"] == pytest.approx(10125.0)


def test_equity_negative_pnl():
    curve = calculate_equity_curve(10000.0, [_trade(_date(1), -250.0)])

    assert curve[-1]["balance"] == pytest.approx(9750.0)
    assert curve[-1]["equity"] == pytest.approx(9750.0)
    assert curve[-1]["pnl"] == pytest.approx(-250.0)


def test_equity_soft_deleted_excluded():
    curve = calculate_equity_with_floating(
        10000.0,
        [
            _trade(_date(1), 100.0),
            _trade(_date(2), 900.0, is_deleted=True),
        ],
        [
            _trade(None, 50.0),
            _trade(None, 500.0, is_deleted=True),
        ],
    )

    assert len(curve) == 2
    assert curve[-1]["balance"] == pytest.approx(10100.0)
    assert curve[-1]["floating_pnl"] == pytest.approx(50.0)
    assert curve[-1]["equity"] == pytest.approx(10150.0)