import asyncio

from tortoise import Tortoise
from tortoise.expressions import Q
from typing import List, Literal, Tuple

from app.models import WordlistFr, WordlistJp
from app.schemas.search_schemas import SearchRequest
from app.utils.all_kana import all_in_kana
from app.utils.textnorm import normalize_text
from settings import TORTOISE_ORM


async def suggest_autocomplete(query: SearchRequest, limit: int = 10) -> List[str]:
    """

    :param query: 当前用户输入的内容
    :param limit: 返回列表限制长度
    :return: 联想的单词列表（非完整信息，单纯单词）
    """
    if query.language == 'fr':
        query_word = normalize_text(query.query)
        qs_prefix = await (
            WordlistFr
            .filter(search_text__startswith=query_word)
            .only("text", "freq")
        )
        prefix_objs = qs_prefix[:limit]
        prefix: List[Tuple[str, int]] = [(o.text, o.freq) for o in prefix_objs]

        need = max(0, limit - len(prefix))
        contains: List[Tuple[str, int]] = []

        if need > 0:
            qs_contain = await (
                WordlistFr
                .filter(search_text__icontains=query_word)
                .exclude(search_text__startswith=query_word)
                .only("text", "freq")
            )
            contains_objs = qs_contain[:need * 2]
            contains: List[Tuple[str, int]] = [(o.text, o.freq) for o in contains_objs]

    else:
        query_word = all_in_kana(query.query)

        qs_prefix = await (
            WordlistJp
            .filter(hiragana__startswith=query_word)
            .only("text", "freq")
        )

        prefix_objs = qs_prefix[:limit]
        prefix: List[Tuple[str, int]] = [(o.text, o.freq) for o in prefix_objs]

        need = max(0, limit - len(prefix))
        contains = []
        if need > 0:
            qs_contain = await (
                WordlistJp
                .filter(Q(hiragana__icontains=query_word) | Q(text__icontains=query_word))
                .exclude(Q(hiragana__startswith=query_word) | Q(text__startswith=query_word))
                .only("text", "freq")
            )
            contains_objs = qs_contain[:need * 2]
            contains: List[Tuple[str, int]] = [(o.text, o.freq) for o in contains_objs]

    seen_text, out = set(), []
    for word in list(qs_prefix) + list(contains):
        if word.text not in seen_text:
            seen_text.add(word.text)
            out.append((word.text, word.freq))
        if len(out) >= limit:
            break
    out = sorted(out, key=lambda w: (w[1], len(w[0]), w[0]))
    return [text for text, _ in out]


async def __test():
    query_word: str = 'あい'
    language: Literal['fr', 'jp'] = 'jp'
    return await suggest_autocomplete(SearchRequest(query=query_word, language=language))


async def __main():
    await Tortoise.init(config=TORTOISE_ORM)
    print(await __test())


if __name__ == '__main__':
    asyncio.run(__main())
