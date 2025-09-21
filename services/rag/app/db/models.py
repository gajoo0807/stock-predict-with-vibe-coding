import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base


class News(Base):
    __tablename__ = "news"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String, index=True, nullable=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), index=True, nullable=True)
    source = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    first_seen_at = Column(DateTime(timezone=True), index=True, nullable=True)

    chunks = relationship("NewsChunk", back_populates="news", cascade="all, delete-orphan")


class NewsChunk(Base):
    __tablename__ = "news_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    news_id = Column(UUID(as_uuid=True), ForeignKey("news.id"), index=True, nullable=False)
    chunk_idx = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    news = relationship("News", back_populates="chunks")
    embedding = relationship("NewsEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_news_chunks_news_id_chunk_idx", "news_id", "chunk_idx", unique=True),
    )


class NewsEmbedding(Base):
    __tablename__ = "news_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("news_chunks.id"), unique=True, nullable=False)
    embedding = Column(Vector(384))

    chunk = relationship("NewsChunk", back_populates="embedding")

    __table_args__ = (
        Index("ix_news_embeddings_chunk_id", "chunk_id", unique=True),
    )


