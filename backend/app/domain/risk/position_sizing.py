"""Position sizing calculations constrained by a per-trade risk budget."""

import math


def calculate_position_size(
    account_equity: float,
    risk_percent: float,
    sl_distance: float,
    value_per_price_unit: float,
    commission_one_side: float,
    min_lot: float,
    max_lot: float,
    lot_step: float,
) -> dict:
    """Calculate a lot size whose price risk and round-trip commission fit the budget."""
    risk_budget = account_equity * (risk_percent / 100)
    commission_per_lot = commission_one_side * 2
    denominator = sl_distance * value_per_price_unit + commission_per_lot

    if denominator <= 0 or lot_step <= 0:
        return {"volume": 0, "reason": "invalid_risk", "risk_budget": risk_budget}

    raw_volume = risk_budget / denominator
    # nextafter corrects a one-ULP downward representation (e.g. 0.3 / 0.1)
    # without materially rounding a genuinely smaller lot up to the next step.
    volume = math.floor(math.nextafter(raw_volume / lot_step, math.inf)) * lot_step

    if volume < min_lot:
        min_risk = min_lot * denominator
        if min_risk > risk_budget:
            return {
                "volume": 0,
                "reason": "min_lot_exceeds_risk_budget",
                "min_lot_risk": min_risk,
                "risk_budget": risk_budget,
            }
        volume = min_lot

    if volume > max_lot:
        volume = max_lot

    price_risk = sl_distance * value_per_price_unit * volume
    commission = commission_per_lot * volume
    total_risk = price_risk + commission

    return {
        "volume": volume,
        "risk_budget": risk_budget,
        "price_risk": price_risk,
        "commission": commission,
        "total_risk": total_risk,
        "reason": "ok",
    }