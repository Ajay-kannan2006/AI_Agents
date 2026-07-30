import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Research Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8002
    HOST: str = "0.0.0.0"

    OPENAI_API_KEY: str = "mock-key-for-testing"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_API_BASE: str = "https://api.openai.com/v1"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/storage.db"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
