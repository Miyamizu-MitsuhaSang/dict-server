from app.api.culture_share import service as culture_service
from app.api.culture_share.culture_share_schemas import ArticleListItem, PopularTagItem
from app.api.miniapp.miniapp_schemas import QuickEntryItem
from app.utils.media_image import build_optimized_cover_thumb_url

DEFAULT_QUICK_ENTRIES = [
    QuickEntryItem(
        key="search",
        title="查词",
        subtitle="法语 / 日语词条检索",
        target_page="/pages/search/index",
    ),
    QuickEntryItem(
        key="ai_assist",
        title="AI 助手",
        subtitle="围绕当前词继续追问",
        target_page="/pages/ai/index",
    ),
    QuickEntryItem(
        key="culture",
        title="文化分享",
        subtitle="精选文章与标签入口",
        target_page="/pages/home/index",
    ),
]


async def get_miniapp_home_payload(redis_client):
    banners = await culture_service.get_active_banners_with_cache(redis_client, limit=4)
    tags, _ = await culture_service.get_top_used_tags(limit=8)
    articles, _ = await culture_service.list_published_articles(page=1, page_size=6)
    featured_articles = []
    for article in articles:
        data = ArticleListItem.model_validate(article).model_dump(mode="json")
        optimized_cover_url = build_optimized_cover_thumb_url(data.get("cover_url"))
        if optimized_cover_url:
            data["cover_url"] = optimized_cover_url
        featured_articles.append(data)

    return {
        "banners": banners,
        "hot_tags": [PopularTagItem.model_validate(item).model_dump(mode="json") for item in tags],
        "featured_articles": featured_articles,
        "quick_entries": [item.model_dump(mode="json") for item in DEFAULT_QUICK_ENTRIES],
    }
