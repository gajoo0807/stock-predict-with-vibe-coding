from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ..adapters.free_source import FreeSourceAdapter
from ..core.config import settings
from ..indicators import compute_indicators
from ..utils.adjust import apply_dividends, apply_splits
from ..utils.validators import validate_date_range, validate_timeframe, validate_tickers

router = APIRouter()

@router.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "market_data"}


class BarOut(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    rsi14: Optional[float] = None
    macd_signal: Optional[Literal["bullish", "bearish", "neutral"]] = None
    ma20_trend: Optional[Literal["up", "down", "flat"]] = None
    vol_vs_avg20: Optional[float] = Field(default=None)


class BarsResponse(BaseModel):
    as_of: datetime
    timeframe: Literal["1d", "1h", "5m"]
    adjust: Literal["raw", "adj"]
    results: Dict[str, List[BarOut]]


@router.get("/internal/bars", response_model=BarsResponse)
async def get_internal_bars(
    ticker: str = Query(..., description="Comma separated tickers"),
    start: str = Query(...),
    end: str = Query(...),
    tf: Literal["1d", "1h", "5m"] = Query("1d"),
    adjust: Literal["raw", "adj"] = Query("raw"),
):
    tickers = [t.strip().upper() for t in ticker.split(",") if t.strip()]
    validate_tickers(tickers)
    validate_timeframe(tf)

    start_dt = pd.to_datetime(start).to_pydatetime().replace(tzinfo=timezone.utc)
    end_dt = pd.to_datetime(end).to_pydatetime().replace(tzinfo=timezone.utc)
    validate_date_range(start_dt, end_dt)

    sample_dir = Path(__file__).resolve().parents[1] / "data" / "sample"
    adapter = FreeSourceAdapter(sample_dir)

    bars_map = adapter.get_bars(tickers, start_dt, end_dt, tf)

    # For simplicity, corporate actions are empty in I1.
    corporate_actions: List[dict] = []
    results: Dict[str, List[BarOut]] = {}

    for tkr, df in bars_map.items():
        if df.empty:
            results[tkr] = []
            continue
        df = df.sort_index()
        if adjust == "adj":
            df = apply_splits(df, corporate_actions)
            df = apply_dividends(df, corporate_actions, enabled=False)

        indic = compute_indicators(df)
        # merge indicators back into df
        enrich = pd.DataFrame(indic, index=df.index)
        joined = pd.concat([df, enrich], axis=1)

        # weekend/holiday handling: df already reflects real timestamps; filter window
        joined = joined[(joined.index >= pd.to_datetime(start_dt)) & (joined.index <= pd.to_datetime(end_dt))]

        out_rows: List[BarOut] = []
        for ts, row in joined.iterrows():
            # Ensure scalar floats for OHLCV in case of any lingering Series types
            def to_float(x):
                import pandas as pd
                if isinstance(x, (list, tuple)):
                    return float(x[0]) if x else 0.0
                try:
                    return float(x)
                except Exception:
                    return float(x.iloc[0]) if hasattr(x, "iloc") else 0.0
            out_rows.append(
                BarOut(
                    ts=pd.to_datetime(ts).to_pydatetime().replace(tzinfo=timezone.utc),
                    open=to_float(row.get("open", 0.0)),
                    high=to_float(row.get("high", 0.0)),
                    low=to_float(row.get("low", 0.0)),
                    close=to_float(row.get("close", 0.0)),
                    volume=to_float(row.get("volume", 0.0)),
                    rsi14=float(row.get("rsi14")) if pd.notna(row.get("rsi14")) else None,
                    macd_signal=(row.get("macd_signal") if pd.notna(row.get("macd_signal")) else None),
                    ma20_trend=(row.get("ma20_trend") if pd.notna(row.get("ma20_trend")) else None),
                    vol_vs_avg20=float(row.get("vol_vs_avg20")) if pd.notna(row.get("vol_vs_avg20")) else None,
                )
            )
        results[tkr] = out_rows

    return BarsResponse(
        as_of=datetime.now(tz=timezone.utc),
        timeframe=tf,
        adjust=adjust,
        results=results,
    )
