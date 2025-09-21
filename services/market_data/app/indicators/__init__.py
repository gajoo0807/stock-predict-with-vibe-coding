from __future__ import annotations

from typing import Dict, Any

import pandas as pd

from .rsi import compute_rsi14
from .macd import compute_macd_12_26_9
from .moving_average import compute_ma20_ma60_and_trend
from .volume import compute_volume_indicators


def compute_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute all indicators for the given bars DataFrame.

    Expected df columns: ["open","high","low","close","volume"], index as datetime or column 'ts'.
    Returns a dict with columns or scalar enrichments per-row where appropriate.
    """
    if df.empty:
        return {}

    work_df = df.copy()
    if "close" not in work_df.columns:
        raise ValueError("DataFrame must contain 'close' column")

    indicators: Dict[str, Any] = {}

    # Ensure 1-D series for close and volume
    close_col = work_df["close"]
    if isinstance(close_col, pd.DataFrame):
        close_col = close_col.iloc[:, 0]
    volume_col = work_df.get("volume")
    if isinstance(volume_col, pd.DataFrame):
        volume_col = volume_col.iloc[:, 0]

    indicators["rsi14"] = compute_rsi14(close_col).tolist()  # type: ignore[arg-type]

    macd_line, signal_line, histogram, signal = compute_macd_12_26_9(close_col)  # type: ignore[arg-type]
    indicators["macd_line"] = macd_line.tolist()
    indicators["signal_line"] = signal_line.tolist()
    indicators["histogram"] = histogram.tolist()
    indicators["macd_signal"] = signal

    ma20, ma60, ma20_trend = compute_ma20_ma60_and_trend(close_col)  # type: ignore[arg-type]
    indicators["ma20"] = ma20.tolist()
    indicators["ma60"] = ma60.tolist()
    indicators["ma20_trend"] = ma20_trend

    vol_avg20, vol_vs_avg20 = compute_volume_indicators(volume_col)  # type: ignore[arg-type]
    indicators["vol_avg20"] = vol_avg20.tolist()
    indicators["vol_vs_avg20"] = vol_vs_avg20.tolist()

    return indicators


