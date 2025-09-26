from typing import Tuple, Dict, Annotated

import redis.asyncio as redis
from fastapi import HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError

from app.models.base import User
from settings import settings

redis_client = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
ALGORITHM = "HS256"


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
