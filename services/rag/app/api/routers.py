from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from app.core.config import settings
from app.domain.schemas import SearchNewsResponse
from app.rag.search import search_news

router = APIRouter()

@router.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "rag"}


class SearchRequest(BaseModel):
    ticker: Optional[str] = None
    query: Optional[str] = None
    since: Optional[datetime] = None
    as_of: datetime
    top_k: Optional[int] = None

    @validator("top_k", always=True)
    def validate_top_k(cls, v):
        if v is None:
            return settings.DEFAULT_TOP_K
        if v <= 0:
            raise ValueError("top_k must be positive")
        if v > settings.MAX_TOP_K:
            return settings.MAX_TOP_K
        return v

    @validator("query", always=True)
    def validate_query_or_ticker(cls, v, values):
        if not v and not values.get("ticker"):
            raise ValueError("ticker or query is required")
        return v


@router.post("/search_news", response_model=SearchNewsResponse)
async def post_search_news(req: SearchRequest):
    try:
        resp = await search_news(
            ticker=req.ticker,
            query=req.query,
            since=req.since,
            as_of=req.as_of,
            top_k=req.top_k or settings.DEFAULT_TOP_K,
        )
        return resp
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        # On error, return empty results but 200
        return SearchNewsResponse(as_of=req.as_of, query=req.query or req.ticker or "", top_k=req.top_k or settings.DEFAULT_TOP_K, results=[])


@router.post("/ingest_samples")
async def post_ingest_samples():
    try:
        # Lazy import to avoid import-time dependency during tests
        from app.ingest.sample_loader import load_samples  # type: ignore
        load_samples()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

