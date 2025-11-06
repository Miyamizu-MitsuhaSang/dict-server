import re
from typing import List, Tuple, Dict, Literal, Type

from fastapi import HTTPException
from redis.asyncio import Redis
from tortoise import Tortoise, Model
from tortoise.expressions import Q

from app.api.search_dict.search_schemas import SearchRequest, ProverbSearchRequest
from app.models import WordlistFr, WordlistJp, KangjiMapping
from app.utils.all_kana import all_in_kana
from app.utils.textnorm import normalize_text
from settings import TORTOISE_ORM


async def search_time_updates(redis: Redis) -> None:
    key = "search_times"

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
    if re.search(r"[a-zA-ZÀ-ÿ]", text):
        return text, "fr", False

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
        start_condition = Q(**{f"{chi_exp_field}__istartswith": keyword}) | Q(
            **{f"{search_field}__istartswith": keyword})
        contain_condition = Q(**{f"{chi_exp_field}__icontains": keyword}) | Q(**{f"{search_field}__icontains": keyword})
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


async def suggest_autocomplete(query: SearchRequest, limit: int = 10):
    """

    :param query: 当前用户输入的内容
    :param limit: 返回列表限制长度
    :return: 联想的单词列表（非完整信息，单纯单词）
    """
    if query.language == 'fr':
        query_word = normalize_text(query.query)
        exact = await (
            WordlistFr
            .get_or_none(search_text=query.query)
            .values("text", "freq")
        )
        if exact:
            exact_word = [(exact.get("text"), exact.get("freq"))]
        else:
            exact_word = []

        qs_prefix = (
            WordlistFr
            .filter(Q(search_text__startswith=query_word) | Q(text__startswith=query.query))
            .exclude(search_text=query.query)
            .only("text", "freq")
        )
        prefix_objs = await qs_prefix[:limit]
        prefix: List[Tuple[str, int]] = [(o.text, o.freq) for o in prefix_objs]

        need = max(0, limit - len(prefix))
        contains: List[Tuple[str, int]] = []

        if need > 0:
            qs_contain = (
                WordlistFr
                .filter(Q(search_text__icontains=query_word) | Q(text__icontains=query.query))
                .exclude(Q(search_text__startswith=query_word) | Q(text__startswith=query.query) | Q(text=query.query))
                .only("text", "freq")
                .only("text", "freq")
            )
            contains_objs = await qs_contain[: need * 2]
            contains = [(o.text, o.freq) for o in contains_objs]

            seen_text, out = set(), []
            for text, freq in list(exact_word) + list(prefix) + list(contains):
                key = text
                if key not in seen_text:
                    seen_text.add(key)
                    out.append((text, freq))
                if len(out) >= limit:
                    break
            out = sorted(out, key=lambda w: (-w[2], len(w[0]), w[0]))
            return [text for text, _ in out]

    else:
        query_word = all_in_kana(query.query)
        exact = await (
            WordlistJp
            .get_or_none(
                text=query.query
            )
            .only("text", "hiragana", "freq")
        )
        if exact:
            exact_word = [(exact.text, exact.hiragana, exact.freq)]
        else:
            exact_word = []

        qs_prefix = (
            WordlistJp
            .filter(Q(hiragana__startswith=query_word) | Q(text__startswith=query.query))
            .exclude(text=query.query)
            .only("text", "hiragana", "freq")
        )
        prefix_objs = await qs_prefix[:limit]
        prefix: List[Tuple[str, str, int]] = [(o.text, o.hiragana, o.freq) for o in prefix_objs]

        need = max(0, limit - len(prefix))
        contains: List[Tuple[str, str, int]] = []

        if need > 0:
            qs_contain = await (
                WordlistJp
                .filter(Q(hiragana__icontains=query_word) | Q(text__icontains=query.query))
                .exclude(Q(hiragana__startswith=query_word) | Q(text__startswith=query.query) | Q(text=query.query))
                .only("text", "hiragana", "freq")
            )
            contains_objs = qs_contain[:need * 2]
            contains: List[Tuple[str, str, int]] = [(o.text, o.hiragana, o.freq) for o in contains_objs]

        seen_text, out = set(), []
        for text, hiragana, freq in list(exact_word) + list(prefix) + list(contains):
            key = (text, hiragana)
            if key not in seen_text:
                seen_text.add(key)
                out.append((text, hiragana, freq))
            if len(out) >= limit:
                break
        out = sorted(out, key=lambda w: (-w[2], len(w[0]), w[0]))
        return [(text, hiragana) for text, hiragana, _ in out]


async def __test():
    query_word: str = '棋逢'
    return await (
        suggest_proverb(
            query=ProverbSearchRequest(query=query_word),
            lang='zh'
        )
    )


async def __main():
    await Tortoise.init(config=TORTOISE_ORM)
    print(await __test())


if __name__ == '__main__':
    # asyncio.run(__main())
    print(detect_language(text="ahsjdasd"))
