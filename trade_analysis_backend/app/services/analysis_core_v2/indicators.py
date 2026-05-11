import math


def calc_ema(values: list[float], length: int) -> list[float | None]:
    """计算 EMA 序列，前 length-1 根返回 None。"""
    result: list[float | None] = [None] * len(values)
    valid_indices = [i for i, v in enumerate(values) if v is not None and not math.isnan(v)]
    if len(valid_indices) < length:
        return result

    start = valid_indices[length - 1]
    sma = sum(values[i] for i in range(valid_indices[0], start + 1) if values[i] is not None and not math.isnan(values[i])) / length  # type: ignore[arg-type]
    result[start] = sma

    multiplier = 2 / (length + 1)
    for i in range(start + 1, len(values)):
        v = values[i]
        if v is not None and not math.isnan(v):
            result[i] = (v - result[i - 1]) * multiplier + result[i - 1]  # type: ignore[operator]
        else:
            result[i] = result[i - 1]

    return result


def calc_macd(
    closes: list[float],
    short: int = 4,
    long: int = 20,
    mid: int = 20,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """返回 (diff, dea, histogram) 三线，前 long+mid-2 根为 None。"""
    ema_short = calc_ema(closes, short)
    ema_long = calc_ema(closes, long)

    diff: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if ema_short[i] is not None and ema_long[i] is not None:
            diff[i] = ema_short[i] - ema_long[i]  # type: ignore[operator]

    dea = calc_ema([d if d is not None else float("nan") for d in diff], mid)
    # 修正中间标记：把原序列中 None 的位置映射回 None
    dea = [v if diff[i] is not None else None for i, v in enumerate(dea)]

    histogram: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if diff[i] is not None and dea[i] is not None:
            histogram[i] = diff[i] - dea[i]  # type: ignore[operator]

    return diff, dea, histogram
