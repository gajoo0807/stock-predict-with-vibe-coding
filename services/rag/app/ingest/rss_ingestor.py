from __future__ import annotations
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db import crud
from app.rag.chunk import split_text
from app.rag.embed import EmbeddingBackend
from app.rag.mapping import guess_ticker_from_text


RSS_FEEDS: List[str] = [
    "https://www.apple.com/newsroom/rss-feed.rss",
]


def ingest_rss():
    try:
        import feedparser  # type: ignore
    except Exception:
        return  # no external network or package not available

    embedder = EmbeddingBackend()
    with SessionLocal() as db:
        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
            except Exception:
                continue
            for entry in feed.entries[:20]:
                title = entry.get("title") or ""
                url = entry.get("link")
                published = entry.get("published_parsed")
                if published:
                    published_at = datetime(*published[:6], tzinfo=timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)
                summary = entry.get("summary") or ""
                text = summary
                ticker = guess_ticker_from_text(title + " " + text)
                news = crud.upsert_news(
                    db,
                    ticker=ticker,
                    title=title,
                    url=url,
                    published_at=published_at,
                    source="rss",
                    text=text,
                    first_seen_at=published_at,
                )
                chunks = split_text(text)
                if not chunks:
                    continue
                created_chunks = crud.add_chunks(db, news, chunks)
                vectors = embedder.embed_chunks([c.content for c in created_chunks])
                crud.add_embeddings(db, created_chunks, vectors)
        db.commit()


if __name__ == "__main__":
    ingest_rss()


