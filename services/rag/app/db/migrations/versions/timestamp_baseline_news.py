"""baseline news/chunks/embeddings

Revision ID: 0001_news_baseline
Revises: 
Create Date: 2025-09-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy


revision = '0001_news_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        'news',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_news_ticker', 'news', ['ticker'])
    op.create_index('ix_news_published_at', 'news', ['published_at'])
    op.create_index('ix_news_first_seen_at', 'news', ['first_seen_at'])

    op.create_table(
        'news_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('news_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('news.id'), nullable=False),
        sa.Column('chunk_idx', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
    )
    op.create_index('ix_news_chunks_news_id', 'news_chunks', ['news_id'])
    op.create_index('ix_news_chunks_news_id_chunk_idx', 'news_chunks', ['news_id', 'chunk_idx'], unique=True)

    op.create_table(
        'news_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('news_chunks.id'), nullable=False, unique=True),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(384)),
    )
    op.create_index('ix_news_embeddings_chunk_id', 'news_embeddings', ['chunk_id'], unique=True)

    # Create ivfflat index if available
    try:
        op.execute("CREATE INDEX IF NOT EXISTS ix_news_embeddings_embedding ON news_embeddings USING ivfflat (embedding vector_cosine_ops);")
    except Exception:
        # fallback: skip index creation if not supported
        pass


def downgrade() -> None:
    op.drop_index('ix_news_embeddings_embedding', table_name='news_embeddings')
    op.drop_table('news_embeddings')
    op.drop_index('ix_news_chunks_news_id_chunk_idx', table_name='news_chunks')
    op.drop_index('ix_news_chunks_news_id', table_name='news_chunks')
    op.drop_table('news_chunks')
    op.drop_index('ix_news_first_seen_at', table_name='news')
    op.drop_index('ix_news_published_at', table_name='news')
    op.drop_index('ix_news_ticker', table_name='news')
    op.drop_table('news')


