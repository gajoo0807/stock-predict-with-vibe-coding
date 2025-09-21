from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import HTTPException


ALLOWED_TIMEFRAMES = {"1d", "1h", "5m"}


def validate_tickers(tickers: List[str]) -> None:
    if not tickers or len(tickers) > 50:
        raise HTTPException(status_code=422, detail="tickers must be 1..50 symbols")


def validate_timeframe(tf: str) -> None:
    if tf not in ALLOWED_TIMEFRAMES:
        raise HTTPException(status_code=422, detail=f"invalid timeframe: {tf}")


def validate_date_range(start: datetime, end: datetime) -> None:
    if start > end:
        raise HTTPException(status_code=422, detail="start must be <= end")
    delta_days = (end - start).days
    if delta_days > 365 * 5:
        raise HTTPException(status_code=422, detail="date window must be <= 5 years")



