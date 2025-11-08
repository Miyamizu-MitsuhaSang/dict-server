import asyncio
from typing import Literal, List

from fastapi import APIRouter, Depends, HTTPException, Request, Form

from app.api.search_dict import service
from app.api.search_dict.search_schemas import SearchRequest, WordSearchResponse, SearchItemFr, SearchItemJp, \
    ProverbSearchRequest
from app.api.word_comment.word_comment_schemas import CommentSet
from app.models import DefinitionJp, CommentFr, CommentJp, WordlistFr
from app.models.fr import DefinitionFr, ProverbFr
from app.models.jp import IdiomJp, WordlistJp
from app.utils.all_kana import all_in_kana
from app.utils.security import get_current_user
from app.utils.textnorm import normalize_text

dict_search = APIRouter()


async def __get_comments(
        __query_word: str,
        language: Literal["jp", "fr"]
) -> CommentSet:
    if language == "fr":
        comments = await (
            CommentFr
            .filter(comment_word__word=__query_word)
            .select_related("user")
            .order_by("-created_at")
        )
        commentlist = CommentSet(
            comments=[
                (
                    comment.user.id,
                    comment.user.name,
                    comment.comment_text
                ) for comment in comments
            ]
        )
        return commentlist
    else:
        comments = await (
            CommentJp
            .filter(comment_word__word=__query_word)
            .select_related("user")
            .order_by("-created_at")
        )
        commentlist = CommentSet(
            comments=[
                (
                    comment.user.id,
                    comment.user.name,
                    comment.comment_text,
                ) for comment in comments
            ]
        )
        return commentlist


@dict_search.post("/search/word", response_model=WordSearchResponse)
async def search(request: Request, body: SearchRequest, user=Depends(get_current_user)):
    """
    精确搜索
    :param request:
    :param body: 单词是依据list返回清单中的内容动态更新对数据库text字段进行精确匹配的
    :param user:
    :return:
    """
    redis = request.app.state.redis

    query = body.query

    if body.language == 'fr':
        query = normalize_text(query)
        word_contents = await (
            DefinitionFr
            .filter(word__text=query)
            .prefetch_related("word")
        )
        if not word_contents:
            raise HTTPException(status_code=404, detail="Word not found")

        # 修改freq
        first_word = word_contents[0].word
        current_freq = first_word.freq
        first_word.freq = current_freq + 1
        await first_word.save()

        pos_seen = set()
        pos_contents = []
        contents: List[SearchItemFr] = []
        for wc in word_contents:
            if wc.pos not in pos_seen:
                pos_seen.add(wc.pos)
                pos_contents.append(wc.pos)

            contents.append(
                SearchItemFr(
                    pos=wc.pos,
                    chi_exp=wc.meaning,
                    example=wc.example,
                    eng_explanation=wc.eng_explanation,
                )
            )

        await service.search_time_updates(redis)

        return WordSearchResponse(
            query=query,
            pos=pos_contents,
            contents=contents,
        )
    else:
        query_kana = all_in_kana(query)
        print(query)
        word_content = await DefinitionJp.filter(
            word__text=query,
            word__hiragana=query_kana,
        ).prefetch_related("word", "pos")
        if not word_content:
            raise HTTPException(status_code=404, detail="Word not found")

        first_def = word_content[0]
        first_word = first_def.word
        first_word.freq = first_word.freq + 1
        await first_word.save()
        pos_list = await first_def.pos
        pos_contents = [p.pos_type for p in pos_list]

        contents: List[SearchItemJp] = []
        for wc in word_content:
            contents.append(
                SearchItemJp(
                    chi_exp=wc.meaning,
                    example=wc.example,
                )
            )

        await service.search_time_updates(redis)

        return WordSearchResponse(
            query=query,
            pos=pos_contents,
            contents=contents,
            hiragana=query_kana,
        )


# TODO 相关度排序（转换为模糊匹配）
# TODO 输入搜索框时反馈内容

