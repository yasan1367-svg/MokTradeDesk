from app.domain.risk.commission_engine import calculate_round_trip_commission


def test_commission_zero():
    assert calculate_round_trip_commission(volume=1.0, commission_one_side=0.0) == 0.0


def test_commission_round_trip():
    assert calculate_round_trip_commission(volume=2.5, commission_one_side=3.0) == 15.0