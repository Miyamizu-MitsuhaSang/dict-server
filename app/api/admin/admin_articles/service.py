import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
import re

from tortoise.queryset import QuerySet

from app.api.admin.admin_articles.admin_articles_schemas import ArticleCreatePayload, ArticleUpdatePayload
from app.core.redis import redis_delete
from app.models.articles import Article, ArticlePicture, ArticleTag, Banner
from app.utils.article_content import sanitize_html, strip_html_tags
from settings import ROOT_DIR

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
TEMP_IMAGE_URL_PREFIX = "/media/article/temp/"


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


def _extract_temp_urls(text: str | None) -> list[str]:
    if not text:
        return []
    pattern = re.compile(r"/media/article/temp/[A-Za-z0-9_./-]+")
    return list(dict.fromkeys(pattern.findall(text)))


def _move_temp_file_to_content(article_id: str, temp_url: str) -> str:
    temp_file = ROOT_DIR / temp_url.lstrip("/")
    if not temp_file.exists():
        return temp_url

    ext = temp_file.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return temp_url

    folder_name = datetime.now().strftime("%Y%m")
    relative_dir = Path("article/content") / folder_name
    absolute_dir = ROOT_DIR / "media" / relative_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)

    safe_article_id = article_id.replace("-", "")
    unique = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    save_name = f"content_{safe_article_id}_{timestamp}_{unique}{ext}"

    relative_path = (relative_dir / save_name).as_posix()
    absolute_path = absolute_dir / save_name
    temp_file.replace(absolute_path)
    return f"/media/{relative_path}"


async def _sync_promoted_pictures(article: Article, promoted_urls: list[str], cover_url: str | None) -> None:
    if not promoted_urls and not cover_url:
        return

    existing_paths = set(await ArticlePicture.filter(article=article).values_list("pic_path", flat=True))

    if cover_url and cover_url.startswith("/media/"):
        cover_path = cover_url.replace("/media/", "", 1)
        old_cover = await ArticlePicture.get_or_none(article=article, is_cover=True)
        if old_cover:
            old_cover.pic_path = cover_path
            old_cover.sequence = 0
            await old_cover.save(update_fields=["pic_path", "sequence"])
        elif cover_path not in existing_paths:
            await ArticlePicture.create(article=article, pic_path=cover_path, is_cover=True, sequence=0)
            existing_paths.add(cover_path)

    last_pic = await ArticlePicture.filter(article=article, is_cover=False).order_by("-sequence").first()
    sequence = (last_pic.sequence if last_pic else 0) + 1
    for url in promoted_urls:
        if not url.startswith("/media/"):
            continue
        pic_path = url.replace("/media/", "", 1)
        if pic_path in existing_paths:
            continue
        await ArticlePicture.create(article=article, pic_path=pic_path, is_cover=False, sequence=sequence)
        existing_paths.add(pic_path)
        sequence += 1


async def promote_temp_images_for_article(
        article: Article,
        cover_url: str | None,
        content_html: str,
) -> tuple[str | None, str]:
    temp_urls = _extract_temp_urls(content_html)
    if cover_url and cover_url.startswith(TEMP_IMAGE_URL_PREFIX):
        temp_urls = list(dict.fromkeys([cover_url] + temp_urls))

    if not temp_urls:
        return cover_url, content_html

    mapping: dict[str, str] = {}
    for temp_url in temp_urls:
        mapping[temp_url] = _move_temp_file_to_content(article.article_id, temp_url)

    resolved_cover = mapping.get(cover_url, cover_url) if cover_url else None
    resolved_html = content_html
    for old_url, new_url in mapping.items():
        resolved_html = resolved_html.replace(old_url, new_url)

    promoted_urls = [new for old, new in mapping.items() if old != new]
    await _sync_promoted_pictures(article, promoted_urls, resolved_cover)
    return resolved_cover, resolved_html


async def create_article(payload: ArticleCreatePayload) -> Article:
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
        content_html=payload.content_html,
        content_text=payload.content_text,
        tags=final_tags,
        category=payload.category,
        status=payload.status,
        publish_at=final_publish_at,
    )

    resolved_cover, resolved_html = await promote_temp_images_for_article(
        article=article,
        cover_url=payload.cover_url,
        content_html=payload.content_html,
    )
    cleaned_html = sanitize_html(resolved_html)
    final_text = payload.content_text or strip_html_tags(cleaned_html)

    article.cover_url = resolved_cover
    article.content_html = cleaned_html
    article.content_text = final_text
    await article.save(update_fields=["cover_url", "content_html", "content_text"])

    await refresh_tag_usage_counts()
    return article


async def update_article(article_id: str, payload: ArticleUpdatePayload) -> Article:
    article = await Article.get(article_id=article_id)

    final_publish_at = payload.publish_at

    # 如果从草稿切到发布，且没给发布时间，就补当前时间
    if payload.status == "published" and final_publish_at is None:
        final_publish_at = article.publish_at or datetime.now()

    final_tags = normalize_tags(payload.tags)
    await ensure_tags_exist(final_tags)

    resolved_cover, resolved_html = await promote_temp_images_for_article(
        article=article,
        cover_url=payload.cover_url,
        content_html=payload.content_html,
    )
    cleaned_html = sanitize_html(resolved_html)
    final_text = payload.content_text or strip_html_tags(cleaned_html)

    article.title = payload.title.strip()
    article.summary = payload.summary.strip() if payload.summary else None
    article.source = payload.source.strip() if payload.source else None
    article.cover_url = resolved_cover
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


async def upload_article_content_images(
        article_id: str,
        files: list[tuple[str, bytes]],
) -> list[dict]:
    article = await Article.get(article_id=article_id)

    folder_name = datetime.now().strftime("%Y%m")
    relative_dir = Path("article/content") / folder_name
    absolute_dir = ROOT_DIR / "media" / relative_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)

    last_pic = await ArticlePicture.filter(article=article, is_cover=False).order_by("-sequence").first()
    start_sequence = (last_pic.sequence if last_pic else 0) + 1

    safe_article_id = article.article_id.replace("-", "")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    results: list[dict] = []
    for idx, (filename, content) in enumerate(files):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"文件 {filename} 格式不支持，仅支持 jpg/jpeg/png/webp/gif")

        unique = uuid.uuid4().hex[:8]
        save_name = f"content_{safe_article_id}_{timestamp}_{idx}_{unique}{ext}"
        relative_path = (relative_dir / save_name).as_posix()
        absolute_path = absolute_dir / save_name
        absolute_path.write_bytes(content)

        sequence = start_sequence + idx
        pic = await ArticlePicture.create(
            article=article,
            pic_path=relative_path,
            is_cover=False,
            sequence=sequence,
        )

        results.append({
            "pic_id": pic.pic_id,
            "image_url": f"/media/{relative_path}",
            "sequence": sequence,
        })

    return results


async def upload_article_temp_images(files: list[tuple[str, bytes]]) -> list[str]:
    folder_name = datetime.now().strftime("%Y%m")
    relative_dir = Path("article/temp") / folder_name
    absolute_dir = ROOT_DIR / "media" / relative_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    urls: list[str] = []
    for idx, (filename, content) in enumerate(files):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"文件 {filename} 格式不支持，仅支持 jpg/jpeg/png/webp/gif")
        unique = uuid.uuid4().hex[:8]
        save_name = f"temp_{timestamp}_{idx}_{unique}{ext}"
        relative_path = (relative_dir / save_name).as_posix()
        absolute_path = absolute_dir / save_name
        absolute_path.write_bytes(content)
        urls.append(f"/media/{relative_path}")
    return urls


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
