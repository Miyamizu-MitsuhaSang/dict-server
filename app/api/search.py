from typing import Literal, List

import jaconv
import pykakasi
from fastapi import APIRouter, Depends, HTTPException, Request

from app.models import DefinitionJp
from app.models.fr import DefinitionFr
from app.schemas.search_schemas import SearchRequest, SearchResponse, SearchItemFr, SearchItemJp
from app.utils.all_kana import all_in_kana
from app.utils.autocomplete import suggest_autocomplete
from app.utils.security import get_current_user
from app.utils.textnorm import normalize_text
from scripts.update_jp import normalize_jp_text

dict_search = APIRouter()


@dict_search.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest, user=Depends(get_current_user)):
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
        return SearchResponse(
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
        pos_list = await first_def.pos.all()
        pos_contents = [p.pos_type for p in pos_list]

        contents: List[SearchItemJp] = []
        for wc in word_content:
            contents.append(
                SearchItemJp(
                    chi_exp=wc.meaning,
                    example=wc.example,
                )
            )
        return SearchResponse(
            query=query,
            pos=pos_contents,
            contents=contents,
        )


# TODO 相关度排序（转换为模糊匹配）
# TODO 输入搜索框时反馈内容

@dict_search.post("/search/list")
async def search_list(query_word: SearchRequest, user=Depends(get_current_user)):
    """
    检索时的提示接口
    :param query_word: 用户输入的内容
    :param user:
    :return: 待选列表
    """
    print(query_word.query, query_word.language, query_word.sort, query_word.order)
    word_contents = await suggest_autocomplete(query=query_word)
    return {"list": word_contents}
