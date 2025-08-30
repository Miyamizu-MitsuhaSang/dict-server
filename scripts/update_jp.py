import asyncio
import re
import unicodedata
import jaconv
from pathlib import Path

import pandas as pd
from fugashi import Tagger
import unidic_lite
from importlib import resources
from pykakasi import kakasi
from tortoise import Tortoise
from tortoise.exceptions import MultipleObjectsReturned

from app.models import WordlistJp, DefinitionJp, AttachmentJp, PosType
from settings import TORTOISE_ORM

xlsx_name = "./DictTable-20250823.xlsx"
xlsx_path = Path(xlsx_name)


def normalize_jp_text(text: str) -> str:
    # Unicode标准化（全角半角统一）
    text = unicodedata.normalize("NFKC", text)
    # 去除前后空格和常见不可见字符（零宽空格、换行符、制表符等）
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\r\n\t]', '', text)
    return text.strip()


async def pos_process(pos: str):
    # 映射简写到标准枚举值
    mapping = {
        "形": "形容词",
        "形动": "形容动词",
        "感叹": "感叹词",
        "连体词": "连体",
        "副词": "连用",
        "自动": "自动词",
        "他动": "他动词",
        "自他动": "自他动词",
        "五段": "五段动词",
        "一段": "一段动词",
        "接续词": "接续",
        "カ变动词": "カ変",
        "サ变动词": "サ変",
    }

    # 去除空格 + 替换映射
    pos_list = [mapping.get(p.strip(), p.strip()) for p in pos.split("・") if p.strip()]
    if "动词" in pos_list:
        return None, True

    # 查询匹配的 PosType 实例（建议加 set 去重）
    pos_type_objs = await PosType.filter(pos_type__in=list(set(pos_list)))
    return pos_type_objs, False


# 初始化分词器
dicdir = resources.files('unidic_lite').joinpath('dicdir')
tagger = Tagger(f"-d {dicdir}")

# 初始化 kakasi 转换器
kakasi_inst = kakasi()
kakasi_inst.setMode("H", "a")  # 平假名 to 罗马字
kakasi_inst.setMode("K", "a")  # 片假名 to 罗马字
kakasi_inst.setMode("J", "a")  # 汉字按音读转假名再转罗马字
kakasi_inst.setMode("r", "Hepburn")  # 使用 Hepburn 拼音规则
converter = kakasi_inst.getConverter()


def is_kana_only(text: str) -> bool:
    """
    判断是否是纯假名（不含汉字）
    """
    for ch in text:
        if not ('\u3040' <= ch <= '\u309F' or '\u30A0' <= ch <= '\u30FF'):
            return False
    return True


def to_kana(word: str) -> str:
    # 如果全为假名，则直接返回
    if is_kana_only(word):
        return word

    # 否则用 fugashi 分词并拼接假名（假设用 `feature.kana`）
    tokens = tagger(word)
    kana_list = []
    for token in tokens:
        # token.feature.kana 是 Unidic 词典中的假名字段
        kana = token.feature.get('kana') or token.surface
        kana_list.append(kana)

    return ''.join(kana_list)


def kana_to_romaji(text: str) -> str:
    """
    将日文文本转换为罗马字（假名优先，汉字使用Unidic读音推测）
    """

    # 用fugashi解析词并取其假名
    kana_seq = []
    for word in tagger(text):
        kana = word.feature[7] if len(word.feature) > 7 and word.feature[7] else word.surface
        kana_seq.append(kana)

    joined_kana = ''.join(kana_seq)
    romaji = converter.do(joined_kana)
    return romaji


async def import_wordlist_jp(path: Path = xlsx_path, sheet_name: str = "日汉释义"):
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [col.strip() for col in df.columns]

    for row in df.itertuples():
        word = normalize_jp_text(str(row.单词))
        if pd.isna(word):
            continue

        word_obj, created = await WordlistJp.get_or_create(text=word, defaults={"freq": 0})
        if created and word == 'また':
            print(f"✅ 新增词条: {word}")
        elif not created:
            print(f"⚠️ 已存在: {word}，跳过")
        else:
            pass


