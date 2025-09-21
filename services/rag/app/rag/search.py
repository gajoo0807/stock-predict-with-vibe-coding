from __future__ import annotations
from typing import List, Optional
from datetime import datetime
import numpy as np
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from app.db.session import SessionLocal
from app.db import models as m
from app.domain.schemas import SearchNewsItem, SearchNewsResponse
from app.rag.embed import EmbeddingBackend
from app.rag.mapping import aliases_for_ticker
from app.core.config import settings


async def search_news(
    *,
    ticker: Optional[str] = None,
    query: Optional[str] = None,
    since: Optional[datetime] = None,
    as_of: datetime,
    top_k: int,
):
    # Build textual query
    aliases = aliases_for_ticker(ticker)
    qtext = " ".join(aliases + ([query] if query else [])) or (ticker or "")

    # 0) Metadata-first cheap candidates to guarantee non-empty results
    with SessionLocal() as db:
        meta_rows = _metadata_fallback(db, ticker=ticker, qtext=qtext, since=since, as_of=as_of)
        if meta_rows:
            # optional rerank by TF-IDF on meta candidates
            texts = [r.get("content") or "" for r in meta_rows]
            try:
                tfidf = TfidfVectorizer(max_features=20000)
                X = tfidf.fit_transform(texts)
                qX = tfidf.transform([qtext])
                scores = (X @ qX.T).toarray().ravel()
            except Exception:
                scores = np.zeros(len(texts), dtype=float)
            ranked = sorted(
                zip(meta_rows, scores), key=lambda x: float(x[1]), reverse=True
            )[: top_k]
            results: List[SearchNewsItem] = []
            for r, s in ranked:
                snippet = (r.get("content") or "")[:240]
                results.append(
                    SearchNewsItem(
                        doc_id=f"news:{r['news_id']}",
                        title=r.get("title") or "",
                        url=r.get("url"),
                        published_at=r.get("published_at"),
                        snippet=snippet,
                        score=float(s),
                        ticker=r.get("ticker"),
                    )
                )
            return SearchNewsResponse(as_of=as_of, query=qtext, top_k=top_k, results=results)

    # 1) Embed query
    embedder = EmbeddingBackend()
    qvec = embedder.embed_chunks([qtext])
    if qvec.shape[0] == 0:
        return SearchNewsResponse(as_of=as_of, query=qtext, top_k=top_k, results=[])
    q = qvec[0]

    # Candidate retrieval by vector similarity using pgvector cosine
    # Limit initial candidates to 50
    with SessionLocal() as db:
        # Join embeddings -> chunk -> news with time filters
        params = {"as_of": as_of}
        time_filter = "news.first_seen_at <= :as_of AND news.published_at <= :as_of"
        if since is not None:
            params["since"] = since
            time_filter += " AND news.published_at >= :since"

        dim = len(q)
        # Use cosine distance: 1 - cos_sim. Order by increasing distance.
        sql = f"""
        SELECT
            nc.id AS chunk_id,
            n.id AS news_id,
            n.title AS title,
            n.url AS url,
            n.published_at AS published_at,
            n.ticker AS ticker,
            nc.content AS content,
            1 - (ne.embedding <=> :qvec) AS score
        FROM news_embeddings ne
        JOIN news_chunks nc ON ne.chunk_id = nc.id
        JOIN news n ON nc.news_id = n.id
        WHERE {time_filter}
        ORDER BY ne.embedding <=> :qvec
        LIMIT 50
        """
        try:
            rows = db.execute(sql_text(sql), {**params, "qvec": q.tolist()}).mappings().all()
        except Exception:
            rows = []

        # Fallback to python cosine search if SQL returned no rows or failed
        if not rows:
            rows = _fallback_vector_search_python(db, q, since=since, as_of=as_of)
            if not rows:
                # final fallback: TF-IDF only over chunks
                rows = _tfidf_only_search(db, qtext, since=since, as_of=as_of)
                if not rows:
                    # ultimate fallback: simple metadata query by ticker/aliases or LIKE
                    rows = _metadata_fallback(db, ticker=ticker, qtext=qtext, since=since, as_of=as_of)
                    if not rows:
                        # last resort: return latest news chunks by time only
                        rows = _latest_news_fallback(db, since=since, as_of=as_of)
                        if not rows:
                            return SearchNewsResponse(as_of=as_of, query=qtext, top_k=top_k, results=[])

        # Hybrid rerank with TF-IDF over candidates
        texts = [r["content"] or "" for r in rows]
        tfidf = TfidfVectorizer(max_features=20000)
        try:
            X = tfidf.fit_transform(texts)
            qX = tfidf.transform([qtext])
            import numpy as _np

            bm25_scores = (X @ qX.T).toarray().ravel()
        except Exception:
            bm25_scores = np.zeros(len(texts), dtype=float)

        # Blend scores: alpha * vector + (1-alpha) * tfidf
        alpha = 0.7
        vec_scores = np.array([r.get("score", 0.0) for r in rows])
        scores = alpha * vec_scores + (1 - alpha) * bm25_scores

        ranked = sorted(
            zip(rows, scores), key=lambda x: float(x[1]), reverse=True
        )
        ranked = ranked[: top_k]

        results: List[SearchNewsItem] = []
        for r, s in ranked:
            snippet = (r["content"] or "")[:240]
            results.append(
                SearchNewsItem(
                    doc_id=f"news:{r['news_id']}",
                    title=r["title"] or "",
                    url=r.get("url"),
                    published_at=r.get("published_at"),
                    snippet=snippet,
                    score=float(s),
                    ticker=r.get("ticker"),
                )
            )

        return SearchNewsResponse(as_of=as_of, query=qtext, top_k=top_k, results=results)


