import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.api.admin.admin_articles import service


class ArticleTempImagePromotionTests(unittest.TestCase):
    def test_validation_rejects_a_missing_temp_image_before_article_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(service, "ROOT_DIR", Path(directory)):
                with self.assertRaisesRegex(ValueError, "临时图片不存在"):
                    service._validate_temp_image_urls([
                        "/media/article/temp/202608/missing.png",
                    ])

    def test_missing_temp_image_is_rejected_instead_of_returning_a_stale_url(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(service, "ROOT_DIR", Path(directory)):
                with self.assertRaisesRegex(ValueError, "临时图片不存在"):
                    service._move_temp_file_to_content(
                        "article-id",
                        "/media/article/temp/202608/missing.png",
                    )


if __name__ == "__main__":
    unittest.main()
