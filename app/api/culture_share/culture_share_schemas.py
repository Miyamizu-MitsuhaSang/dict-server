from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class BannerArticle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subtitle: str | None = None
    image_url: str
    target_url: str
    sort_order: int
    is_active: bool
    start_at: datetime | None = None
    end_at: datetime | None = None


class BannerResponse(BaseModel):
    article_cnt: int
    article_list: List[BannerArticle]


class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_id: str
    title: str
    summary: str | None = None
    source: str | None = None
    cover_url: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    publish_at: datetime | None = None
    created_at: datetime


class ArticleListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ArticleListItem]


class ArticleDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_id: str
    title: str
    summary: str | None = None
    source: str | None = None
    cover_url: str | None = None
    content_html: str
    content_text: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    publish_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PopularTagItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tag_id: str
    name: str
    usage_count: int


class PopularTagResponse(BaseModel):
    total: int
    items: list[PopularTagItem]
