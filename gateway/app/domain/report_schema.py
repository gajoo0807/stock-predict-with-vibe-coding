from pydantic import BaseModel, Field, AnyUrl
from typing import Literal, Optional, List, Dict


class MacdModel(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]


class NewsItem(BaseModel):
    title: str
    ts: str
    doc_id: str
    url: Optional[AnyUrl] = None


class IndicatorsModel(BaseModel):
    rsi14: float
    macd: MacdModel
    vol_vs_avg20: float
    trend_20_60: Literal["up", "flat", "down"]


class ContextModel(BaseModel):
    sector: Optional[str] = None
    peer_strength_percentile: Optional[float] = None
    top_news: List[NewsItem] = []


class ReportResponse(BaseModel):
    as_of: str
    ticker: str
    spot: float
    indicators: IndicatorsModel
    context: ContextModel

    class Config:
        schema_extra = {
            "example": {
                "as_of": "2024-01-10T00:00:00Z",
                "ticker": "TSM",
                "spot": 108.0,
                "indicators": {
                    "rsi14": 55.0,
                    "macd": {"signal": "bullish"},
                    "vol_vs_avg20": 1.2,
                    "trend_20_60": "up",
                },
                "context": {
                    "sector": "Semiconductors",
                    "peer_strength_percentile": 0.8,
                    "top_news": [
                        {
                            "title": "TSM hits new milestone",
                            "ts": "2024-01-10T12:00:00Z",
                            "doc_id": "doc-1",
                            "url": "http://example.com/news1",
                        }
                    ],
                },
            }
        }


