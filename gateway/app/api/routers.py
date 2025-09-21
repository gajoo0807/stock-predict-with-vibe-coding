from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.services.report_service import get_report
from app.domain.report_schema import ReportResponse

router = APIRouter()

@router.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "gateway"}

@router.get("/report", response_model=ReportResponse)
async def report(
    ticker: str = Query(..., description="Ticker symbol, e.g., TSM"),
    as_of: Optional[datetime] = Query(
        None, description="ISO8601 datetime. If weekend/holiday, fallback to latest trading day"
    ),
):
    return await get_report(ticker=ticker, as_of=as_of)
