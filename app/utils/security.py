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

from settings import SECRET_KEY

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


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
    if re.search(r'[^a-zA-Z0-9]', password):
        raise HTTPException(status_code=400, detail="密码不能包含特殊字符，只能包含字母和数字")


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


@asynccontextmanager
async def redis_pool():
    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    yield client


# 从请求头中获取当前用户信息
async def get_current_user(request: Request) -> Tuple[User, Dict]:
    # 从 headers 中获取 Authorization 字段
    token = request.headers.get("Authorization")

    # 检查 token 是否存在且格式正确（Bearer 开头）
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    raw_token = token[7:]

    # 黑名单校验
    if await redis_client.get(f"blacklist:{raw_token}") == "true":
        raise HTTPException(status_code=401, detail="token 已失效")

    try:
        # 去掉 "Bearer " 前缀后解析 JWT
        payload = jwt.decode(token[7:], SECRET_KEY, algorithms=["HS256"])  # 自动校验exp
        user_id = payload.get("user_id")
    except ExpiredSignatureError:
        # token 信息中的 exp 已经过期
        raise HTTPException(status_code=401, detail="登陆信息已过期")
    except JWTError:
        # JWT 格式错误或校验失败
        raise HTTPException(status_code=401, detail="无效的令牌")

    # 从数据库查找对应用户
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user, payload


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/logout")
ALGORITHM = "HS256"


async def get_current_user_with_OAuth(token: Annotated[str, Depends(oauth2_scheme)]):
    # TODO OAuth验证
    # Redis 黑名单检查
    blacklisted = await redis_client.get(f"blacklist:{token}")
    if blacklisted:
        raise HTTPException(status_code=401, detail="Token 已失效")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无效 token")
        user = await User.get_or_none(id=user_id)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        return user, payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token 已过期")
    except JWTError:
        raise HTTPException(status_code=401, detail="")

