import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

from tortoise.queryset import QuerySet

from app.api.admin.admin_articles.admin_articles_schemas import ArticleCreatePayload, ArticleUpdatePayload
from app.core.redis import redis_delete
from app.models.articles import Article, ArticlePicture, ArticleTag, Banner
from app.utils.article_content import sanitize_html, strip_html_tags
from settings import ROOT_DIR

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def normalize_tags(tags: list[str]) -> list[str]:
    # 去空白、去重，保留用户输入顺序
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in tags:
        tag = raw.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized


async def ensure_tags_exist(tags: list[str]) -> None:
    for tag_name in tags:
        await ArticleTag.get_or_create(name=tag_name)


async def refresh_tag_usage_counts() -> None:
    rows = await Article.all().values_list("tags", flat=True)
    counter: Counter[str] = Counter()
    for tags in rows:
        if not isinstance(tags, list):
            continue
        for tag_name in normalize_tags(tags):
            counter[tag_name] += 1

    # 确保文章里出现过的 tag 在 tag 表中存在
    for tag_name in counter:
        await ArticleTag.get_or_create(name=tag_name)

    await ArticleTag.all().update(usage_count=0)
    for tag_name, cnt in counter.items():
        await ArticleTag.filter(name=tag_name).update(usage_count=cnt)

async def clear_banner_cache():
    for limit in range(1, 11):
        await redis_delete(f"home:banners:{limit}")


async def create_article(payload: ArticleCreatePayload) -> Article:
    cleaned_html = sanitize_html(payload.content_html)

    # 如果前端没传 content_text，就后端自动提取
    final_text = payload.content_text or strip_html_tags(cleaned_html)

    # 如果状态是 published，但 publish_at 没传，就自动补当前时间
    final_publish_at = payload.publish_at
    if payload.status == "published" and final_publish_at is None:
        final_publish_at = datetime.now()

    final_tags = normalize_tags(payload.tags)
    await ensure_tags_exist(final_tags)

    article = await Article.create(
        title=payload.title.strip(),
        summary=payload.summary.strip() if payload.summary else None,
        source=payload.source.strip() if payload.source else None,
        cover_url=payload.cover_url,
        content_html=cleaned_html,
        content_text=final_text,
        tags=final_tags,
        category=payload.category,
        status=payload.status,
        publish_at=final_publish_at,
    )
    await refresh_tag_usage_counts()
    return article


async def update_article(article_id: str, payload: ArticleUpdatePayload) -> Article:
    article = await Article.get(article_id=article_id)

    cleaned_html = sanitize_html(payload.content_html)
    final_text = payload.content_text or strip_html_tags(cleaned_html)

    final_publish_at = payload.publish_at

    # 如果从草稿切到发布，且没给发布时间，就补当前时间
    if payload.status == "published" and final_publish_at is None:
        final_publish_at = article.publish_at or datetime.now()

    final_tags = normalize_tags(payload.tags)
    await ensure_tags_exist(final_tags)

    article.title = payload.title.strip()
    article.summary = payload.summary.strip() if payload.summary else None
    article.source = payload.source.strip() if payload.source else None
    article.cover_url = payload.cover_url
    article.content_html = cleaned_html
    article.content_text = final_text
    article.tags = final_tags
    article.category = payload.category
    article.status = payload.status
    article.publish_at = final_publish_at

    await article.save()
    await refresh_tag_usage_counts()
    return article


async def publish_article(article_id: int) -> Article:
    article = await Article.get(article_id=article_id)

    article.status = "published"
    if article.publish_at is None:
        article.publish_at = datetime.now()

    await article.save()
    return article


async def unpublish_article(article_id: str) -> Article:
    article = await Article.get(article_id=article_id)
    article.status = "draft"
    await article.save()
    return article


async def get_article_publish_status(article_id: str) -> tuple[str, bool, datetime | None]:
    article = await Article.get(article_id=article_id)
    return article.status, article.status == "published", article.publish_at


async def get_article_banner_status(article_id: str) -> tuple[bool, bool, int | None, int | None, datetime | None, datetime | None]:
    article = await Article.get(article_id=article_id)
    banner = await Banner.get_or_none(article=article)
    if not banner:
        return False, False, None, None, None, None
    return True, banner.is_active, banner.id, banner.sort_order, banner.start_at, banner.end_at


async def get_article_detail(article_id: int) -> Article:
    return await Article.get(article_id=article_id)


async def list_articles(
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
        category: str | None = None,
        keyword: str | None = None,
) -> tuple[list[Article], int]:
    qs: QuerySet[Article] = Article.all()

    if status:
        qs = qs.filter(status=status)

    if category:
        qs = qs.filter(category=category)

    if keyword:
        qs = qs.filter(title__icontains=keyword)

    total = await qs.count()

    offset = (page - 1) * page_size
    items = await qs.offset(offset).limit(page_size)

    return items, total


