from pydantic import BaseSettings

class AppSettings(BaseSettings):
    APP_NAME: str = "market_data"
    APP_ENV: str = "dev"
    TZ: str = "UTC"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = ""
    REDIS_URL: str = ""
    OFFLINE: bool = False

    class Config:
        env_file = ".env"

settings = AppSettings()
