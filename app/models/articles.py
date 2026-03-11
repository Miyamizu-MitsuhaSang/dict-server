from tortoise import fields
from tortoise.models import Model

from app.utils.key_generator import KeyGenerator


class Article(Model):
    article_id = fields.CharField(pk=True, max_length=255, default=KeyGenerator.generate_uuid)

    title = fields.CharField(max_length=255)
    summary = fields.TextField(null=True)
    source = fields.TextField(null=True)
    cover_url = fields.CharField(max_length=500, null=True)

    content_html = fields.TextField()
    content_text = fields.TextField(null=True)

    # 先用字符串分类，后面如果你要分类表，再改成 ForeignKey
    category = fields.CharField(max_length=50, null=True)

    # tags 先直接存 JSON 数组，最省事
    tags = fields.JSONField(default=list)

    # draft / published
    status = fields.CharField(max_length=20, default="draft")

    # 发布时间：可以为空；草稿为空，发布时自动补
    publish_at = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "articles"
        ordering = ["-created_at"]


class ArticlePicture(Model):
    pic_id = fields.CharField(pk=True, max_length=256, default=KeyGenerator.generate_uuid)
    sequence = fields.IntField(default=0)
    pic_path = fields.CharField(max_length=256, description="图片存放路径")
    article = fields.ForeignKeyField("models.Article", related_name="pics")
    is_cover = fields.BooleanField(default=False)

    class Meta:
        table = "article_pics"

class Banner(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    subtitle = fields.CharField(max_length=500, null=True)
    image_url = fields.CharField(max_length=500)
    target_url = fields.CharField(max_length=500)
    article = fields.ForeignKeyField(
        "models.Article",
        related_name="banner",
        null=True,
        on_delete=fields.SET_NULL
    )

    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    start_at = fields.DatetimeField(null=True)
    end_at = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class ArticleTag(Model):
    tag_id = fields.CharField(pk=True, max_length=255, default=KeyGenerator.generate_uuid)
    name = fields.CharField(max_length=50, unique=True, index=True)
    usage_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "article_tags"
        ordering = ["name"]
