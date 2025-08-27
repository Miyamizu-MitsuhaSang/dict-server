from enum import Enum

from pydantic import BaseModel, validator, field_validator, Field
from typing import Optional, Literal, List


class PosEnumFr(str, Enum):
    # noun
    n = "n."
    n_f = "n.f."
    n_f_pl = "n.f.pl."
    n_m = "n.m."
    n_m_pl = "n.m.pl."
    # verb
    v = "v."
    v_t = "v.t."
    v_i = "v.i."
    v_pr = "v.pr."
    v_t_i = "v.t./v.i."
    v_t_dir = "v.t.dir."
    v_t_ind = "v.t.ind."
    v_t_pr = "v.t.(v.pr.)"
    v_i_ind = "v.t.ind./v.i."

    adj = "adj."  # adj
    adv = "adv."  # adv
    prep = "prep."  # prep
    pron = "pron."  # pron
    conj = "conj."
    interj = "interj."
    chauff = "chauff"
    art = "art."



class PosEnumJp(str, Enum):
    noun = "名词"
    adj = "形容词"
    adj_v = "形容动词"
    adv = "连用"
    v1 = "一段动词"
    v5 = "五段动词"
    help = "助词"
    self = "自动词"
    other = "他动词"
    tail = "接尾"
    self_other = "自他动词"
    follow = "接续"
    habit = "惯用"
    excl = "感叹词"
    ka_v = "カ変"
    sa_v = "サ変"
    conn = "连体"
    quantity = "量词"
    pron = "代词"

class CreateWord(BaseModel):
    word: str
    language: Literal["fr", "jp"]
    pos: str = Field(title="词性", description="必须符合对应语言词性枚举")
    meaning: str
    example: Optional[str]
    eng_explanation: Optional[str]

    class Config:
        orm_mode = True
        title = "接受新词条模型"

    @classmethod
    @field_validator("eng_explanation")
    def validate_eng_explanation(cls, v):
        if cls.language == "jp" and v:
            raise ValueError("Japanese word has no English explanation")
        if cls.language == "fr" and v is None or v == "":
            raise ValueError("French word must have English explanation")
        return v

    @classmethod
    @field_validator("pos")
    def validate_pos(cls, v):
        if cls.language == "fr" and v not in PosEnumFr:
            raise ValueError("Pos is not a valid type")
        if cls.language == "jp" and v not in PosEnumJp:
            raise ValueError("Pos is not a valid type")
        return v


class UpdateWord(BaseModel):
    id: int
    word: str
    language: Literal["fr", "jp"]
    eng_explanation: Optional[str]
    example: Optional[str]
    pos: Optional[str]
    meaning: Optional[str]

    class Config:
        orm_mode = True  # 允许从 ORM 实例中提取字段，而不仅限于 dict 类型


class UpdateWordSet(List[UpdateWord]):
    pass


class SearchWordRequest(BaseModel):
    word: str
    language: Literal["fr", "jp"]
    pos: Optional[str]

    @classmethod
    @field_validator("pos")
    def validate_pos(cls, v):
        if v is not None:
            if cls.language is "fr" and v not in PosEnumFr:
                raise ValueError("Pos is not a valid type")
            if cls.language is "jp" and v not in PosEnumJp:
                raise ValueError("Pos is not a valid type")
        return v