async def upload_article_cover(article_id: str, filename: str, content: bytes) -> tuple[str, str]:
    article = await Article.get(article_id=article_id)

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("仅支持 jpg/jpeg/png/webp/gif 图片格式")

    folder_name = datetime.now().strftime("%Y%m")
    relative_dir = Path("article/covers") / folder_name
    absolute_dir = ROOT_DIR / "media" / relative_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)

    safe_article_id = article.article_id.replace("-", "")
    unique = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    save_name = f"cover_{safe_article_id}_{timestamp}_{unique}{ext}"

    relative_path = (relative_dir / save_name).as_posix()
    absolute_path = absolute_dir / save_name
    absolute_path.write_bytes(content)

    cover_url = f"/media/{relative_path}"

    old_cover = await ArticlePicture.get_or_none(article=article, is_cover=True)
    if old_cover and old_cover.pic_path:
        old_file = ROOT_DIR / "media" / old_cover.pic_path
        if old_file.exists():
            old_file.unlink()

    if old_cover:
        old_cover.pic_path = relative_path
        old_cover.sequence = 0
        await old_cover.save(update_fields=["pic_path", "sequence"])
        pic_id = old_cover.pic_id
    else:
        new_cover = await ArticlePicture.create(
            article=article,
            pic_path=relative_path,
            is_cover=True,
            sequence=0,
        )
        pic_id = new_cover.pic_id

    article.cover_url = cover_url
    await article.save(update_fields=["cover_url"])

    return cover_url, pic_id


async def search_tags(keyword: str | None = None, limit: int = 20) -> tuple[list[ArticleTag], int]:
    qs = ArticleTag.all()
    if keyword:
        qs = qs.filter(name__icontains=keyword.strip())
    total = await qs.count()
    items = await qs.order_by("name").limit(limit)
    return items, total


async def create_tag(name: str) -> ArticleTag:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("tag 名称不能为空")
    tag, _ = await ArticleTag.get_or_create(name=cleaned)
    if tag.usage_count is None:
        tag.usage_count = 0
        await tag.save(update_fields=["usage_count"])
    return tag


async def switch_article_banner(
        article_id: str,
        enabled: bool,
        title: str | None = None,
        subtitle: str | None = None,
        image_url: str | None = None,
        target_url: str | None = None,
        sort_order: int | None = 0,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
) -> tuple[int | None, bool]:
    article = await Article.get(article_id=article_id)
    existing_banner = await Banner.get_or_none(article=article)

    if enabled:
        # 最多允许 4 个激活轮播；若当前文章已激活则允许更新
        if not existing_banner or not existing_banner.is_active:
            active_cnt = await Banner.filter(is_active=True).count()
            if active_cnt >= 4:
                raise ValueError("当前已存在4个轮播，请先取消其他文章的轮播后再开启")

        final_title = (title.strip() if title else article.title).strip()
        final_subtitle = subtitle.strip() if subtitle else article.summary
        final_image_url = image_url or article.cover_url
        final_target_url = target_url or f"/culture_share/article/{article.article_id}"
        final_sort_order = sort_order if sort_order is not None else 0

        banner = existing_banner
        if banner:
            banner.title = final_title
            banner.subtitle = final_subtitle
            banner.image_url = final_image_url
            banner.target_url = final_target_url
            banner.sort_order = final_sort_order
            banner.start_at = start_at
            banner.end_at = end_at
            banner.is_active = True
            await banner.save()
        else:
            banner = await Banner.create(
                title=final_title,
                subtitle=final_subtitle,
                image_url=final_image_url,
                target_url=final_target_url,
                article=article,
                sort_order=final_sort_order,
                is_active=True,
                start_at=start_at,
                end_at=end_at,
            )

        await clear_banner_cache()
        return banner.id, True

    banners = await Banner.filter(article=article)
    banner_id: int | None = None
    if banners:
        banner_id = banners[0].id
        await Banner.filter(article=article).update(is_active=False)

    await clear_banner_cache()
    return banner_id, False


async def delete_article(article_id: str) -> str:
    article = await Article.get(article_id=article_id)

    pic_paths = await ArticlePicture.filter(article=article).values_list("pic_path", flat=True)
    for pic_path in pic_paths:
        if not pic_path:
            continue
        old_file = ROOT_DIR / "media" / pic_path
        if old_file.exists():
            old_file.unlink()

    if article.cover_url and article.cover_url.startswith("/media/"):
        cover_file = ROOT_DIR / article.cover_url.lstrip("/")
        if cover_file.exists():
            cover_file.unlink()

    await Banner.filter(article=article).delete()
    await article.delete()

    await clear_banner_cache()
    await refresh_tag_usage_counts()
    return article_id
