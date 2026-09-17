from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MAPIS"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-this-in-production"

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./mapis.db"

    # Trust thresholds (0.0 = fully trusted, 1.0 = fully malicious)
    TRUST_BLOCK_THRESHOLD: float = 0.3   # block if trust score BELOW this
    TRUST_WARN_THRESHOLD: float = 0.6    # warn if trust score BELOW this
    SESSION_HISTORY_LIMIT: int = 50      # max messages remembered per session

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
