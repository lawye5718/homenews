from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NewsSource(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    url: str
    category: Optional[str] = None
    language: str = "en"
    country: Optional[str] = None

    class Config:
        from_attributes = True


class NewsArticle(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: str
    url_to_image: Optional[str] = None
    published_at: datetime
    source: NewsSource
    author: Optional[str] = None
    tags: Optional[list[str]] = []

    class Config:
        from_attributes = True
