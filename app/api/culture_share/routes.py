from typing import Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from starlette.requests import Request
from tortoise.exceptions import DoesNotExist

from app.api.culture_share import service
from app.api.culture_share.culture_share_schemas import (
    ArticleDetailResponse,
    ArticleListItem,
    ArticleListResponse,
    BannerResponse,
    PopularTagItem,
    PopularTagResponse,
)
from app.models import User
from app.utils.security import get_current_user

culture_share_router = APIRouter()


@culture_share_router.get(
    "/banners",
    description="主页轮播窗口展示",
    response_model=BannerResponse,
)
async def show_in_index_page(
        request: Request,
        limit: int = Query(default=4, ge=2, le=5)
):
    """
    展示的文章由管理后台指定，计划展示 4 篇，如果不足 4 篇则展示最新的
    :return:
    """
    redis_client = request.app.state.redis
    items = await service.get_active_banners_with_cache(redis_client, limit)

    return BannerResponse(
        article_list=items,
        article_cnt=len(items),
    )


@culture_share_router.get(
    "/article/list",
    response_model=ArticleListResponse,
    description="前端文章分页列表，仅返回已发布文章",
)
async def list_articles(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1, le=50),
        category: str | None = Query(default=None),
        keyword: str | None = Query(default=None),
        _user: Tuple[User, Dict] = Depends(get_current_user),
):
    items, total = await service.list_published_articles(
        page=page,
        page_size=page_size,
        category=category,
        keyword=keyword,
    )

    return ArticleListResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[ArticleListItem.model_validate(item) for item in items],
    )


@culture_share_router.get(
    "/article/{article_id}",
    response_model=ArticleDetailResponse,
    description="前端文章详情，仅返回已发布文章",
)
async def get_article_detail(
        article_id: str,
        _user: Tuple[User, Dict] = Depends(get_current_user),
):
    try:
        article = await service.get_published_article_detail(article_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在或未发布")

    return ArticleDetailResponse.model_validate(article)


@culture_share_router.get(
    "/tags",
    response_model=PopularTagResponse,
    description="前端高频标签列表（按使用文章数量降序）",
)
async def get_popular_tags(
        limit: int = Query(default=10, ge=1, le=100),
        _user: Tuple[User, Dict] = Depends(get_current_user),
):
    items, total = await service.get_top_used_tags(limit=limit)
    return PopularTagResponse(
        total=total,
        items=[PopularTagItem.model_validate(item) for item in items],
    )
