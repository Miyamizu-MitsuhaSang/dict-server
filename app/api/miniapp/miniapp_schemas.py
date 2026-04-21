from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.api.culture_share.culture_share_schemas import BannerArticle, ArticleListItem, PopularTagItem


class QuickEntryItem(BaseModel):
    key: str
    title: str
    subtitle: str
    target_page: str


class MiniappHomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    banners: List[BannerArticle]
    hot_tags: List[PopularTagItem]
    featured_articles: List[ArticleListItem]
    quick_entries: List[QuickEntryItem] = Field(default_factory=list)
