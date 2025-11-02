from typing import Literal, List, Union, Optional

from pydantic import BaseModel

from app.schemas.admin_schemas import PosEnumFr


class SearchRequest(BaseModel):
    query: str
    language: Literal['fr', 'jp']
    sort: Literal['relevance', 'date'] = 'date'
    order: Literal['asc', 'des'] = 'des'

class ProverbSearchRequest(BaseModel):
    query: str
    dict_language: Literal['fr', 'jp'] = "fr"


class SearchItemJp(BaseModel):
    chi_exp: str
    example: str


class SearchItemFr(BaseModel):
    pos: PosEnumFr
    chi_exp: str
    eng_explanation: str
    example: Optional[str]


class WordSearchResponse(BaseModel):
    query: str
    pos: list
    contents: Union[List[SearchItemFr], List[SearchItemJp]]


class ProverbSearchResponse(BaseModel):
    proverb_text: str
    chi_exp: str
