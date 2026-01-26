from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Use database URL from settings instead of hardcoding
engine = create_engine(
    settings.DATABASE_URL,
    # Note: check_same_thread=False is required for SQLite with FastAPI
    # This allows SQLite to be accessed from multiple threads
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
