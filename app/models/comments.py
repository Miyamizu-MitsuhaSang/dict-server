from tortoise import fields
from tortoise.models import Model

class CommentFr(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="comments_fr")
    comment_text = fields.TextField(description="The comment text")
    comment_word = fields.ForeignKeyField("models.WordlistFr", related_name="comments_fr")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    supervised = fields.BooleanField(default=False)

    class Meta:
        table = "comments_fr"

class CommentJp(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="comments_jp")
    comment_text = fields.TextField(description="The comment text")
    comment_word = fields.ForeignKeyField("models.WordlistJp", related_name="comments_jp")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    supervised = fields.BooleanField(default=False)

    class Meta:
        table = "comments_jp"

class ImprovingComment(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="comments_improving")
    comment_text = fields.TextField(description="The comment text")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "comments_improving"