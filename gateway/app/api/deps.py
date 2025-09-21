from typing import Optional

from fastapi import Query


def ticker_query(ticker: str = Query(..., description="Ticker symbol")) -> str:
    return ticker



