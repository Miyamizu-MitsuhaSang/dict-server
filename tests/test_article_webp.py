import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.api.admin.admin_articles import service
from app.utils.media_image import (
    build_optimized_content_image_url,
    prepare_admin_image_upload,
)


def make_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (40, 30), "#4f8fba").save(output, format="PNG")
    return output.getvalue()


class ArticleWebpTests(unittest.TestCase):
    def test_new_article_image_upload_is_webp(self):
        prepared = prepare_admin_image_upload("article.png", make_png())

        self.assertEqual(prepared.filename_suffix, ".webp")
        with Image.open(BytesIO(prepared.content)) as image:
            self.assertEqual(image.format, "WEBP")

    def test_existing_content_image_gets_webp_url_without_removing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "media/article/content/202608/content_1.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(make_png())

            with patch("app.utils.media_image.ROOT_DIR", root):
                result = build_optimized_content_image_url(
                    "/media/article/content/202608/content_1.png"
                )

            self.assertEqual(result, "/media/article/content/202608/content_1.webp")
            self.assertTrue(source.exists())
            self.assertTrue((source.parent / "content_1.webp").exists())

    def test_put_normalizes_content_html_image_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "media/article/content/202608/content_1.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(make_png())

            html = '<p><img src="/media/article/content/202608/content_1.png"></p>'
            with patch("app.utils.media_image.ROOT_DIR", root):
                result = service.normalize_content_image_urls(html)

            self.assertIn("content_1.webp", result)
            self.assertNotIn("content_1.png", result)

    def test_temp_image_promotion_returns_webp_and_keeps_png_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            temp = root / "media/article/temp/202608/image.png"
            temp.parent.mkdir(parents=True)
            temp.write_bytes(make_png())

            with patch.object(service, "ROOT_DIR", root), patch(
                "app.utils.media_image.ROOT_DIR", root
            ), patch("app.api.admin.admin_articles.service.uuid.uuid4") as create_uuid:
                create_uuid.return_value.hex = "abc12345"
                result = service._move_temp_file_to_content(
                    "article-id",
                    "/media/article/temp/202608/image.png",
                )

            self.assertTrue(result.endswith(".webp"))
            content_dir = root / "media/article/content"
            self.assertEqual(len(list(content_dir.rglob("*.png"))), 1)
            self.assertEqual(len(list(content_dir.rglob("*.webp"))), 1)


if __name__ == "__main__":
    unittest.main()
