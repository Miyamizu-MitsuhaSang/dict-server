from typing import Literal, List

import jaconv
import pykakasi
from fastapi import APIRouter, Depends, HTTPException, Request

from app.models import DefinitionJp
from app.models.fr import DefinitionFr
from app.schemas.search_schemas import SearchRequest, SearchResponse, SearchItemFr, SearchItemJp
from app.utils.security import get_current_user
from app.utils.textnorm import normalize_text
from scripts.update_jp import normalize_jp_text

dict_search = APIRouter()

kks = pykakasi.kakasi()
kks.setMode("H", "a")  # 平假名 -> ascii (罗马字)
kks.setMode("K", "a")  # 片假名 -> ascii
kks.setMode("J", "a")  # 汉字   -> ascii
kks.setMode("r", "Hepburn")  # 转换成 Hepburn 罗马字
conv = kks.getConverter()


def all_in_kana(text: str) -> str:
    """
    将输入统一转换为平假名，支持：
    - 平假名
    - 片假名
    - 罗马字 (Hepburn 转写)

    返回：平假名字符串
    """
    if not text:
        return ""

    # 1. 片假名 → 平假名
    normalized = jaconv.kata2hira(text)

    # 2. 如果里面含有罗马字字符，就先转成假名
    if any("a" <= ch.lower() <= "z" for ch in normalized):
        hira = conv.do(normalized)  # 罗马字 -> 平假名
        normalized = jaconv.kata2hira(hira)

    # 3. 再次片假名 -> 平假名保险
    normalized = jaconv.kata2hira(normalized)

    return normalized


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
        query = all_in_kana(query)
        print(query)
        word_content = await DefinitionJp.filter(
            word__text=query
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
