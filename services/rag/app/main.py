import os
import subprocess
import logging
from pathlib import Path

from fastapi import FastAPI
from app.core.config import settings
from app.api.routers import router as api_router
from app.db.session import engine, create_all_with_extensions

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# 關閉 tokenizers 平行化避免 fork 警告/死鎖
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def run_migrations_or_fallback() -> None:
    """
    先嘗試 Alembic 升級；失敗則建立必要的 extension 與所有表。
    """
    # 以 services/rag 為工作目錄（alembic.ini 放在 app/ 目錄底下）
    project_root = Path(__file__).resolve().parents[1]  # .../services/rag
    alembic_cfg = "app/alembic.ini"
    alembic_path = project_root / alembic_cfg

    try:
        if not alembic_path.exists():
            raise FileNotFoundError(f"Alembic config not found: {alembic_path}")

        subprocess.run(
            ["alembic", "-c", alembic_cfg, "upgrade", "head"],
            check=True,
            cwd=str(project_root),
        )
        logger.info("[MIGRATION] Alembic upgrade head succeeded")
    except Exception as exc:
        logger.warning("[MIGRATION] Alembic upgrade failed: %s", exc)
        try:
            # Fallback：確保 pgvector extension 後建立所有表
            create_all_with_extensions(engine)
            logger.info("[MIGRATION] Fallback create_all_with_extensions executed")
        except Exception as exc2:
            logger.error("[MIGRATION] Fallback failed: %s", exc2)
            # 不中斷服務運行，但後續操作可能取不到表；保留錯誤日誌讓測試可定位


@app.on_event("startup")
async def on_startup():
    run_migrations_or_fallback()


# 路由
app.include_router(api_router)

# （可選）簡單健康檢查，若已在 routers 內定義可移除
@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": settings.APP_NAME}


