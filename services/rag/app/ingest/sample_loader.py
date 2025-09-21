from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db import crud
from app.rag.chunk import split_text
from app.rag.embed import EmbeddingBackend
from app.rag.mapping import guess_ticker_from_text

# ---- 確保 pgvector extension 在 fallback 模式也會被建立 ----
def _ensure_vector_extension(session: Session) -> None:
    try:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        session.commit()
    except Exception:
        session.rollback()
        # 不阻斷流程，但留給上層 log（如需）

SAMPLES: List[Dict] = [
    {
        "title": "TSMC expands advanced packaging (CoWoS) capacity to meet AI demand",
        "url": "https://example.com/tsmc-packaging",
        "text": "TSM and TSMC strengthen advanced packaging (CoWoS) capacity to address surging AI accelerator demand. 台積電 宣布 擴充 先進封裝 產能。",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=20),
    },
    {
        "title": "Apple unveils new A-series chip with improved neural engine",
        "url": "https://example.com/apple-a-series",
        "text": "Apple introduced its next-generation A-series processor with a significantly enhanced neural engine, targeting on-device AI performance for iPhone and iPad...",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=18),
    },
    {
        "title": "NVIDIA reports record data center revenue on AI growth",
        "url": "https://example.com/nvda-datacenter",
        "text": "NVIDIA posted record data center revenue as demand for AI training and inference accelerates. The company highlighted strong adoption of its Hopper architecture... 輝達 數據中心 業績。",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=17),
    },
    {
        "title": "Apple invests in Taiwan suppliers for advanced packaging",
        "url": "https://example.com/apple-tsmc-packaging",
        "text": "Reports indicate Apple is investing with Taiwan suppliers to secure advanced packaging capacity in preparation for next-gen devices utilizing AI features.",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=16),
    },
    {
        "title": "TSMC announces 2nm process timeline",
        "url": "https://example.com/tsmc-2nm",
        "text": "TSMC detailed its 2nm process technology roadmap, emphasizing improved performance-per-watt and leadership in mobile and HPC applications.",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=15),
    },
    {
        "title": "NVIDIA partners with foundries for advanced packaging",
        "url": "https://example.com/nvda-packaging",
        "text": "To meet soaring demand, NVIDIA is partnering with leading foundries to scale advanced packaging capacity for its next-gen AI GPUs.",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=14),
    },
    {
        "title": "Apple explores AI features across ecosystem",
        "url": "https://example.com/apple-ai-ecosystem",
        "text": "Apple is exploring AI-powered features across its ecosystem, leveraging on-device processing and privacy-preserving techniques.",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=13),
    },
    {
        "title": "TSMC sees strong demand from AI accelerators",
        "url": "https://example.com/tsmc-ai-demand",
        "text": "Industry sources note TSMC is seeing robust orders driven by AI accelerators, requiring expanded capacity and advanced nodes. 先進封裝 與 CoWoS 需求 強勁。",
        "source": "sample",
        "published_at": datetime.now(timezone.utc) - timedelta(days=12),
    },
]


def load_samples() -> None:
    embedder = EmbeddingBackend()  # auto: 有 OPENAI_KEY 用 openai，否則 local ST model
    num_news = 0
    new_chunks = 0
    new_embeddings = 0

    with SessionLocal() as db:
        # 確保 pgvector 存在（避免 Alembic 失敗時 embeddings 寫不進去）
        _ensure_vector_extension(db)

        for item in SAMPLES:
            # 1) upsert 新聞（以 url 或 (title, published_at) 去重，crud 內部負責）
            ticker = guess_ticker_from_text(f"{item['title']} {item['text']}") or None
            news = crud.upsert_news(
                db,
                ticker=ticker,
                title=item["title"],
                url=item["url"],
                published_at=item["published_at"],
                source=item["source"],
                text=item["text"],
                first_seen_at=item["published_at"],
            )
            num_news += 1

            # 2) 確保有 chunks：若 add_chunks 回 0，代表已存在，就跳到找「尚未嵌入」的 chunks
            chunks_texts = split_text(item["text"], target_tokens=600, min_tokens=200)
            created_chunks = crud.add_chunks(db, news, chunks_texts)  # 回傳「新建的 Chunk 物件」list
            if created_chunks:
                new_chunks += len(created_chunks)

            # 3) 找到所有「尚未嵌入」的 chunks（包含既有但沒有 embeddings 的）
            pending_chunks = crud.get_chunks_without_embedding(db, news_id=news.id)
            if pending_chunks:
                vectors = embedder.embed_chunks([c.content for c in pending_chunks])
                crud.add_embeddings(db, pending_chunks, vectors)
                new_embeddings += len(pending_chunks)

        db.commit()

    print(f"[sample_loader] inserted news={num_news}, new_chunks={new_chunks}, new_embeddings={new_embeddings}")


if __name__ == "__main__":
    load_samples()



