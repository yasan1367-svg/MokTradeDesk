import pytest

from app.domain.risk.position_sizing import calculate_position_size


def _size(**overrides):
    params = {
        "account_equity": 5000.0,
        "risk_percent": 1.0,
        "sl_distance": 20.0,
        "value_per_price_unit": 10.0,
        "commission_one_side": 0.0,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "lot_step": 0.001,
    }
    params.update(overrides)
    return calculate_position_size(**params)


def test_eurusd_1pct_20pip():
    result = _size()

    assert result["volume"] == pytest.approx(0.25)
    assert result["risk_budget"] == pytest.approx(50.0)
    assert result["price_risk"] == pytest.approx(50.0)
    assert result["commission"] == pytest.approx(0.0)
    assert result["total_risk"] == pytest.approx(50.0)
    assert result["reason"] == "ok"


def test_eurusd_1pct_40pip():
    result = _size(sl_distance=40.0)

    assert result["volume"] == pytest.approx(0.125)
    assert result["volume"] == pytest.approx(_size()["volume"] / 2)


def test_xauusd_0_5pct_5dollar():
    result = _size(
        account_equity=5000.0,
        risk_percent=0.5,
        sl_distance=5.0,
        value_per_price_unit=1.0,
    )

    assert result["risk_budget"] == pytest.approx(25.0)
    assert result["volume"] == pytest.approx(5.0)
    assert result["price_risk"] == pytest.approx(25.0)


def test_dji30_commission():
    result = _size(
        account_equity=10000.0,
        risk_percent=1.0,
        sl_distance=10.0,
        value_per_price_unit=1.0,
        commission_one_side=2.0,
        lot_step=0.01,
    )

    assert result["volume"] == pytest.approx(7.14)
    assert result["price_risk"] == pytest.approx(71.4)
    assert result["commission"] == pytest.approx(28.56)
    assert result["total_risk"] == pytest.approx(99.96)
    assert result["total_risk"] <= result["risk_budget"]


def test_min_lot_exceeds_risk():
    result = _size(
        account_equity=100.0,
        risk_percent=1.0,
        sl_distance=10.0,
        value_per_price_unit=10.0,
        min_lot=0.1,
    )

    assert result["volume"] == 0
    assert result["reason"] == "min_lot_exceeds_risk_budget"
    assert result["min_lot_risk"] == pytest.approx(10.0)
    assert result["risk_budget"] == pytest.approx(1.0)


def test_lot_step_round_down():
    result = _size(
        account_equity=1000.0,
        risk_percent=1.0,
        sl_distance=3.0,
        value_per_price_unit=10.0,
        lot_step=0.1,
    )

    assert result["volume"] == pytest.approx(0.3)
    assert result["total_risk"] <= result["risk_budget"]


def test_max_lot():
    result = _size(
        account_equity=100000.0,
        risk_percent=10.0,
        sl_distance=1.0,
        value_per_price_unit=1.0,
        max_lot=5.0,
    )

    assert result["volume"] == pytest.approx(5.0)
    assert result["reason"] == "ok"


def test_invalid_lot_step_is_rejected():
    result = _size(lot_step=0.0)

    assert result["volume"] == 0
    assert result["reason"] == "invalid_risk"
    assert result["risk_budget"] == pytest.approx(50.0)