from typing import Tuple

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.params import Query
from tortoise.exceptions import DoesNotExist

from app.api.admin.admin_articles import service
from app.api.admin.admin_articles.admin_articles_schemas import ArticleActionResponse, ArticleCreatePayload, \
    ArticleUpdatePayload, ArticleDetailResponse, ArticleListResponse, ArticleItemResponse, ArticleCoverUploadResponse, \
    TagCreatePayload, TagItemResponse, TagListResponse, BannerSwitchPayload, BannerSwitchResponse
from app.models.base import User
from app.utils.security import is_admin_user

admin_banner_router = APIRouter()

@admin_banner_router.post(
    "/create_article",
    response_model=ArticleActionResponse,
    summary="创建文章",
)
async def create_article_api(payload: ArticleCreatePayload):
    article = await service.create_article(payload)
    return ArticleActionResponse(
        message="文章创建成功",
        article_id=article.article_id
    )

@admin_banner_router.put(
    "/{article_id}",
    response_model=ArticleActionResponse,
    summary="更新文章"
)
async def update_article_api(article_id: str, payload: ArticleUpdatePayload):
    try:
        article = await service.update_article(article_id, payload)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")

    return ArticleActionResponse(
        message="文章更新成功",
        article_id=article.article_id
    )

@admin_banner_router.post(
    "/{article_id}/publish",
    response_model=ArticleActionResponse,
    summary="发布文章"
)
async def publish_article_api(article_id: str):
    try:
        article = await service.publish_article(article_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")

    return ArticleActionResponse(
        message="文章发布成功",
        article_id=article.article_id
    )


@admin_banner_router.post(
    "/{article_id}/unpublish",
    response_model=ArticleActionResponse,
    summary="取消发布文章"
)
async def unpublish_article_api(article_id: str):
    try:
        article = await service.unpublish_article(article_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")

    return ArticleActionResponse(
        message="文章已撤回为草稿",
        article_id=article.article_id
    )


@admin_banner_router.delete(
    "/{article_id}",
    response_model=ArticleActionResponse,
    summary="删除文章"
)
async def delete_article_api(article_id: str):
    try:
        deleted_article_id = await service.delete_article(article_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")

    return ArticleActionResponse(
        message="文章删除成功",
        article_id=deleted_article_id
    )


@admin_banner_router.get("/{article_id}", response_model=ArticleDetailResponse, summary="获取文章详情")
async def get_article_detail_api(article_id: str):
    try:
        article = await service.get_article_detail(article_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")

    return ArticleDetailResponse.model_validate(article)

@admin_banner_router.get("", response_model=ArticleListResponse, summary="文章列表")
async def list_articles_api(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1, le=100),
        status: str | None = Query(default=None),
        category: str | None = Query(default=None),
        keyword: str | None = Query(default=None),
):
    items, total = await service.list_articles(
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        keyword=keyword,
    )

    return ArticleListResponse(
        items=[ArticleItemResponse.model_validate(item) for item in items],
        total=total,
    )


@admin_banner_router.post(
    "/{article_id}/cover/upload",
    response_model=ArticleCoverUploadResponse,
    summary="上传文章封面图",
)
async def upload_article_cover_api(
        article_id: str,
        file: UploadFile = File(...),
        _admin_user: Tuple[User, dict] = Depends(is_admin_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件必须是图片")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        cover_url, pic_id = await service.upload_article_cover(article_id, file.filename, content)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ArticleCoverUploadResponse(
        message="封面上传成功",
        article_id=article_id,
        cover_url=cover_url,
        pic_id=pic_id,
    )


@admin_banner_router.get(
    "/tag/search",
    response_model=TagListResponse,
    summary="搜索文章 tag",
)
async def search_tags_api(
        keyword: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
):
    items, total = await service.search_tags(keyword=keyword, limit=limit)
    return TagListResponse(
        items=[TagItemResponse.model_validate(item) for item in items],
        total=total,
    )


@admin_banner_router.post(
    "/tag",
    response_model=TagItemResponse,
    summary="新增文章 tag",
)
async def create_tag_api(payload: TagCreatePayload):
    try:
        tag = await service.create_tag(payload.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TagItemResponse.model_validate(tag)


@admin_banner_router.post(
    "/{article_id}/banner/switch",
    response_model=BannerSwitchResponse,
    summary="文章轮播开关",
)
async def switch_article_banner_api(article_id: str, payload: BannerSwitchPayload):
    try:
        banner_id, enabled = await service.switch_article_banner(
            article_id=article_id,
            enabled=payload.enabled,
            title=payload.title,
            subtitle=payload.subtitle,
            image_url=payload.image_url,
            target_url=payload.target_url,
            sort_order=payload.sort_order,
            start_at=payload.start_at,
            end_at=payload.end_at,
        )
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BannerSwitchResponse(
        message="轮播已开启" if enabled else "轮播已关闭",
        article_id=article_id,
        banner_id=banner_id,
        enabled=enabled,
    )
