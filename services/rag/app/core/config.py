from pydantic import BaseSettings, Field

class AppSettings(BaseSettings):
    APP_NAME: str = "rag"
    APP_ENV: str = "dev"
    TZ: str = "UTC"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@db:5432/market"
    )
    REDIS_URL: str = ""
    OPENAI_API_KEY: str = ""
    EMBEDDING_BACKEND: str = Field(default="auto")  # auto|openai|local
    EMBEDDING_MODEL_LOCAL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2"
    )
    MAX_TOP_K: int = 10
    DEFAULT_TOP_K: int = 3
    REQUEST_TIMEOUT_SECONDS: int = 10

    class Config:
        env_file = ".env"

settings = AppSettings()

