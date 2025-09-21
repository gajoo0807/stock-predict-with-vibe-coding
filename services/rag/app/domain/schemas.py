from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class SearchNewsItem(BaseModel):
    doc_id: str
    title: str
    url: Optional[str]
    published_at: Optional[datetime]
    snippet: str
    score: float
    ticker: Optional[str]


class SearchNewsResponse(BaseModel):
    as_of: datetime
    query: str
    top_k: int
    results: List[SearchNewsItem]


