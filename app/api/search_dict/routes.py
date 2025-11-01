from typing import Literal, List

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.search_dict import service
from app.api.search_dict.search_schemas import SearchRequest, WordSearchResponse, SearchItemFr, SearchItemJp, \
    ProverbSearchRequest
from app.api.search_dict.service import suggest_autocomplete
from app.api.word_comment.word_comment_schemas import CommentSet
from app.models import DefinitionJp, CommentFr, CommentJp
from app.models.fr import DefinitionFr
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


@dict_search.post("/search/proverb")
async def proverb(request: Request, proverb_id: int, user=Depends(get_current_user)):
    """
    用于法语谚语搜索
    :param request:
    :param body: 要求用户输入的内容必须为法语
    :param user:
    :return:
    """
    content = await service.accurate_proverb(proverb_id=proverb_id)
    return content


# TODO 相关度排序（转换为模糊匹配）
# TODO 输入搜索框时反馈内容

@dict_search.post("/search/word/list")
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


@dict_search.post("/search/proverb/list")
async def search_proverb_list(query_word: ProverbSearchRequest, user=Depends(get_current_user)):
    lang: Literal['fr', 'zh'] = 'zh' if service.contains_chinese(query_word.query) else 'fr'
    suggest_proverbs = await service.suggest_proverb(query=query_word, lang=lang)
    return {"list": suggest_proverbs}