async def import_def_jp(path: Path = xlsx_path, sheet_name: str = "日汉释义"):
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [col.strip() for col in df.columns]

    for row in df.itertuples():
        word = normalize_jp_text(str(row.单词))
        if pd.isna(word):
            continue

        word = str(word).strip()

        try:
            cls_word = await WordlistJp.get(text=word)
        except MultipleObjectsReturned:
            ids = await WordlistJp.filter(text=word).values_list("id", flat=True)
            print(f"❗ 重复单词 {word}，id为: {' '.join(str(i) for i in ids)}")
            continue
        except Exception as e:
            print(f"❌ 查找单词 {word} 出错: {e}")
            continue

        if pd.isna(row[6]):
            continue
        # 字段处理
        example = None if pd.isna(row.日语例句2) else normalize_jp_text(str(row.日语例句2))
        if not pd.isna(row.词性):
            pos_obj, jump = await pos_process(str(row.词性))
            if jump:
                continue
        else:
            print(f"❌ {word} 的词性为空，跳过")
            continue
        chi_exp = str(row[6]).strip()   # 读取第二个释义

        exists = await DefinitionJp.filter(
            word=cls_word,
            meaning=chi_exp,
        ).exists()
        if exists:
            print(f"⚠️ 已存在释义，跳过：{word} - {chi_exp[:10]}...")
            continue

        try:
            new_item = await DefinitionJp.create(
                word=cls_word,
                meaning=chi_exp,
                example=example,
            )
            await new_item.pos.add(*pos_obj)
            print(f"✅ 导入释义：{word}")
        except Exception as e:
            print(f"❌ 插入释义失败：{word}，错误: {e}")


async def import_attachment(path: Path = xlsx_path, sheet_name: str = "日汉释义"):
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [col.strip() for col in df.columns]

    # 统一清洗后去重词汇列表
    unique_words = df["单词"].dropna().map(lambda x: normalize_jp_text(str(x))).unique().tolist()

    # 批量获取所有 WordlistJp 实例
    word_objs = await WordlistJp.filter(text__in=unique_words)
    word_map = {normalize_jp_text(w.text): w for w in word_objs}

    for row in df.itertuples():
        word = normalize_jp_text(str(row.单词))
        if pd.isna(word):
            continue
        word_obj = word_map.get(word)
        if not word_obj:
            print(f"❌ 未找到词条：{word}，跳过")
            print(f"[DEBUG] 原始: {repr(row.单词)} → 标准化后: {normalize_jp_text(str(row.单词))}")
            print(f"编码: {[hex(ord(c)) for c in str(row.单词)]}")
            continue

        hiragana = normalize_jp_text(jaconv.kata2hira(str(row[1]))) if pd.isna(row[2]) else normalize_jp_text(str(row[2]))
        romaji = jaconv.kana2alphabet(hiragana)

        await AttachmentJp.get_or_create(
            word=word_obj,
            hiragana=hiragana,
            romaji=romaji,
        )


async def set_hiragana(xlsx_path: Path = xlsx_path, sheet_name : str="日汉释义"):
    df = pd.read_excel(xlsx_path)
    df.columns = [col.strip() for col in df.columns]

    for row in df.itertuples():
        word = normalize_jp_text(str(row[1]).strip())
        if pd.isna(word):
            break

        hiragana = normalize_jp_text(jaconv.kata2hira(str(row[1]))) if pd.isna(row[2]) else normalize_jp_text(str(row[2]))
        romaji = row[3]

        await WordlistJp.filter(text=word).update(hiragana=hiragana)


async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    # await DefinitionJp.all().delete()  # TRUNCATE TABLE definitions_fr;
    # await WordlistJp.all().delete()
    # await AttachmentJp.all().delete()
    # await import_wordlist_jp()
    # await import_def_jp()
    # await import_attachment()
    await set_hiragana()


if __name__ == '__main__':
    asyncio.run(main())
