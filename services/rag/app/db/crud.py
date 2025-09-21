from __future__ import annotations
from typing import Iterable, Optional, Sequence, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, outerjoin
from app.db import models as m


def upsert_news(
    db: Session,
    *,
    ticker: Optional[str],
    title: str,
    url: Optional[str],
    published_at,
    source: Optional[str],
    text: Optional[str],
    first_seen_at,
):
    # dedupe by url if provided, else by (title, published_at)
    stmt = None
    if url:
        stmt = select(m.News).where(m.News.url == url)
    else:
        stmt = select(m.News).where(m.News.title == title, m.News.published_at == published_at)
    existing = db.execute(stmt).scalars().first()
    if existing:
        return existing
    news = m.News(
        ticker=ticker,
        title=title,
        url=url,
        published_at=published_at,
        source=source,
        text=text,
        first_seen_at=first_seen_at,
    )
    db.add(news)
    db.flush()
    return news


def add_chunks(db: Session, news: m.News, chunks: Sequence[str]):
    # idempotent: skip if chunk_idx already exists for this news
    existing = db.execute(
        select(m.NewsChunk.chunk_idx, m.NewsChunk.id).where(m.NewsChunk.news_id == news.id)
    ).all()
    existing_idx_to_id = {row[0]: row[1] for row in existing}
    created = []
    for idx, content in enumerate(chunks):
        if idx in existing_idx_to_id:
            # optionally update content if empty; keep as is to avoid churn
            continue
        c = m.NewsChunk(news_id=news.id, chunk_idx=idx, content=content)
        db.add(c)
        created.append(c)
    db.flush()
    return created


def add_embeddings(db: Session, chunks: Sequence[m.NewsChunk], vectors):
    # vectors: ndarray num_chunks x 384
    for chunk, vec in zip(chunks, vectors):
        # upsert by chunk_id uniqueness
        existing = db.execute(
            select(m.NewsEmbedding).where(m.NewsEmbedding.chunk_id == chunk.id)
        ).scalars().first()
        if existing:
            existing.embedding = vec.tolist()
        else:
            emb = m.NewsEmbedding(chunk_id=chunk.id, embedding=vec.tolist())
            db.add(emb)
    db.flush()
    return True


def get_candidate_chunks_by_time(db: Session, *, as_of, since=None):
    # Return chunks joined with news filtered by time
    from sqlalchemy import and_

    stmt = select(m.NewsChunk, m.News).join(m.News, m.NewsChunk.news_id == m.News.id)
    conds = [m.News.first_seen_at <= as_of, m.News.published_at <= as_of]
    if since is not None:
        conds.append(m.News.published_at >= since)
    stmt = stmt.where(and_(*conds))
    return db.execute(stmt).all()


def get_chunks_without_embedding(db: Session, *, news_id=None):
    # Return NewsChunk objects that do not have a corresponding NewsEmbedding
    chunk = m.NewsChunk
    emb = m.NewsEmbedding
    j = outerjoin(chunk, emb, chunk.id == emb.chunk_id)
    stmt = select(chunk).select_from(j).where(emb.id.is_(None))
    if news_id is not None:
        stmt = stmt.where(chunk.news_id == news_id)
    return db.execute(stmt).scalars().all()


