from pydantic import BaseSettings

class AppSettings(BaseSettings):
    APP_NAME: str = "rag"
    APP_ENV: str = "dev"
    TZ: str = "UTC"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = ""
    REDIS_URL: str = ""

    class Config:
        env_file = ".env"

settings = AppSettings()

