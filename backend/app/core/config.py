from pydantic_settings import BaseSettings
from typing import List, Union
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "HomeNews API"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = []

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./homenews.db")

    # Secrets
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        case_sensitive = True


settings = Settings()
