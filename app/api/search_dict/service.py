import re
from typing import List, Tuple, Dict, Literal, Type, Any

from fastapi import HTTPException
from redis.asyncio import Redis
from tortoise import Tortoise, Model
from tortoise.expressions import Q

from app.models import KangjiMapping
from app.utils.all_kana import all_in_kana
from settings import TORTOISE_ORM


async def search_time_updates(redis: Redis) -> None:
    key = "search_time"

    await redis.incr(key, 1)


async def detect_language(text: str) -> Tuple[str, str, bool]:
    """
    自动检测输入语言:
        - zh: 简体中文
        - jp: 日语（含假名或旧字体）
        - fr: 拉丁字母（法语等）
        - other: 其他

    返回:
        (映射或原文本, 语言代码, 是否为“含汉字且命中映射表”的情况)
    """
    JAPANESE_HIRAGANA = r"[\u3040-\u309F]"
    JAPANESE_KATAKANA = r"[\u30A0-\u30FF\u31F0-\u31FF]"

    text = text.strip()
    if not text:
        return "", "other", False

    # ✅ Step 1: 全部假名（无汉字）
    if re.fullmatch(f"(?:{JAPANESE_HIRAGANA}|{JAPANESE_KATAKANA})+", text):
        return text, "jp", False

    # ✅ Step 2: 汉字检测
    if re.search(r"[\u4e00-\u9fff]", text):
        # 优先判断是否为日语汉字
        jp_match = await KangjiMapping.get_or_none(kangji=text).only("kangji")
        if jp_match:
            return text, "jp", True  # 含汉字且命中日语列

        # 再检查是否为中文汉字
        zh_match = await KangjiMapping.get_or_none(hanzi=text).only("hanzi", "kangji")
        if zh_match:
            return zh_match.kangji, "zh", True  # 含汉字且命中中文列

        # 若都不在映射表中，则为未映射的中文
        return text, "zh", False

    # ✅ Step 3: 拉丁字母检测（如法语）
    if re.search(r"[À-ÿ]", text):
        return text, "fr", True  # True → 含拉丁扩展（非英语）

    # 全部为纯英文字符
    elif re.fullmatch(r"[a-zA-Z]+", text):
        return text, "fr", False  # False → 英语单词

    # ✅ Step 4: 其他情况（符号、空格等）
    return text, "other", False


async def accurate_idiom_proverb(search_id: int, model: Type[Model], only_fields: List[str] = None):
    if "freq" not in only_fields:
        only_fields.append("freq")
    result = await model.get_or_none(id=search_id).only(*only_fields)
    if not result:
        raise HTTPException(status_code=404, detail="Target not found")
    result.freq = result.freq + 1
    await result.save(update_fields=["freq"])
    return result


async def suggest_proverb(
        query: str,
        lang: Literal["fr", "zh", "jp"],
        model: Type[Model],
        search_field: str = "search_text",
        target_field: str = "text",
        chi_exp_field: str = "chi_exp",
        limit: int = 10,
) -> List[Dict[str, str]]:
    keyword = query.strip()
    if not keyword:
        return []

    # ✅ 搜索条件：中文时双字段联合匹配
    if lang == "zh":
        start_condition = Q(**{f"{chi_exp_field}__istartswith": keyword})
        contain_condition = Q(**{f"{chi_exp_field}__icontains": keyword})
    else:
        start_condition = Q(**{f"{search_field}__istartswith": keyword})
        contain_condition = Q(**{f"{search_field}__icontains": keyword})

    # ✅ 1. 开头匹配
    start_matches = await (
        model.filter(start_condition)
        .order_by("-freq", "id")
        .limit(limit)
        .values("id", target_field, chi_exp_field, "search_text")
    )

    # ✅ 2. 包含匹配（但不是开头）
    contain_matches = await (
        model.filter(contain_condition & ~start_condition)
        .order_by("-freq", "id")
        .limit(limit)
        .values("id", target_field, chi_exp_field, "search_text")
    )

    # ✅ 3. 合并去重保持顺序
    results = []
    seen_ids = set()
    for row in start_matches + contain_matches:
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            results.append({
                "id": row["id"],
                "proverb": row[target_field],
                "search_text": row["search_text"],
                "chi_exp": row[chi_exp_field],
            })

    # ✅ 截断最终返回数量
    return results[:limit]


