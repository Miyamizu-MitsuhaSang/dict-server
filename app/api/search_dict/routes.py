import asyncio
from typing import Literal, List

from fastapi import APIRouter, Depends, HTTPException, Request, Form

from app.api.search_dict import service
from app.api.search_dict.search_schemas import SearchRequest, WordSearchResponse, SearchItemFr, SearchItemJp, \
    ProverbSearchRequest
from app.api.search_dict.service import suggest_autocomplete, accurate_proverb
from app.api.word_comment.word_comment_schemas import CommentSet
from app.models import DefinitionJp, CommentFr, CommentJp
from app.models.fr import DefinitionFr, ProverbFr
from app.models.jp import IdiomJp
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
        return WordSearchResponse(
            query=query,
            pos=pos_contents,
            contents=contents,
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
    word_contents = await suggest_autocomplete(query=query_word)
    return {"list": word_contents}


@dict_search.post("/search/list/proverb")
async def search_proverb_list(query_word: ProverbSearchRequest, user=Depends(get_current_user)):
    query, lang, _ = service.detect_language(text=query_word.query)
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
    result = await service.accurate_idiom_proverb(search_id=proverb_id, model=ProverbFr, only_fields=["text", "chi_exp"])

    return {"result": result}


@dict_search.post("/search/list/idiom")
async def search_idiom_list(query_idiom: ProverbSearchRequest, user=Depends(get_current_user)):
    if query_idiom.dict_language == "fr":
        raise HTTPException(status_code=400, detail="Dict language Error")

    mapping_query, lang, is_kangji = await service.detect_language(text=query_idiom.query)
    query = all_in_kana(text=query_idiom.query) if lang == "jp" else query_idiom.query

    # ✅ 并发任务列表
    tasks = [
        service.suggest_proverb(
            query=query,
            lang=lang,
            model=IdiomJp,
            search_field="search_text",
            target_field="text",
        )
    ]

    if lang == "zh" and is_kangji:
        # jp_query = all_in_kana(text=query_idiom.query)
        tasks.append(
            service.suggest_proverb(
                query=mapping_query,
                lang="jp",
                model=IdiomJp,
                search_field="text",
            )
        )

    # ✅ 并发执行（返回结果顺序与任务顺序一致）
    results = await asyncio.gather(*tasks)

    # ✅ 合并结果
    result = results[0]
    if len(results) > 1:
        result[:0] = results[1]  # 将中文映射查询结果插到最前面

    return {"list": result}


@dict_search.post("/search/idiom")
async def search_idiom(query_id: int, user=Depends(get_current_user)):
    result = await service.accurate_idiom_proverb(search_id=query_id, model=IdiomJp, only_fields=["id", "text", "search_text", "chi_exp", "example"])
    return {"result": result}
