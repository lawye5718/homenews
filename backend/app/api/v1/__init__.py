"""API v1 router configuration."""
from fastapi import APIRouter

from app.api.v1.endpoints import news

router = APIRouter()
router.include_router(news.router, prefix="/news", tags=["news"])