async def suggest_autocomplete(
        query: str,
        dict_lang: Literal["fr", "jp"],
        model: Type[Model],
        search_field: str = "search_text",
        text_field: str = "text",
        hira_field: str = "hiragana",
        freq_field: str = "freq",
        limit: int = 10,
) -> List[Dict[str, str]]:
    """
    通用自动补全建议接口：
    - 法语: 按 search_text / text 搜索 + 反查 DefinitionFr 英/中释义
    - 日语: 先按原文 text 匹配，再按假名匹配 + 反查 DefinitionJp 中文释义
    统一返回结构：
    [
        {
            "word": "étudier",
            "hiragana": None,
            "meanings": ["学习", "研究"],
            "english": ["to study", "to learn"]
        }
    ]
    """
    keyword = query.strip()
    if not keyword:
        return []

    # ========== 法语分支 ==========
    if dict_lang == "fr":
        start_condition = (
                Q(**{f"{search_field}__istartswith": keyword})
                | Q(**{f"{text_field}__istartswith": keyword})
        )
        contain_condition = (
                Q(**{f"{search_field}__icontains": keyword})
                | Q(**{f"{text_field}__icontains": keyword})
        )
        value_fields = ["id", text_field, freq_field, search_field]

    # ========== 日语分支 ==========
    elif dict_lang == "jp":
        kana_word = all_in_kana(keyword)
        start_condition = Q(**{f"{text_field}__startswith": keyword})
        contain_condition = Q(**{f"{text_field}__icontains": keyword})

        kana_start = Q(**{f"{hira_field}__startswith": kana_word})
        kana_contain = Q(**{f"{hira_field}__icontains": kana_word})

        start_condition |= kana_start
        contain_condition |= kana_contain
        value_fields = ["id", text_field, hira_field, freq_field]

    else:
        return []

    # ✅ 获取匹配单词
    start_matches = await (
        model.filter(start_condition)
        .order_by(f"-{freq_field}", "id")
        .limit(limit)
        .values(*value_fields)
    )

    contain_matches = await (
        model.filter(contain_condition & ~start_condition)
        .order_by(f"-{freq_field}", "id")
        .limit(limit)
        .values(*value_fields)
    )

    results = []
    seen_ids = set()
    for row in start_matches + contain_matches:
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            results.append({
                "id": row["id"],
                "word": row[text_field],
                "hiragana": row.get(hira_field) if dict_lang == "jp" else None,
                "meanings": [],
                "english": [],
            })

    # ✅ 批量反查 Definition 表，防止 N+1 查询
    if dict_lang == "fr":
        from app.models import DefinitionFr  # 避免循环导入
        word_ids = [r["id"] for r in results]
        defs = await DefinitionFr.filter(word_id__in=word_ids).values("word_id", "meaning", "eng_explanation")

        meaning_map: Dict[int, Dict[str, List[str]]] = {}
        for d in defs:
            meaning_map.setdefault(d["word_id"], {"meanings": [], "english": []})
            if d["meaning"]:
                meaning_map[d["word_id"]]["meanings"].append(d["meaning"].strip())
            if d["eng_explanation"]:
                meaning_map[d["word_id"]]["english"].append(d["eng_explanation"].strip())

        for r in results:
            if r["id"] in meaning_map:
                r["meanings"] = list(set(meaning_map[r["id"]]["meanings"]))
                r["english"] = list(set(meaning_map[r["id"]]["english"]))

    elif dict_lang == "jp":
        from app.models import DefinitionJp
        word_ids = [r["id"] for r in results]
        defs = await DefinitionJp.filter(word_id__in=word_ids).values("word_id", "meaning")

        meaning_map: Dict[int, List[str]] = {}
        for d in defs:
            if d["meaning"]:
                meaning_map.setdefault(d["word_id"], []).append(d["meaning"].strip())

        for r in results:
            if r["id"] in meaning_map:
                r["meanings"] = list(set(meaning_map[r["id"]]))

    # ✅ 删除 id，只保留用户需要字段
    for r in results:
        r.pop("id", None)

    return results[:limit]


