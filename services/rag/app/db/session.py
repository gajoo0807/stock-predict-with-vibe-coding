from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 建立 Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def get_db_session():
    """FastAPI 依賴注入用"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_extensions(engine):
    """
    確保 Postgres 所需 extension 存在，例如 pgvector
    在 fallback create_all 時會呼叫
    """
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # 如果未來需要全文檢索或中文支援，可以在這裡加：
        # conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        # conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))


def create_all_with_extensions(engine):
    """
    在 Alembic 無法使用時，直接建立所有表，並確保 extension 存在
    """
    init_extensions(engine)
    Base.metadata.create_all(bind=engine)



