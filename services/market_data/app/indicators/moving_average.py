from __future__ import annotations

from typing import Iterable, Tuple, List

import pandas as pd


def compute_ma20_ma60_and_trend(close: Iterable[float]) -> Tuple[pd.Series, pd.Series, List[str]]:
    """Compute MA20 and MA60 using simple moving average, and determine MA20 trend.

    Trend rules:
    - 'up' if current MA20 > MA20 from previous period by a small epsilon
    - 'down' if current MA20 < previous MA20 by epsilon
    - 'flat' otherwise
    """
    close_series = pd.Series(close, dtype=float)
    ma20 = close_series.rolling(window=20, min_periods=1).mean()
    ma60 = close_series.rolling(window=60, min_periods=1).mean()
    prev_ma20 = ma20.shift(1)
    epsilon = 1e-8

    def trend(curr: float, prev: float) -> str:
        if pd.isna(curr) or pd.isna(prev):
            return "flat"
        if curr > prev + epsilon:
            return "up"
        if curr < prev - epsilon:
            return "down"
        return "flat"

    trend_list: List[str] = [trend(c, p) for c, p in zip(ma20.tolist(), prev_ma20.tolist())]
    return ma20, ma60, trend_list



