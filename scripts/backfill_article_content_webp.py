import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tortoise import Tortoise
from tortoise.transactions import in_transaction

from app.api.admin.admin_articles.service import normalize_content_image_urls
from app.models.articles import Article, ArticlePicture
from app.utils.media_image import build_optimized_content_image_url
from settings import ONLINE_SETTINGS, ROOT_DIR


def backup_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    directory = ROOT_DIR / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"article-content-webp-backfill-{timestamp}.jsonl"


async def main() -> None:
    await Tortoise.init(config=ONLINE_SETTINGS)
    backup_file = backup_path()
    converted_articles = 0
    converted_pictures = 0
    skipped_articles = 0

    try:
        with backup_file.open("x", encoding="utf-8") as backup:
            articles = await Article.all().order_by("article_id")
            for article in articles:
                original_html = article.content_html
                normalized_html = normalize_content_image_urls(original_html)
                pictures = await ArticlePicture.filter(article=article, is_cover=False)
                picture_updates: list[tuple[ArticlePicture, str]] = []
                for picture in pictures:
                    original_url = f"/media/{picture.pic_path}"
                    optimized_url = build_optimized_content_image_url(original_url)
                    if optimized_url and optimized_url != original_url:
                        picture_updates.append((picture, optimized_url.removeprefix("/media/")))

                if normalized_html == original_html and not picture_updates:
                    continue

                backup.write(json.dumps({
                    "article_id": article.article_id,
                    "content_html": original_html,
                    "article_pics": {
                        picture.pic_id: picture.pic_path for picture, _ in picture_updates
                    },
                }, ensure_ascii=False) + "\n")
                backup.flush()

                async with in_transaction() as connection:
                    updated_count = await Article.filter(
                        article_id=article.article_id,
                        content_html=original_html,
                    ).using_db(connection).update(content_html=normalized_html)
                    if updated_count != 1:
                        skipped_articles += 1
                        continue

                    for picture, optimized_path in picture_updates:
                        await ArticlePicture.filter(pic_id=picture.pic_id).using_db(connection).update(
                            pic_path=optimized_path,
                        )
                    converted_articles += 1
                    converted_pictures += len(picture_updates)
    finally:
        await Tortoise.close_connections()

    print(f"backup={backup_file}")
    print(f"converted_articles={converted_articles}")
    print(f"converted_pictures={converted_pictures}")
    print(f"skipped_articles={skipped_articles}")


if __name__ == "__main__":
    asyncio.run(main())
