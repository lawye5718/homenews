from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Determine connect_args based on database type (only needed for SQLite)
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# Use database URL from settings instead of hardcoding
engine = create_engine(
    settings.DATABASE_URL,
    # Note: check_same_thread=False is required for SQLite with FastAPI
    # This allows SQLite to be accessed from multiple threads
    connect_args=_connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
