import re
from typing import List, Tuple, Dict, Literal, Type

from fastapi import HTTPException
from tortoise import Tortoise, Model
from tortoise.expressions import Q

from app.api.search_dict.search_schemas import SearchRequest, ProverbSearchResponse, ProverbSearchRequest
from app.models import WordlistFr, WordlistJp
from app.models.fr import ProverbFr
from app.utils.all_kana import all_in_kana
from app.utils.textnorm import normalize_text
from settings import TORTOISE_ORM


def detect_language(text: str) -> Literal["fr", "zh", "jp", "other"]:
    """
    自动检测输入语言:
        返回 'zh' / 'jp' / 'fr' / 'other'
    """
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    elif re.search(r"[\u3040-\u30ff\u31f0-\u31ff]", text):  # 日文假名范围
        return "jp"
    elif re.search(r"[a-zA-ZÀ-ÿ]", text):
        return "fr"
    return "other"


async def accurate_proverb(proverb_id: int) -> ProverbSearchResponse:
    """对于查询法语谚语的精准查询，返回详细信息"""
    proverb = await ProverbFr.get_or_none(id=proverb_id)
    if not proverb:
        raise HTTPException(status_code=404, detail="Proverb not found")
    return ProverbSearchResponse(
        proverb_text=proverb.text,
        chi_exp=proverb.chi_exp,
    )


async def suggest_proverb(
    query: str,
    lang: Literal["fr", "zh", "jp"],
    model: Type[Model],
    proverb_field: str = "text",
    chi_exp_field: str = "chi_exp",
    limit: int = 10,
) -> List[Dict[str, str]]:
    """
    通用搜索建议函数，用于多语言谚语表。
    参数:
        query: 搜索关键词
        lang: 'fr' 或 'zh'
        model: Tortoise ORM 模型类，例如 ProverbFr
        proverb_field: 外语谚语字段名
        chi_exp_field: 中文释义字段名
        limit: 每类匹配的最大返回数量

    搜索逻辑:
        1. 根据语言选择搜索字段；
        2. 优先匹配以输入开头的结果；
        3. 其次匹配包含输入但非开头的结果；
        4. 合并去重后返回。
    """
    keyword = query.strip()
    if not keyword:
        return []

    # ✅ 根据语言选择搜索字段
    if lang == "zh":
        startswith_field = f"{chi_exp_field}__istartswith"
        contains_field = f"{chi_exp_field}__icontains"
    else:
        startswith_field = f"{proverb_field}__istartswith"
        contains_field = f"{proverb_field}__icontains"

    # ✅ 1. 开头匹配
    start_matches = await (
        model.filter(**{startswith_field: keyword})
        .order_by("-freq")
        .limit(limit)
        .values("id", proverb_field, chi_exp_field)
    )

    # ✅ 2. 包含匹配（非开头）
    contain_matches = await (
        model.filter(
            Q(**{contains_field: keyword}) & ~Q(**{startswith_field: keyword})
        )
        .order_by("-freq")
        .limit(limit)
        .values("id", proverb_field, chi_exp_field)
    )

    # ✅ 3. 合并去重并保持顺序
    results: List[Dict[str, str]] = []
    seen_ids = set()
    for row in start_matches + contain_matches:
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            results.append({
                "id": row["id"],
                "proverb": row[proverb_field],
                "chi_exp": row[chi_exp_field]
            })

    return results


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