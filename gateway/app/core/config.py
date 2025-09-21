from pydantic import BaseSettings, AnyHttpUrl, validator


class AppSettings(BaseSettings):
    APP_NAME: str = "gateway"
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # External/internal service endpoints
    MARKET_DATA_BASE_URL: AnyHttpUrl = "http://market_data:8000"
    RAG_BASE_URL: AnyHttpUrl = "http://rag:8000"

    # Timezone and timeouts
    DEFAULT_TZ: str = "UTC"
    REQUEST_TIMEOUT_SECONDS: int = 10

    @validator("REQUEST_TIMEOUT_SECONDS")
    def _validate_timeout(cls, v: int) -> int:
        return max(1, v)

    class Config:
        env_file = ".env"


settings = AppSettings()
