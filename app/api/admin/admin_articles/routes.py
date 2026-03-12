from typing import Tuple

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.params import Query
from tortoise.exceptions import DoesNotExist

from app.api.admin.admin_articles import service
from app.api.admin.admin_articles.admin_articles_schemas import ArticleActionResponse, ArticleCreatePayload, \
    ArticleUpdatePayload, ArticleDetailResponse, ArticleListResponse, ArticleItemResponse, ArticleCoverUploadResponse, \
    ArticleContentImageUploadResponse, ArticleContentImageItemResponse, ArticleTempImageUploadResponse, \
    ArticleTempImageItemResponse, ArticleTempImageDeletePayload, ArticleTempImageDeleteResponse, TagCreatePayload, \
    TagItemResponse, \
    TagListResponse, BannerSwitchPayload, BannerSwitchResponse, \
    ArticlePublishedStatusResponse, ArticleBannerStatusResponse
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


@admin_banner_router.get(
    "/{article_id}/published",
    response_model=ArticlePublishedStatusResponse,
    summary="查询文章发布状态",
)
async def get_article_published_status_api(article_id: str):
    try:
        status, is_published, publish_at = await service.get_article_publish_status(article_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")

    return ArticlePublishedStatusResponse(
        article_id=article_id,
        status=status,
        is_published=is_published,
        publish_at=publish_at,
    )


@admin_banner_router.get(
    "/{article_id}/banner",
    response_model=ArticleBannerStatusResponse,
    summary="查询文章轮播状态",
)
async def get_article_banner_status_api(article_id: str):
    try:
        has_banner, enabled, banner_id, sort_order, start_at, end_at = await service.get_article_banner_status(article_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")

    return ArticleBannerStatusResponse(
        article_id=article_id,
        has_banner=has_banner,
        enabled=enabled,
        banner_id=banner_id,
        sort_order=sort_order,
        start_at=start_at,
        end_at=end_at,
    )

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


@admin_banner_router.post(
    "/upload-temp-images",
    response_model=ArticleTempImageUploadResponse,
    summary="临时上传文章图片（多图，无需 article_id）",
)
async def upload_article_temp_images_api(
        files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")

    prepared_files: list[tuple[str, bytes]] = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="存在缺少文件名的图片")
        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 不是图片")
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 内容为空")
        prepared_files.append((file.filename, content))

    try:
        urls = await service.upload_article_temp_images(prepared_files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ArticleTempImageUploadResponse(
        message="临时图片上传成功",
        images=[ArticleTempImageItemResponse(image_url=url) for url in urls],
    )


@admin_banner_router.delete(
    "/upload-temp-images",
    response_model=ArticleTempImageDeleteResponse,
    summary="删除临时上传文章图片（多图）",
)
async def delete_article_temp_images_api(payload: ArticleTempImageDeletePayload):
    deleted_urls, skipped_urls = await service.delete_article_temp_images(payload.image_urls)
    return ArticleTempImageDeleteResponse(
        message="临时图片删除完成",
        deleted_urls=deleted_urls,
        skipped_urls=skipped_urls,
    )


@admin_banner_router.post(
    "/{article_id}/content-images/upload",
    response_model=ArticleContentImageUploadResponse,
    summary="上传正文图片（多图）",
)
async def upload_article_content_images_api(
        article_id: str,
        files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")

    prepared_files: list[tuple[str, bytes]] = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="存在缺少文件名的图片")
        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 不是图片")
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 内容为空")
        prepared_files.append((file.filename, content))

    try:
        uploaded = await service.upload_article_content_images(article_id, prepared_files)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="文章不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ArticleContentImageUploadResponse(
        message="正文图片上传成功",
        article_id=article_id,
        images=[ArticleContentImageItemResponse(**item) for item in uploaded],
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
