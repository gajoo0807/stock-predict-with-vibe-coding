from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from .base import BarsAdapter


TIMEFRAME_TO_YF = {
    "1d": "1d",
    "1h": "60m",
    "5m": "5m",
}


class FreeSourceAdapter(BarsAdapter):
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _read_parquet_fallback(self, ticker: str, tf: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> pd.DataFrame:
        file_path = self.data_dir / f"{ticker}_{tf}.parquet"
        if not file_path.exists():
            # Generate synthetic data in-memory for the requested window
            import numpy as np

            if start is None or end is None:
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).astype(
                    {"open": float, "high": float, "low": float, "close": float, "volume": float}
                )

            if tf == "1d":
                ts = pd.date_range(start=pd.to_datetime(start, utc=True), end=pd.to_datetime(end, utc=True), freq="B")
            elif tf == "1h":
                ts = pd.date_range(start=pd.to_datetime(start, utc=True), end=pd.to_datetime(end, utc=True), freq="H")
            else:  # "5m"
                ts = pd.date_range(start=pd.to_datetime(start, utc=True), end=pd.to_datetime(end, utc=True), freq="5min")
                # Cap to avoid explosion
                if len(ts) > 500:
                    ts = ts[:500]

            # If no timestamps (e.g., weekend for 1d), return empty set to reflect no trading days
            if len(ts) == 0:
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).astype(
                    {"open": float, "high": float, "low": float, "close": float, "volume": float}
                )

            rng = np.random.default_rng(42)
            prices = 100 + np.cumsum(rng.normal(0, 1, size=len(ts)))
            close = pd.Series(prices)
            open_ = close.shift(1)
            if not close.empty:
                open_ = open_.fillna(close.iloc[0])
            high = pd.concat([open_, close], axis=1).max(axis=1) + 0.2
            low = pd.concat([open_, close], axis=1).min(axis=1) - 0.2
            volume = pd.Series(1_000_000 + rng.integers(0, 1000, size=len(ts))).astype(float)
            df = pd.DataFrame(
                {
                    "ts": ts,
                    "open": open_.values,
                    "high": high.values,
                    "low": low.values,
                    "close": close.values,
                    "volume": volume.values,
                }
            ).set_index("ts")
            return df
        df = pd.read_parquet(file_path)
        # Expect 'ts' column
        if "ts" in df.columns:
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            df = df.set_index("ts")
        return df[["open", "high", "low", "close", "volume"]].sort_index()

    def get_bars(self, tickers: List[str], start: datetime, end: datetime, tf: str) -> Dict[str, pd.DataFrame]:
        results: Dict[str, pd.DataFrame] = {}
        interval = TIMEFRAME_TO_YF.get(tf, "1d")
        for ticker in tickers:
            try:
                df = yf.download(ticker, start=start, end=end, interval=interval, progress=False, auto_adjust=False)
                if df is None or df.empty:
                    raise RuntimeError("empty from yfinance")
                # Normalize columns (handle possible MultiIndex columns from newer yfinance)
                if isinstance(df.columns, pd.MultiIndex):
                    # Determine which level contains price fields
                    level0 = [str(v).lower() for v in df.columns.get_level_values(0).unique()]
                    level1 = [str(v).lower() for v in df.columns.get_level_values(1).unique()]
                    candidate_fields = {"open", "high", "low", "close", "volume"}
                    if any(v in candidate_fields for v in level0):
                        field_level = 0
                        sym_level = 1
                    elif any(v in candidate_fields for v in level1):
                        field_level = 1
                        sym_level = 0
                    else:
                        # Fallback: flatten columns and try rename later
                        df.columns = ["_".join(map(str, c)).lower() for c in df.columns]
                        
                    if isinstance(df.columns, pd.MultiIndex):
                        # Try select symbol columns
                        if ticker in df.columns.get_level_values(sym_level):
                            df = df.xs(ticker, axis=1, level=sym_level)
                        else:
                            # pick first symbol
                            first_sym = df.columns.get_level_values(sym_level)[0]
                            df = df.xs(first_sym, axis=1, level=sym_level)

                # After possible xs, ensure flat columns and standard names
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.rename(columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Adj Close": "adj_close",
                    "Volume": "volume",
                })
                df.columns = [str(c).lower() for c in df.columns]
                # Ensure timezone-aware UTC index
                if df.index.tz is None:
                    df.index = pd.to_datetime(df.index, utc=True)
                # Drop duplicate columns if any
                if df.columns.duplicated().any():
                    df = df.loc[:, ~df.columns.duplicated()]
                # Keep only required columns if present
                keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
                df = df[keep]
            except Exception:
                # fallback to local parquet
                df = self._read_parquet_fallback(ticker, tf, start=start, end=end)

            # Clip to date window in case
            if not df.empty:
                df = df[(df.index >= pd.to_datetime(start, utc=True)) & (df.index <= pd.to_datetime(end, utc=True))]
            results[ticker] = df
        return results


def generate_sample_parquet(data_dir: Path) -> None:
    """Generate minimal sample parquet files for AAPL and TSM for 1d and 5m.

    This function creates deterministic synthetic data suitable for tests.
    """
    import numpy as np

    data_dir.mkdir(parents=True, exist_ok=True)

    def make_series(start: str, periods: int, freq: str, base_price: float) -> pd.DataFrame:
        ts = pd.date_range(start=start, periods=periods, freq=freq, tz="UTC")
        prices = base_price + np.cumsum(np.random.default_rng(42).normal(0, 1, size=periods))
        close = pd.Series(prices)
        open_ = close.shift(1).fillna(close.iloc[0])
        high = pd.concat([open_, close], axis=1).max(axis=1) + 0.5
        low = pd.concat([open_, close], axis=1).min(axis=1) - 0.5
        volume = pd.Series(1_000_000 + np.random.default_rng(42).integers(0, 1000, size=periods))
        df = pd.DataFrame({
            "ts": ts,
            "open": open_.values,
            "high": high.values,
            "low": low.values,
            "close": close.values,
            "volume": volume.values.astype(float),
        })
        return df

    samples = [
        ("AAPL", "1d", "2024-01-01", 30, "1D", 180.0),
        ("TSM", "1d", "2024-01-01", 30, "1D", 100.0),
        ("AAPL", "5m", "2024-01-02 14:30", 100, "5min", 180.0),
        ("TSM", "5m", "2024-01-02 14:30", 100, "5min", 100.0),
    ]

    for ticker, tf, start, periods, freq, base in samples:
        df = make_series(start, periods, freq, base)
        file_path = data_dir / f"{ticker}_{tf}.parquet"
        df.to_parquet(file_path, index=False)


