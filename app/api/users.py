from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Tuple, Dict
from datetime import datetime, timedelta, timezone
from jose import jwt
import redis.asyncio as redis

from app.models.base import ReservedWords, User, Language
from app.utils.security import verify_password, hash_password, validate_password, validate_username, get_current_user
from settings import settings
from app.core.redis import get_redis

from app.schemas.user_schemas import UserIn, UserOut, UpdateUserRequest, UserLoginRequest

users_router = APIRouter()


@users_router.post("/register", response_model=UserOut)
async def register(user_in: UserIn):
    await validate_username(user_in.username)
    await validate_password(user_in.password)

    hashed_pwd = hash_password(user_in.password)

    lang_pref = await Language.get(code=user_in.lang_pref)

    new_user = await User.create(name=user_in.username,
                                 pwd_hashed=hashed_pwd,
                                 language=lang_pref,  # 后续检查参数是否正确
                                 portrait=user_in.portrait)
    return {
        "id": new_user.id,
        "message": "register success",
    }


@users_router.put("/update", deprecated=False)
async def user_modification(updated_user: UpdateUserRequest, current_user: User = Depends(get_current_user)):
    """

    :param updated_user: Pydantic 模型验证修改内容（根据JSON内容修改对应字段）
    :param current_user:
    :return:
    """
    reserved_words = await ReservedWords.filter(category="username").values_list("reserved", flat=True)
    # 验证当前密码
    if not await verify_password(updated_user.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    # 修改用户名（如果提供）
    if updated_user.new_username:
        if updated_user.new_username.lower() in reserved_words:
            raise HTTPException(status_code=400, detail="用户名为保留关键词，请更换")
        current_user.username = updated_user.new_username

    # 修改密码（如果提供）
    if updated_user.new_password:
        current_user.password_hash = hash_password(updated_user.new_password)

@users_router.post("/login")
async def user_login(user_in: UserLoginRequest):
    user = await User.get_or_none(name=user_in.name)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not await verify_password(user_in.password, user.pwd_hashed):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    # token 中放置的信息
    payload = {
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),  # 设置过期时间
        "is_admin": user.is_admin,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.name,
            "is_admin": user.is_admin
        }
    }


@users_router.post("/logout")
async def user_logout(request: Request,
                      redis_client: redis.Redis = Depends(get_redis),
                      user_data: Tuple[User, Dict] = Depends(get_current_user)):
    user, payload = user_data
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer"):
        raise HTTPException(status_code=401, detail="未登录")

    # 检查 token
    raw_token = token[7:]

    exp = payload.get("exp")
    now = datetime.now(timezone.utc).timestamp()
    ttl = max(int(exp - now), 1) if exp else 7200

    # try:
    #     payload = jwt.decode(raw_token, SECRET_KEY, algorithms=["HS256"])
    #     exp = payload.get("exp")
    #     now = datetime.now(timezone.utc).timestamp()
    #     ttl = int(exp - now) if exp else 7200 # Time To Live: 黑名单生效时长
    # except ExpiredSignatureError:
    #     raise HTTPException(status_code=401, detail="登录信息已过期")
    # except JWTError:
    #     raise HTTPException(status_code=401, detail="无效 token")

    await redis_client.setex(f"blacklist:{raw_token}", ttl, "true")

    return {"message": "logout ok"}
