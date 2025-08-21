from enum import Enum

import pandas as pd
from tortoise.models import Model
from tortoise import fields
from typing import Tuple, Type, TypeVar

from app.schemas.admin_schemas import PosEnumFr

sheet_name_fr = "法英中释义"


class WordlistFr(Model):
    id = fields.IntField(pk=True)
    text = fields.CharField(max_length=40, unique=True, description="单词")
    definitions: fields.ReverseRelation["DefinitionFr"]
    attachments: fields.ReverseRelation["AttachmentFr"]
    freq = fields.IntField()  # 词频排序用
    search_text = fields.CharField(max_length=255, index=True)  # 检索字段

    # attachment = fields.ForeignKeyField("models.Attachment", related_name="wordlists", on_delete=fields.CASCADE)
    # source = fields.CharField(max_length=20, description="<UNK>", null=True)
    class Meta:
        table = "wordlist_fr"


class AttachmentFr(Model):
    id = fields.IntField(pk=True)
    word = fields.ForeignKeyField("models.WordlistFr", related_name="attachments", on_delete=fields.CASCADE)
    yinbiao = fields.CharField(max_length=60, description="音标", null=True)
    record = fields.CharField(max_length=120, description="发音", null=True)
    pic = fields.CharField(max_length=120, description="配图", null=True)

    class Meta:
        table = "attachment_fr"


class DefinitionFr(Model):
    id = fields.IntField(pk=True)
    word = fields.ForeignKeyField("models.WordlistFr", related_name="definitions", on_delete=fields.CASCADE)
    pos = fields.CharEnumField(PosEnumFr, max_length=30, null=True)  # ✅ 把词性放在释义层面
    meaning = fields.TextField(description="单词释义")  # 如：“学习”
    example = fields.TextField(null=True, description="单词例句")
    eng_explanation = fields.TextField(null=True, description="English explanation")
    example_varification = fields.BooleanField(default=False, description="例句是否审核")
    class Meta:
        table = "definition_fr"