def _fallback_vector_search_python(db: Session, q: np.ndarray, *, since, as_of):
    # Load all candidate chunks by time and compute cosine similarity in Python
    from sqlalchemy import and_, select
    import numpy as _np

    stmt = (
        select(m.NewsChunk, m.News, m.NewsEmbedding)
        .join(m.News, m.NewsChunk.news_id == m.News.id)
        .join(m.NewsEmbedding, m.NewsEmbedding.chunk_id == m.NewsChunk.id)
    )
    conds = [m.News.first_seen_at <= as_of, m.News.published_at <= as_of]
    if since is not None:
        conds.append(m.News.published_at >= since)
    stmt = stmt.where(and_(*conds))
    rows = db.execute(stmt).all()
    def cos_sim(a, b):
        a = _np.array(a)
        b = _np.array(b)
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        return float(a.dot(b) / denom) if denom else 0.0
    out = []
    for chunk, news, emb in rows:
        out.append(
            {
                "chunk_id": str(chunk.id),
                "news_id": str(news.id),
                "title": news.title,
                "url": news.url,
                "published_at": news.published_at,
                "ticker": news.ticker,
                "content": chunk.content,
                "score": cos_sim(q, emb.embedding),
            }
        )
    # sort descending by score and return top 50
    out = sorted(out, key=lambda x: float(x["score"]), reverse=True)[:50]
    return out


def _tfidf_only_search(db: Session, qtext: str, *, since, as_of):
    from sqlalchemy import and_, select
    # pull chunks with time filters only (no embeddings)
    stmt = (
        select(m.NewsChunk, m.News)
        .join(m.News, m.NewsChunk.news_id == m.News.id)
    )
    conds = [m.News.first_seen_at <= as_of, m.News.published_at <= as_of]
    if since is not None:
        conds.append(m.News.published_at >= since)
    stmt = stmt.where(and_(*conds))
    rows = db.execute(stmt).all()
    if not rows:
        return []
    texts = [(chunk.content or "") for chunk, news in rows]
    try:
        tfidf = TfidfVectorizer(max_features=20000)
        X = tfidf.fit_transform(texts)
        qX = tfidf.transform([qtext])
        scores = (X @ qX.T).toarray().ravel()
    except Exception:
        scores = np.zeros(len(texts), dtype=float)
    out = []
    for (chunk, news), s in zip(rows, scores):
        out.append(
            {
                "chunk_id": str(chunk.id),
                "news_id": str(news.id),
                "title": news.title,
                "url": news.url,
                "published_at": news.published_at,
                "ticker": news.ticker,
                "content": chunk.content,
                "score": float(s),
            }
        )
    out = sorted(out, key=lambda x: float(x["score"]), reverse=True)[:50]
    return out


def _metadata_fallback(db: Session, *, ticker: Optional[str], qtext: str, since, as_of):
    from sqlalchemy import and_, select, or_
    # Try to find recent news by ticker first, else simple LIKE match on title/text
    conds_time = [m.News.first_seen_at <= as_of, m.News.published_at <= as_of]
    if since is not None:
        conds_time.append(m.News.published_at >= since)

    results = []
    if ticker:
        stmt = (
            select(m.NewsChunk, m.News)
            .join(m.News, m.NewsChunk.news_id == m.News.id)
            .where(and_(m.News.ticker == ticker, *conds_time))
            .order_by(m.News.published_at.desc(), m.NewsChunk.chunk_idx.asc())
            .limit(50)
        )
        rows = db.execute(stmt).all()
        for chunk, news in rows:
            results.append(
                {
                    "chunk_id": str(chunk.id),
                    "news_id": str(news.id),
                    "title": news.title,
                    "url": news.url,
                    "published_at": news.published_at,
                    "ticker": news.ticker,
                    "content": chunk.content,
                    "score": 0.0,
                }
            )
        if results:
            return results

    # LIKE-based
    like = f"%{qtext.split()[0]}%" if qtext else "%"
    stmt = (
        select(m.NewsChunk, m.News)
        .join(m.News, m.NewsChunk.news_id == m.News.id)
        .where(
            and_(
                or_(m.News.title.ilike(like), m.News.text.ilike(like)),
                *conds_time,
            )
        )
        .order_by(m.News.published_at.desc(), m.NewsChunk.chunk_idx.asc())
        .limit(50)
    )
    rows = db.execute(stmt).all()
    for chunk, news in rows:
        results.append(
            {
                "chunk_id": str(chunk.id),
                "news_id": str(news.id),
                "title": news.title,
                "url": news.url,
                "published_at": news.published_at,
                "ticker": news.ticker,
                "content": chunk.content,
                "score": 0.0,
            }
        )
    return results


def _latest_news_fallback(db: Session, *, since, as_of):
    from sqlalchemy import and_, select
    stmt = (
        select(m.NewsChunk, m.News)
        .join(m.News, m.NewsChunk.news_id == m.News.id)
    )
    conds = [m.News.first_seen_at <= as_of, m.News.published_at <= as_of]
    if since is not None:
        conds.append(m.News.published_at >= since)
    stmt = stmt.where(and_(*conds)).order_by(m.News.published_at.desc(), m.NewsChunk.chunk_idx.asc()).limit(50)
    rows = db.execute(stmt).all()
    results = []
    for chunk, news in rows:
        results.append(
            {
                "chunk_id": str(chunk.id),
                "news_id": str(news.id),
                "title": news.title,
                "url": news.url,
                "published_at": news.published_at,
                "ticker": news.ticker,
                "content": chunk.content,
                "score": 0.0,
            }
        )
    return results


