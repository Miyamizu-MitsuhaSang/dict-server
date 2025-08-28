from typing import Literal, List, Union

from pydantic import BaseModel

from app.models import PosType
from app.schemas.admin_schemas import PosEnumFr


class SearchRequest(BaseModel):
    query: str
    language: Literal['fr', 'jp']
    sort: Literal['relevance', 'date'] = 'date'
    order: Literal['asc', 'des'] = 'des'


class SearchItemJp(BaseModel):
    chi_exp: str
    example: str


class SearchItemFr(BaseModel):
    pos: PosEnumFr
    chi_exp: str
    eng_explanation: str
    example: str


class SearchResponse(BaseModel):
    query: str
    pos: list
    contents: Union[List[SearchItemFr], List[SearchItemJp]]