@dict_search.post("/search/list/word")
async def search_word_list(query_word: SearchRequest, user=Depends(get_current_user)):
    """
    检索时的提示接口
    :param query_word: 用户输入的内容
    :param user:
    :return: 待选列表
    """
    # print(query_word.query, query_word.language, query_word.sort, query_word.order)
    query = query_word.query
    lang = query_word.language
    query, search_lang, transable = await service.detect_language(text=query)
    word_contents = []
    if lang == "fr":
        if search_lang == "fr":
            word_contents = await service.suggest_autocomplete(
                query=query,
                dict_lang="fr",
                model=WordlistFr,
            )
            if not transable:
                word_contents.extend(
                    await service.search_definition_by_meaning(
                        query=query,
                        model=DefinitionFr,
                        lang="en",
                    )
                )
        else:
            word_contents = await service.search_definition_by_meaning(
                query=query_word.query,
                model=DefinitionFr,
                lang="zh",
            )
    else:
        if search_lang == "jp":
            word_contents = await service.suggest_autocomplete(
                query=query,
                dict_lang="jp",
                model=WordlistJp,
            )
        elif search_lang == "zh":
            word_contents = []
            word_contents.extend(
                await service.search_definition_by_meaning(
                    query=query_word.query,
                    model=DefinitionJp,
                    lang="zh",
                )
            )
            if transable:
                word_contents = await service.suggest_autocomplete(
                    query=query,
                    dict_lang="jp",
                    model=WordlistJp,
                )
        else:
            word_contents = await service.suggest_autocomplete(
                query=query,
                dict_lang="jp",
                model=WordlistJp,
            )
    suggest_list = service.merge_word_results(word_contents)
    return {"list": suggest_list}


@dict_search.post("/search/list/proverb")
async def search_proverb_list(query_word: ProverbSearchRequest, user=Depends(get_current_user)):
    query, lang, transable = await service.detect_language(text=query_word.query)
    query = normalize_text(query_word.query) if lang == "fr" else query_word.query
    suggest_proverbs = await service.suggest_proverb(
        query=query_word.query,
        lang=lang,
        model=ProverbFr,
        search_field="search_text",
    )
    return {"list": suggest_proverbs}


@dict_search.post("/search/proverb")
async def search_proverb(proverb_id: int = Form(...), user=Depends(get_current_user)):
    result = await service.accurate_idiom_proverb(search_id=proverb_id, model=ProverbFr,
                                                  only_fields=["id", "text", "chi_exp"])

    return {"result": result}


@dict_search.post("/search/list/idiom")
async def search_idiom_list(
        query_idiom: ProverbSearchRequest,
        user=Depends(get_current_user)
):
    """日语成语检索接口（带语言检测与分类逻辑）"""

    if query_idiom.dict_language == "fr":
        raise HTTPException(status_code=400, detail="Dict language Error")

    # 语言检测
    mapping_query, lang, is_kangji = await service.detect_language(text=query_idiom.query)
    query = query_idiom.query

    # 初始化任务列表（后续依任务顺序返回）
    tasks = []

    # --- 1️⃣ 日语输入 ---
    if lang == "jp":
        if is_kangji:
            tasks.append(
                service.suggest_proverb(
                    query=query,
                    lang="jp",
                    model=IdiomJp,
                    search_field="text",
                )
            )
            tasks.append(
                service.suggest_proverb(
                    query=all_in_kana(query),
                    lang="jp",
                    model=IdiomJp,
                    search_field="search_text",
                    target_field="text",
                )
            )
        else:
            tasks.append(
                service.suggest_proverb(
                    query=query,
                    lang="jp",
                    model=IdiomJp,
                    search_field="search_text",
                    target_field="text",
                )
            )

    # --- 2️⃣ 中文输入（调整优先级） ---
    elif lang == "zh":
        # ✅ (1) 若存在映射：mapping_query 优先匹配日语原型（text）
        if is_kangji and mapping_query:
            tasks.append(
                service.suggest_proverb(
                    query=mapping_query,
                    lang="jp",
                    model=IdiomJp,
                    search_field="text",
                )
            )

        # ✅ (2) 然后匹配中文释义（chi_exp 或 search_text）
        tasks.append(
            service.suggest_proverb(
                query=query,
                lang="zh",
                model=IdiomJp,
                target_field="text",
            )
        )

        # ✅ (3) 最后用假名匹配映射（辅助补全）
        if is_kangji and mapping_query:
            tasks.append(
                service.suggest_proverb(
                    query=all_in_kana(mapping_query),
                    lang="jp",
                    model=IdiomJp,
                    search_field="search_text",
                )
            )

    # --- 3️⃣ 其他语言（默认回退） ---
    else:
        tasks.append(
            service.suggest_proverb(
                query=query,
                lang="jp",
                model=IdiomJp,
                search_field="search_text",
                target_field="text",
            )
        )

    # ✅ 并发执行任务（结果顺序与任务定义顺序一致）
    results = await asyncio.gather(*tasks)

    # ✅ 顺序合并 + 稳定去重
    seen = set()
    ordered_unique = []
    for res in results:
        for item in res:
            key = item.get("proverb") or item.get("text")
            if key and key not in seen:
                seen.add(key)
                ordered_unique.append(item)

    return {"list": ordered_unique}



@dict_search.post("/search/idiom")
async def search_idiom(query_id: int, user=Depends(get_current_user)):
    result = await service.accurate_idiom_proverb(search_id=query_id, model=IdiomJp,
                                                  only_fields=["id", "text", "search_text", "chi_exp", "example"])
    return {"result": result}
