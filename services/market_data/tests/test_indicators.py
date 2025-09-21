import pandas as pd
import numpy as np
import pytest

from services.market_data.app.indicators.rsi import compute_rsi14
from services.market_data.app.indicators.macd import compute_macd_12_26_9
from services.market_data.app.indicators.moving_average import compute_ma20_ma60_and_trend
from services.market_data.app.indicators.volume import compute_volume_indicators


def test_rsi_basic():
    # Construct a deterministic series: steadily increasing -> RSI should be high
    close = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], dtype=float)
    rsi = compute_rsi14(close)
    assert len(rsi) == len(close)
    assert rsi.iloc[-1] > 70


def test_macd_values_and_signal():
    close = pd.Series(np.linspace(100, 120, 100), dtype=float)  # upward trend -> bullish histogram
    macd_line, signal_line, histogram, signal = compute_macd_12_26_9(close)
    assert len(macd_line) == len(close)
    assert len(signal) == len(close)
    assert signal[-1] in {"bullish", "bearish", "neutral"}
    assert signal[-1] == "bullish"


def test_ma_trend():
    close = pd.Series(np.concatenate([np.linspace(100, 110, 30), np.linspace(110, 105, 30)]), dtype=float)
    ma20, ma60, trend = compute_ma20_ma60_and_trend(close)
    assert len(trend) == len(close)
    # trend towards the end should be 'down'
    assert trend[-1] == "down"


def test_volume_avg20_ratio():
    vol = pd.Series([100] * 19 + [200], dtype=float)
    avg20, ratio = compute_volume_indicators(vol)
    assert len(avg20) == len(vol)
    assert ratio.iloc[-1] == pytest.approx(200 / (sum([100] * 19 + [200]) / 20), rel=1e-6)


