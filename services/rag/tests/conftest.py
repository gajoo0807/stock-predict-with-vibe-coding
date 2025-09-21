# services/<service>/tests/conftest.py
import os
import sys
from pathlib import Path
import pytest

# 將該服務根目錄（含 app/）加入匯入路徑
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

# 讓本機 pytest 使用 localhost 的 Postgres，而非 Docker 內部的 host 名稱
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/market")
os.environ.setdefault("EMBEDDING_BACKEND", "local")


@pytest.fixture(scope="session", autouse=True)
def _ensure_db_schema():
    # 延遲載入以套用上面的環境變數
    from sqlalchemy import text
    from app.db.session import engine, Base
    # 建立 pgvector 擴充後再建表
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    yield
