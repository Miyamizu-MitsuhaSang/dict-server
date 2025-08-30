import re
import bcrypt
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Tuple, Dict, Annotated
from fastapi import HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
import redis.asyncio as redis

from app.models.base import ReservedWords, User

from settings import settings

redis_client = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
ALGORITHM = "HS256"


async def validate_username(username: str):
    # 长度限制
    if not (3 <= len(username) <= 20):
        raise ValueError('用户名长度必须在3到20个字符之间')
    # 只能包含字母、数字和下划线
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', username):
        raise ValueError('用户名只能包含字母、数字和下划线，且不能以数字开头')
    # 保留词
    reserved_words = await ReservedWords.filter(category="username").values_list("reserved", flat=True)
    if username.lower() in {w.lower() for w in reserved_words}:
        raise HTTPException(status_code=400, detail="用户名为保留关键词，请更换")


async def validate_password(password: str):
    if not (6 <= len(password) <= 20):
        raise HTTPException(status_code=400, detail="密码长度必须在6到20之间")
    if not re.search(r'\d', password):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个数字")
    # 检查是否包含允许的特殊字符（白名单方式）
    allowed_specials = r"!@#$%^&*()_\-+=\[\]{};:'\",.<>?/\\|`~"
    if re.search(fr"[^\da-zA-Z{re.escape(allowed_specials)}]", password):
        raise HTTPException(
            status_code=400,
            detail=f"密码只能包含字母、数字和常见特殊字符 {allowed_specials}"
        )


# 登陆校验
async def verify_password(raw_password: str, hashed_password: str) -> bool:
    """
        校验用户登录时输入的密码是否与数据库中保存的加密密码匹配。

        参数：
            raw_password: 用户登录时输入的明文密码
            hashed_password: 数据库存储的加密密码字符串（password_hash）

        返回：
            如果密码匹配，返回 True；否则返回 False
        """
    return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))


# 注册或修改密码时加密
def hash_password(raw_password: str) -> str:
    """
        将用户输入的明文密码进行加密（哈希）后返回字符串，用于保存到数据库中。

        参数：
            raw_password: 用户输入的明文密码

        返回：
            加密后的密码字符串（含盐），可直接保存到数据库字段如 password_hash 中
        """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(raw_password.encode("utf-8"), salt).decode("utf-8")


# @asynccontextmanager
# async def redis_pool():
#     client = redis.Redis(host="localhost", port=6379, decode_responses=True)
#     yield client


async def _extract_bearer_token(request: Request) -> str:
    """
    小工具：提取 Bearer Token（兼容大小写/多空格）
    :return: token
    """
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="未登录")
    # 兼容 "bearer" / "Bearer" 等写法，并裁剪多余空格
    parts = auth.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="无效的授权头")
    return parts[1]  # token 内容


async def _decode_and_load_user(token: str) -> Tuple[User, Dict]:
    # 黑名单校验（登出或主动失效）
    if await redis_client.get(f"blacklist:{token}") == "true":
        raise HTTPException(status_code=401, detail="token 已失效")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登陆信息已过期")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的令牌")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效 token 载荷")
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user, payload


# 从请求头中获取当前用户信息
async def get_current_user_basic(request: Request) -> Tuple[User, Dict]:
    token = await _extract_bearer_token(request)
    return await _decode_and_load_user(token)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


async def get_current_user_with_oauth(
        token: Annotated[str, Depends(oauth2_scheme)]
) -> Tuple[User, Dict]:
    return await _decode_and_load_user(token)


async def get_current_user(
        request: Request,
        token: Annotated[str, Depends(oauth2_scheme)] = None
) -> Tuple[User, Dict]:
    if settings.USE_OAUTH:
        return await get_current_user_with_oauth(token)
    return await get_current_user_basic(request)


async def is_admin_user(
    user_payload: Tuple[User, Dict] = Depends(get_current_user),
) -> Tuple[User, Dict]:
    user, payload = user_payload
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Access denied")
    return user, payload
