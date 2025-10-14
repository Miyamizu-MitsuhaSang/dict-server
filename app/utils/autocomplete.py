import asyncio
from typing import List, Literal, Tuple

from tortoise import Tortoise
from tortoise.expressions import Q

from app.models import WordlistFr, WordlistJp
from app.schemas.search_schemas import SearchRequest
from app.utils.all_kana import all_in_kana
from app.utils.textnorm import normalize_text
from settings import TORTOISE_ORM


async def suggest_autocomplete(query: SearchRequest, limit: int = 10) -> List[Tuple[str, str]]:
    """

    :param query: 当前用户输入的内容
    :param limit: 返回列表限制长度
    :return: 联想的单词列表（非完整信息，单纯单词）
    """
    if query.language == 'fr':
        query_word = normalize_text(query.query)
        exact = await (
            WordlistFr
            .get_or_none(text=query.query)
            .values("text", "freq")
        )
        if exact:
            exact_word = [(exact.get("text"), exact.get("freq"))]
        else:
            exact_word = []

        qs_prefix = (
            WordlistFr
            .filter(Q(search_text__startswith=query_word) | Q(text__startswith=query.query))
            .exclude(text=query.query)
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
    query_word: str = '愛'
    language: Literal['fr', 'jp'] = 'jp'
    return await suggest_autocomplete(SearchRequest(query=query_word, language=language))


async def __main():
    await Tortoise.init(config=TORTOISE_ORM)
    print(await __test())


if __name__ == '__main__':
    asyncio.run(__main())
