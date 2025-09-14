from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


class TransRequest(BaseModel):
    from_lang: Literal['fr', 'jp', 'zh'] = 'fr'
    to_lang: Literal['fr', 'jp', 'zh'] = 'zh'

    @field_validator('from_lang', 'to_lang')
    @classmethod
    def validate_lang(cls, v):
        allowed_langs = {'auto', 'fr', 'jp', 'zh'}
        if v not in allowed_langs:
            raise ValueError(f'Unsupported language: {v}')
        return v

    @model_validator(mode="after")
    def check_lang(self):
        if self.from_lang == self.to_lang:
            raise ValueError("from_lang and to_lang cannot be the same")
        elif self.to_lang == 'auto':
            raise ValueError("to_lang cannot be 'auto'")
        return self


class TransResponse(BaseModel):
    translated_text: str
