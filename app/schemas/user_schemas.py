from pydantic import BaseModel
from typing import Literal, Optional

default_portrait_url = '#'


class UserIn(BaseModel):
    username: str
    password: str
    lang_pref: Literal['jp', 'fr', 'private'] = "private"
    portrait: str = default_portrait_url

    # @field_validator('username')
    # @classmethod
    # def validate_username(cls, v):
    #     if not (3 <= len(v) <= 20):
    #         raise ValueError("用户名长度必须在3到20个字符之间")
    #     if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', v):
    #         raise ValueError("用户名只能包含字母、数字和下划线，且不能以数字开头")
    #     return v

    # 校验密码
    # @field_validator("password")
    # @classmethod
    # def verify_password(cls, password: str):
    #     if len(password) < 6 or len(password) > 20:
    #         raise ValueError("Password must be between 6 and 20 characters")
    #         # 检查是否包含至少一个数字
    #     if not re.search(r'\d', password):
    #         raise ValueError('密码必须包含至少一个数字')
    #     # 检查是否包含非法特殊字符（只允许字母和数字）
    #     if re.search(r'[^a-zA-Z0-9]', password):
    #         raise ValueError('密码不能包含特殊字符')
    #     return password

    # @field_validator('lang_pref')
    # @classmethod
    # def validate_lang_pref(cls, v):
    #     assert v in ('jp', 'en')
    #     return v


class UserOut(BaseModel):
    name: str
    potrait: str = '#'


class UpdateUserRequest(BaseModel):
    current_password: Optional[str] = None
    new_username: Optional[str] = None
    new_password: Optional[str] = None
    new_language: Literal["jp", "fr", "private"] = "private"

    # lang_pref: str = "jp"


class UserLoginRequest(BaseModel):
    name: str
    password: str
