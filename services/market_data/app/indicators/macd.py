from __future__ import annotations

from typing import Iterable, Tuple, List

import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_macd_12_26_9(close: Iterable[float]) -> Tuple[pd.Series, pd.Series, pd.Series, List[str]]:
    """Compute MACD(12,26,9).

    Returns macd_line, signal_line, histogram, and signal labels per row:
    - 'bullish' when histogram > 0
    - 'bearish' when histogram < 0
    - 'neutral' when histogram == 0 or NaN
    """
    close_series = pd.Series(close, dtype=float)
    ema12 = _ema(close_series, 12)
    ema26 = _ema(close_series, 26)
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line

    def label(value: float) -> str:
        if pd.isna(value) or value == 0:
            return "neutral"
        return "bullish" if value > 0 else "bearish"

    signal = [label(v) for v in histogram.tolist()]
    return macd_line, signal_line, histogram, signal



