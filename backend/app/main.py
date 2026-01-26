from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import engine, Base
from app.api.v1 import router as api_v1_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield
    # Shutdown: Cleanup database connections
    engine.dispose()
    logger.info("Database connections disposed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )


app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root() -> dict:
    """Root endpoint returning basic project information."""
    return {"Hello": "World", "Project": "HomeNews"}


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "HomeNews API"}
