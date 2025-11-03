import re
from typing import List, Tuple, Dict, Literal, Type

from fastapi import HTTPException
from opencc import OpenCC
from tortoise import Tortoise, Model
from tortoise.expressions import Q

from app.api.search_dict.search_schemas import SearchRequest, ProverbSearchResponse, ProverbSearchRequest
from app.models import WordlistFr, WordlistJp
from app.models.fr import ProverbFr
from app.utils.all_kana import all_in_kana
from app.utils.textnorm import normalize_text
from settings import TORTOISE_ORM


def detect_language(text: str) -> Tuple[str, Literal["fr", "zh", "jp", "other"]]:
    """
    自动检测输入语言:
        - zh: 简体中文
        - jp: 日语（含假名或繁体/旧体字）
        - fr: 拉丁字母（法语等）
        - other: 其他
    """
    cc_s2t = OpenCC('s2t')  # 简体 → 繁体
    cc_t2s = OpenCC('t2s')  # 繁体 → 简体

    JAPANESE_HIRAGANA = r"[\u3040-\u309F]"
    JAPANESE_KATAKANA = r"[\u30A0-\u30FF\u31F0-\u31FF]"

    text = text.strip()
    if not text:
        return "", "other"

    # ✅ Step 1: 假名检测
    if re.search(JAPANESE_HIRAGANA, text) or re.search(JAPANESE_KATAKANA, text):
        return text, "jp"

    # ✅ Step 2: 汉字检测
    if re.search(r"[\u4e00-\u9fff]", text):
        # 简繁互转对比
        to_trad = cc_s2t.convert(text)
        to_simp = cc_t2s.convert(text)

        # 如果输入等于繁体转换结果 → 繁体或日文汉字
        if text == to_trad and text != to_simp:
            return text, "jp"
        # 如果输入等于简体转换结果 → 简体中文
        elif text == to_simp and text != to_trad:
            return to_trad, "zh"  # 注意返回的是繁体形式用于补充搜索
        # 否则混合（既有简体又有繁体）
        else:
            # 混合时可优先认定为繁体（日语）
            return to_trad, "jp"

    # ✅ Step 3: 拉丁字母检测
    if re.search(r"[a-zA-ZÀ-ÿ]", text):
        return text, "fr"

    return text, "other"


async def accurate_proverb(proverb_id: int) -> ProverbSearchResponse:
    """对于查询法语谚语的精准查询，返回详细信息"""
    proverb = await ProverbFr.get_or_none(id=proverb_id)
    if not proverb:
        raise HTTPException(status_code=404, detail="Proverb not found")
    proverb.freq = proverb.freq + 1
    await proverb.save()
    return ProverbSearchResponse(
        proverb_text=proverb.text,
        chi_exp=proverb.chi_exp,
    )

async def accurate_idiom(idiom_id: int):
    proverb = await ProverbFr.get_or_none(id=idiom_id)
    if not proverb:
        raise HTTPException(status_code=404, detail="Proverb not found")
    proverb.freq = proverb.freq + 1
    await proverb.save()
    return proverb


async def suggest_proverb(
        query: str,
        lang: Literal["fr", "zh", "jp"],
        model: Type[Model],
        search_field: str = "search_text",
        target_field: str = "text",
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
        startswith_field = f"{search_field}__istartswith"
        contains_field = f"{search_field}__icontains"

    # ✅ 1. 开头匹配
    start_matches = await (
        model.filter(**{startswith_field: keyword})
        .order_by("-freq")
        .limit(limit)
        .values("id", target_field, search_field, chi_exp_field)
    )

    # ✅ 2. 包含匹配（非开头）
    contain_matches = await (
        model.filter(
            Q(**{contains_field: keyword}) & ~Q(**{startswith_field: keyword})
        )
        .order_by("-freq")
        .limit(limit)
        .values("id", target_field, search_field, chi_exp_field)
    )

    # ✅ 3. 合并去重并保持顺序
    results: List[Dict[str, str]] = []
    seen_ids = set()
    for row in start_matches + contain_matches:
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            results.append({
                "id": row["id"],
                "proverb": row[target_field],
                "search_text": row[search_field],
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
