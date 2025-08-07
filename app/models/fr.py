from enum import Enum

import pandas as pd
from tortoise.models import Model
from tortoise import fields
from typing import Tuple, Type, TypeVar

from app.schemas.admin_schemas import PosEnumFr

sheet_name_fr = "法英中释义"


class WordlistFr(Model):
    id = fields.IntField(pk=True)
    language = fields.CharField(max_length=20, description="单词语种")
    text = fields.CharField(max_length=40, unique=True, description="单词")
    definitions = fields.ReverseRelation("DefinitionFr")
    attachments = fields.ReverseRelation("AttachmentsFr")

    # attachment = fields.ForeignKeyField("models.Attachment", related_name="wordlists", on_delete=fields.CASCADE)
    # source = fields.CharField(max_length=20, description="<UNK>", null=True)
    class Meta:
        table = "wordlist_fr"

    T = TypeVar("T", bound=Model)

    @classmethod
    async def update_or_create(cls: Type[T], **kwargs) -> Tuple[T, bool]:
        print("传入参数为：", kwargs)
        if not kwargs:
            raise ValueError("必须提供至少一个字段作为参数")

        created: bool = False

        # 使用 kwargs 中第一个字段作为查找条件
        first_key = next(iter(kwargs))
        lookup = {first_key: kwargs[first_key]}

        word = await cls.filter(**lookup).first()  # 参数展开语法
        if word:
            for k, v in kwargs.items():
                if k != first_key:
                    setattr(word, k, v)
            await word.save()
        else:
            await cls.create(**kwargs)
            created = True

        return word, created


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
    pos = fields.CharEnumField(PosEnumFr, max_length=30)  # ✅ 把词性放在释义层面
    meaning = fields.TextField(description="单词释义")  # 如：“学习”
    example = fields.TextField(null=True, description="单词例句")
    eng_explanation = fields.TextField(null=True, description="English explanation")

    class Meta:
        table = "definitions_fr"

    @classmethod
    async def init_from_xlsx(
            cls,
            filepath: str,
            sheet_name: str
    ):
        """
        Initiate the database from xlsx file. Only read in data without checking
        whether the content already exists.
        :param filepath: receive both relative or absolute path
        :param sheet_name: specific sheet name inside the .xlsx file
        :return: None
        """
        df = pd.read_excel(filepath, sheet_name=sheet_name, na_filter=True)
        df.columns = [col.strip() for col in df.columns]
        df.dropna(how="all", inplace=True)

        # create_cnt = 0
        DEF_COUNT = 1

        for row in df.itertuples():
            word = row.单词
            cls_word = await WordlistFr.filter(text=word).first()
            if cls_word is None:
                print(f"未找到 word: {word}")
                continue
            pos = getattr(row, f"词性{DEF_COUNT}")
            if pd.isna(pos):
                continue
            meaning = getattr(row, f"中文释义{DEF_COUNT}")
            eng_exp = getattr(row, f"英语释义{DEF_COUNT}")
            await DefinitionFr.create(
                part_of_speech=pos,
                meaning=meaning,
                eng_explanation=eng_exp,
                word=cls_word
            )

    # TODO revise the function (check update or create by id)
    @classmethod
    async def update_or_create_meaning(
            cls,
            word_obj,
            target_language_obj,
            part_of_speech: str,
            meaning: str,
            example: str = None,
            eng_explanation: str = None,
    ) -> tuple["DefinitionFr", bool]:
        """
        查询某个单词是否已有该释义（依据四元组作为唯一标识），存在则更新，不存在则新增。
        返回：(对象, 是否为新创建)
        """
        query = {
            "word": word_obj,
            "target_language": target_language_obj,
            "part_of_speech": part_of_speech,
            "meaning": meaning
        }

        obj = await cls.filter(**query).first()
        created = False

        if obj:
            # 可更新其他字段
            obj.example = example
            obj.eng_explanation = eng_explanation
            await obj.save()
        else:
            obj = await cls.create(
                word=word_obj,
                target_language=target_language_obj,
                part_of_speech=part_of_speech,
                meaning=meaning,
                example=example,
                eng_explanation=eng_explanation,
            )
            created = True

        return obj, created
