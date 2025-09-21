from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np
import pandas as pd


def compute_volume_indicators(volume: Iterable[float]) -> Tuple[pd.Series, pd.Series]:
    """Compute 20-day average volume and today's volume vs avg20 ratio.

    Returns: (vol_avg20, vol_vs_avg20)
    """
    volume_series = pd.Series(volume, dtype=float)
    vol_avg20 = volume_series.rolling(window=20, min_periods=1).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        vol_vs_avg20 = volume_series / vol_avg20.replace(0, np.nan)
    vol_vs_avg20 = vol_vs_avg20.fillna(0.0)
    return vol_avg20, vol_vs_avg20



