from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./degaritao-dev.db'
    jwt_secret: str = Field(min_length=32)
    jwt_expires_minutes: int = Field(default=60, ge=5, le=1440)
    allowed_origins: str = 'http://localhost:5173,http://localhost:8080'
    environment: str = 'development'

@lru_cache

def get_settings() -> Settings:
    return Settings()
