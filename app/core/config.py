from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PORT: int = 8000  # Puerto por defecto
    HOST: str = "0.0.0.0"  # Host por defecto para producción

    class Config:
        env_file = ".env"

settings = Settings()

