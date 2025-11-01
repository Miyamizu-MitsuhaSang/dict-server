import asyncio
from pathlib import Path

import pandas as pd
from tortoise import Tortoise, connections
from tortoise.exceptions import MultipleObjectsReturned

from app.models.fr import DefinitionFr, WordlistFr
from settings import TORTOISE_ORM

xlsx_name = "./DictTable_20250811.xlsx"
xlsx_path = Path(xlsx_name)


def pos_process(pos: str) -> str:
    pos = pos.replace(" ", "")
    pos = pos.replace(",", "")
    if not pos.endswith(".") and not pos.endswith(")") and pos != "chauff":
        pos = pos + "."
    return pos


async def import_wordlist_fr(path: Path = xlsx_path, sheet_name: str = "法英中释义"):
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [col.strip() for col in df.columns]

    for row in df.itertuples():
        word = str(row.单词).strip()
        if pd.isna(word):
            break

        word_obj, created = await WordlistFr.get_or_create(text=word, defaults={"freq": 0})
        if created:
            print(f"✅ 新增词条: {word}")
        else:
            print(f"⚠️ 已存在: {word}，跳过")


async def import_def_fr(
        path: Path = xlsx_path,
        sheet_name: str = "法英中释义"
):
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [col.strip() for col in df.columns]

    for row in df.itertuples():
        word = row.单词
        if pd.isna(word):
            continue

        word = str(word).strip()

        # 查找 WordlistFr 实例（注意异常处理）
        try:
            cls_word = await WordlistFr.get(text=word)
        except MultipleObjectsReturned:
            ids = await WordlistFr.filter(text=word).values_list("id", flat=True)
            print(f"❗ 重复单词 {word}，id为: {' '.join(str(i) for i in ids)}")
            continue
        except Exception as e:
            print(f"❌ 查找单词 {word} 出错: {e}")
            continue

        # 字段处理
        example = None if pd.isna(row.法语例句1) else str(row.法语例句1).strip()
        pos = None if pd.isna(row.词性1) else pos_process(str(row.词性1).strip())
        eng_exp = None if pd.isna(row.英语释义1) else str(row.英语释义1).strip()
        chi_exp = str(row[3]).strip()

        # 去重：同一个词条不能有重复释义（同 pos + meaning）
        exists = await DefinitionFr.filter(
            word=cls_word,
            pos=pos,
            meaning=chi_exp
        ).exists()
        if exists:
            print(f"⚠️ 已存在释义，跳过：{word} - {pos} - {chi_exp[:10]}...")
            continue

        # 创建定义
        try:
            await DefinitionFr.create(
                word=cls_word,
                pos=pos,
                eng_explanation=eng_exp,
                meaning=chi_exp,
                example=example,
            )
            print(f"✅ 导入释义：{word} - {pos}")
        except Exception as e:
            print(f"❌ 插入释义失败：{word} - {pos}，错误: {e}")


async def varification_eg():
    """
    更新所有的已经写入的example为已经校验检查过的
    :return: None
    """
    await DefinitionFr.filter(example__not_isnull=True).update(example_varification=True)


async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    await DefinitionFr.all().delete()   # TRUNCATE TABLE definitions_fr;
    conn = connections.get("default")
    await conn.execute_script("""
        ALTER TABLE definitions_fr AUTO_INCREMENT = 1;
    """)
    await import_def_fr()
    # await import_wordlist_fr()


if __name__ == "__main__":
    asyncio.run(main())
