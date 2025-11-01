import asyncio
import re
from typing import List, Tuple, Dict, Literal

from fastapi import HTTPException
from tortoise import Tortoise
from tortoise.expressions import Q

from app.api.search_dict.search_schemas import SearchRequest, ProverbSearchResponse, ProverbSearchRequest
from app.models import WordlistFr, WordlistJp
from app.models.fr import ProverbFr
from app.utils.all_kana import all_in_kana
from app.utils.textnorm import normalize_text
from settings import TORTOISE_ORM


def contains_chinese(text: str) -> bool:
    """判断字符串中是否包含至少一个中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


async def accurate_proverb(proverb_id: int) -> ProverbSearchResponse:
    proverb = await ProverbFr.get_or_none(id=proverb_id)
    if not proverb:
        raise HTTPException(status_code=404, detail="Proverb not found")
    return ProverbSearchResponse(
        proverb_text=proverb.proverb,
        chi_exp=proverb.chi_exp,
    )


async def suggest_proverb(query: ProverbSearchRequest, lang: Literal['fr', 'zh']) -> List[Dict[str, str]]:
    """
     对法语谚语表进行搜索建议。
    参数:
        query.query: 搜索关键词
        lang: 'fr' 或 'zh'
    逻辑:
        1. 若 lang='fr'，按谚语字段 (proverb) 搜索；
        2. 若 lang='zh'，按中文释义字段 (chi_exp) 搜索；
        3. 优先以输入开头的匹配；
        4. 其次为包含输入但不以其开头的匹配（按 freq 排序）。
    :return: [{'id': 1, 'proverb': 'xxx'}, ...]
    """
    keyword = query.query.strip()
    results: List[Dict[str, str]] = []

    if not keyword:
        return results

    # ✅ 根据语言决定搜索字段
    if lang == "zh":
        startswith_field = "chi_exp__istartswith"
        contains_field = "chi_exp__icontains"
    else:  # 默认法语
        startswith_field = "proverb__istartswith"
        contains_field = "proverb__icontains"

    # ✅ 1. 开头匹配
    start_matches = await (
        ProverbFr.filter(**{startswith_field: keyword})
        .order_by("-freq")
        .limit(10)
        .values("id", "proverb", "chi_exp")
    )

    # ✅ 2. 包含匹配（但不是开头）
    contain_matches = await (
        ProverbFr.filter(
            Q(**{contains_field: keyword}) & ~Q(**{startswith_field: keyword})
        )
        .order_by("-freq")
        .limit(10)
        .values("id", "proverb", "chi_exp")
    )

    # ✅ 合并结果（去重并保持顺序）
    seen_ids = set()
    for row in start_matches + contain_matches:
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            results.append({
                "id": row["id"],
                "proverb": row["proverb"],
                "chi_exp": row["chi_exp"]
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
    asyncio.run(__main())
