from datetime import datetime

from redis.asyncio import Redis
from tortoise.expressions import Q

from app.api.culture_share.culture_share_schemas import BannerArticle
from app.core.redis import redis_get_json, redis_set_json
from app.models.articles import Article, ArticleTag, Banner
from app.utils.media_image import build_optimized_banner_image_url


async def get_active_banners_with_cache(
        redis_client: Redis,
        limit: int = 4
) -> list[BannerArticle]:
    cache_key = f"home:banners:{limit}"

    cached_data = await redis_get_json(cache_key)
    if cached_data is not None:
        return cached_data

    now = datetime.now()

    banners = await Banner.filter(
        is_active=True
    ).filter(
        Q(start_at__isnull=True) | Q(start_at__lte=now)
    ).filter(
        Q(end_at__isnull=True) | Q(end_at__gte=now)
    ).order_by(
        "sort_order", "-created_at"
    ).limit(limit)

    items = []
    for banner in banners:
        data = BannerArticle.model_validate(banner).model_dump(mode="json")
        optimized_url = build_optimized_banner_image_url(data.get("image_url"))
        if optimized_url:
            data["image_url"] = optimized_url
        items.append(data)

    await redis_set_json(cache_key, items, ex=300)

    return items


async def list_published_articles(
        page: int = 1,
        page_size: int = 10,
        category: str | None = None,
        keyword: str | None = None,
) -> tuple[list[Article], int]:
    now = datetime.now()
    qs = Article.filter(status="published").filter(
        Q(publish_at__isnull=True) | Q(publish_at__lte=now)
    )

    if category:
        qs = qs.filter(category=category)

    if keyword:
        qs = qs.filter(title__icontains=keyword)

    total = await qs.count()
    offset = (page - 1) * page_size
    items = await qs.order_by("-publish_at", "-created_at").offset(offset).limit(page_size)

    return items, total


async def get_published_article_detail(article_id: str) -> Article:
    now = datetime.now()
    return await Article.filter(
        article_id=article_id,
        status="published",
    ).filter(
        Q(publish_at__isnull=True) | Q(publish_at__lte=now)
    ).get()


async def get_article_detail_for_admin(article_id: str) -> Article:
    return await Article.get(article_id=article_id)


async def get_top_used_tags(limit: int = 10) -> tuple[list[ArticleTag], int]:
    qs = ArticleTag.filter(usage_count__gt=0).order_by("-usage_count", "name")
    total = await qs.count()
    items = await qs.limit(limit)
    return items, total
