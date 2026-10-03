"""R-multiple and R-distribution calculations for closed trades."""


def calculate_r_multiple(
    direction: str,
    open_price: float,
    close_price: float,
    sl_price: float,
) -> float | None:
    """Calculate realized reward divided by initial stop risk, if the stop is valid."""
    if direction == "buy":
        risk = open_price - sl_price
        reward = close_price - open_price
    elif direction == "sell":
        risk = sl_price - open_price
        reward = open_price - close_price
    else:
        return None

    if risk <= 0:
        return None

    return reward / risk


def calculate_expectancy_r(r_multiples: list[float | None]) -> float:
    """Return the arithmetic mean of valid R values; zero-R trades are included."""
    valid = [r for r in r_multiples if r is not None]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def calculate_r_distribution(r_multiples: list[float | None]) -> list[dict]:
    """Bucket valid R values into the seven ranges used by the analytics charts.

    Buckets are lower-inclusive and upper-exclusive. Thus 0R is kept in ``0..1R``;
    the final ``> 3R`` bucket includes values equal to 3R so every value is counted.
    """
    ranges = ["< -2R", "-2..-1R", "-1..0R", "0..1R", "1..2R", "2..3R", "> 3R"]
    counts = [0] * len(ranges)

    for value in r_multiples:
        if value is None:
            continue
        if value < -2:
            index = 0
        elif value < -1:
            index = 1
        elif value < 0:
            index = 2
        elif value < 1:
            index = 3
        elif value < 2:
            index = 4
        elif value < 3:
            index = 5
        else:
            index = 6
        counts[index] += 1

    return [{"range": label, "count": count} for label, count in zip(ranges, counts)]