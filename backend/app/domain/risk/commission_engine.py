"""Commission calculations for risk and trade-cost estimates."""


def calculate_round_trip_commission(
    volume: float,
    commission_one_side: float,
) -> float:
    """Calculate round-trip commission as volume × one-side commission × 2."""
    return volume * commission_one_side * 2