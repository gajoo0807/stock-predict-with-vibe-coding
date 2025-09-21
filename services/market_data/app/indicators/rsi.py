from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def compute_rsi14(close: Iterable[float]) -> pd.Series:
    """Compute RSI(14) for a close price series.

    Uses Wilder's smoothing method.
    Returns a pandas Series aligned with input.
    """
    close_series = pd.Series(close, dtype=float)
    delta = close_series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    window = 14
    # Wilder's smoothing: use exponential weighted with alpha=1/window, adjust=False
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()

    # Compute RS; handle zero-loss (no down moves) -> RSI should be 100
    rs = pd.Series(np.divide(avg_gain, avg_loss.where(avg_loss != 0, np.nan)), index=close_series.index)
    rsi = 100 - (100 / (1 + rs))

    # Where avg_loss == 0 and avg_gain > 0, set RSI=100; where both 0, set 0
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain == 0)), 0.0)
    rsi = rsi.fillna(0.0)
    return rsi


