from __future__ import annotations

from enum import Enum
from app.schemas.admin_schemas import PosEnumJp

import pandas as pd
from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned
from tortoise.models import Model
from tortoise import fields
from typing import Tuple, TYPE_CHECKING, TypeVar, Type, Optional

sheet_name_jp = "日汉释义"


# noinspection PyArgumentList
class WordlistJp(Model):
    id = fields.IntField(pk=True)
    text = fields.CharField(max_length=40, description="单词")
    definitions : fields.ReverseRelation["DefinitionJp"]
    attachments : fields.ReverseRelation["AttachmentJp"]

    class Meta:
        table = "wordlist_jp"

    T = TypeVar("T")

    @classmethod
    async def init_from_xlsx(cls, filepath: str, sheet_name: str) -> None:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        df.columns = [col.strip() for col in df.columns]
        df.dropna(how="all", inplace=True)

        for row in df.itertuples():
            word = row.单词
            await cls.create(
                text=word,
            )

    @classmethod
    async def update_and_create(cls, text: str) -> Tuple[WordlistJp, bool]:
        created = False
        try:
            word = await cls.get(text=text)
        except DoesNotExist:
            word = await cls.create(text=text)
            created = True
        else:
            word.text = text
            await word.save()
        return word, created


class AttachmentJp(Model):
    id = fields.IntField(pk=True)
    word = fields.ForeignKeyField("models.WordlistJp", related_name="attachments", on_delete=fields.CASCADE)
    hiragana = fields.CharField(max_length=60, description="假名", null=True)
    romaji = fields.TextField(null=True, description="罗马字")
    record = fields.CharField(max_length=120, description="发音", null=True)
    pic = fields.CharField(max_length=120, description="配图", null=True)

    class Meta:
        table = "attachment_jp"


class DefinitionJp(Model):
    id = fields.IntField(pk=True)
    word = fields.ForeignKeyField("models.WordlistJp", related_name="definitions", on_delete=fields.CASCADE)
    meaning = fields.TextField(description="单词释义")
    example = fields.TextField(null=True, description="单词例句")
    pos = fields.ManyToManyField("models.PosType", related_name="definitions", on_delete=fields.CASCADE)

    class Meta:
        table = "definitions_jp"

class PosType(Model):
    id = fields.IntField(pk=True)
    pos_type = fields.CharEnumField(PosEnumJp, max_length=30, null=False)

    class Meta:
        table = "pos_type"