# ===================================================
# ✅ 释义反查接口（返回统一结构）
# ===================================================

async def search_definition_by_meaning(
        query: str,
        model: Type[Model],
        meaning_field: str = "meaning",
        eng_field: str = "eng_explanation",
        hira_field: str = "hiragana",
        limit: int = 20,
        lang: Literal["zh", "en"] = "zh",
) -> List[Dict[str, str]]:
    """
    双语释义反查接口（中文/英文）：
    统一返回结构：
    [
        {
            "word": "étudier",
            "hiragana": None,
            "meanings": ["学习", "研究"],
            "english": ["to study"]
        }
    ]
    """

    keyword = query.strip()
    if not keyword:
        return []

    if lang == "zh":
        search_field = meaning_field
    elif lang == "en":
        search_field = eng_field
    else:
        raise ValueError("lang 参数必须为 'zh' 或 'en'")

    contain_condition = Q(**{f"{search_field}__icontains": keyword})

    matches = (
        await model.filter(contain_condition)
        .prefetch_related("word")
        .order_by("id")
    )

    word_to_data: Dict[str, Dict[str, List[str] | str | None]] = {}

    for entry in matches:
        word_obj = await entry.word
        word_text = getattr(word_obj, "text", None)
        if not word_text:
            continue

        chi_mean = getattr(entry, meaning_field, "").strip() or None
        eng_mean = getattr(entry, eng_field, "").strip() or None
        hira_text = getattr(word_obj, hira_field, None) if hasattr(word_obj, hira_field) else None

        if word_text not in word_to_data:
            word_to_data[word_text] = {"hiragana": hira_text, "meanings": [], "english": []}

        if chi_mean:
            word_to_data[word_text]["meanings"].append(chi_mean)
        if eng_mean:
            word_to_data[word_text]["english"].append(eng_mean)

    results = []
    for word, data in word_to_data.items():
        results.append({
            "word": word,
            "hiragana": data["hiragana"],
            "meanings": list(set(data["meanings"])),
            "english": list(set(data["english"]))
        })

    return results[:limit]


def merge_word_results(*lists: List[Dict[str, Any]]) -> List[Dict[str, object]]:
    """
    合并多个结果列表并去重：
    - 依据 word（+ hiragana）唯一性去重
    - meanings / english 合并去重
    - 保留最早出现的顺序
    """
    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for lst in lists:
        for item in lst:
            word = item.get("word")
            hira = item.get("hiragana")
            key = f"{word}:{hira or ''}"  # 以 word+hiragana 作为唯一标识

            if key not in merged:
                # 初次出现，加入结果集
                merged[key] = {
                    "word": word,
                    "hiragana": hira,
                    "meanings": list(item.get("meanings", [])),
                    "english": list(item.get("english", []))
                }
                order.append(key)
            else:
                # 已存在 → 合并释义和英文解释
                merged[key]["meanings"] = list(set(
                    list(merged[key].get("meanings", [])) +
                    list(item.get("meanings", []) or [])
                ))
                merged[key]["english"] = list(set(
                    list(merged[key].get("english", [])) +
                    list(item.get("english", []) or [])
                ))

    # 保持插入顺序输出
    return [merged[k] for k in order]


# async def __test():
#     query_word: str = '棋逢'
#     return await (
#         suggest_proverb(
#             query=ProverbSearchRequest(query=query_word),
#             lang='zh'
#         )
#     )


async def __main():
    await Tortoise.init(config=TORTOISE_ORM)
    print(await __test())


if __name__ == '__main__':
    # asyncio.run(__main())
    print(detect_language(text="ahsjdasd"))
