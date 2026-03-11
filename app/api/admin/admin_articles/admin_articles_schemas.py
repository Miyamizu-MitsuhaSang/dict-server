from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ArticleStatus = Literal["draft", "published"]


class ArticleBasePayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    summary: str | None = None
    source: str | None = None
    cover_url: str | None = Field(default=None, max_length=500)

    content_html: str = Field(..., min_length=1)
    content_text: str | None = None

    tags: list[str] = Field(default_factory=list)
    category: str | None = Field(default=None, max_length=50)

    status: ArticleStatus = "draft"
    publish_at: datetime | None = None


class ArticleCreatePayload(ArticleBasePayload):
    pass


class ArticleUpdatePayload(ArticleBasePayload):
    pass


class ArticleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_id: str
    title: str
    summary: str | None = None
    source: str | None = None
    cover_url: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: str
    publish_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


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
    status: str
    publish_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ArticleListResponse(BaseModel):
    items: list[ArticleItemResponse]
    total: int


class ArticleActionResponse(BaseModel):
    message: str
    article_id: str


class ArticleCoverUploadResponse(BaseModel):
    message: str
    article_id: str
    cover_url: str
    pic_id: str


class TagCreatePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class TagItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tag_id: str
    name: str
    created_at: datetime
    updated_at: datetime


class TagListResponse(BaseModel):
    items: list[TagItemResponse]
    total: int


class BannerSwitchPayload(BaseModel):
    enabled: bool
    title: str | None = Field(default=None, max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    target_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = 0
    start_at: datetime | None = None
    end_at: datetime | None = None


class BannerSwitchResponse(BaseModel):
    message: str
    article_id: str
    banner_id: int | None = None
    enabled: bool
