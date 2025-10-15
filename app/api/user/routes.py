from datetime import datetime, timedelta, timezone
from typing import Tuple, Dict

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Depends, Request
from jose import jwt

from app.api.user.user_schemas import UserIn, UpdateUserRequest, UserLoginRequest, UserResetPhoneRequest, \
    VerifyPhoneCodeRequest, UserResetEmailRequest, UserResetPasswordRequest, VerifyEmailRequest
from app.core.redis import get_redis
from app.models.base import ReservedWords, User, Language
from app.utils.security import get_current_user
from settings import settings
from . import service

users_router = APIRouter()


@users_router.post("/register")
async def register(req: Request, user_in: UserIn):
    await service.validate_username(user_in.username)
    await service.validate_password(user_in.password)
    # await service.validate_email_exists(user_in.email)
    result = await service.verify_email_code(
        redis=req.app.state.redis,
        email=user_in.email,
        input_code=user_in.code
    )
    if not result:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    hashed_pwd = service.hash_password(user_in.password)

    lang_pref = await Language.get(code=user_in.lang_pref)

    encrypted_phone = (
        req.app.state.phone_encrypto.encrypt(user_in.phone)) \
        if user_in.phone else None

    new_user = await User.create(
        name=user_in.username,
        email=user_in.email,
        pwd_hashed=hashed_pwd,
        language=lang_pref,
        encrypted_phone=encrypted_phone,
    )
    return {
        "id": new_user.id,
        "message": "register success",
    }


@users_router.post("/register/email_verify")
async def register_email_verify(req: Request, user_email: UserResetEmailRequest):
    await service.validate_email_exists(user_email.email)

    code = service.generate_code()
    redis = req.app.state.redis

    await service.save_email_code(redis, email=user_email.email, code=code)
    await service.send_email_code(
        redis=redis,
        email=user_email.email,
        code=code,
        ops_type="reg"
    )

    print(f"[DEBUG] 给 {user_email.email} 发送验证码：{code}")

    return {"message": "验证码已发送"}


@users_router.put("/update", deprecated=False)
async def user_modification(updated_user: UpdateUserRequest, current_user: Tuple[User, Dict] = Depends(get_current_user)):
    """

    :param updated_user: Pydantic 模型验证修改内容（根据JSON内容修改对应字段）
    :param current_user:
    :return:
    """
    reserved_words = await ReservedWords.filter(category="username").values_list("reserved", flat=True)
    # 验证当前密码
    if not await service.verify_password(updated_user.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    # 修改用户名（如果提供）
    if updated_user.new_username:
        if updated_user.new_username.lower() in reserved_words:
            raise HTTPException(status_code=400, detail="用户名为保留关键词，请更换")
        current_user.username = updated_user.new_username

    # 修改密码（如果提供）
    if updated_user.new_password:
        current_user.password_hash = service.hash_password(updated_user.new_password)


@users_router.post("/login")
async def user_login(user_in: UserLoginRequest):
    user = await User.get_or_none(name=user_in.name)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not await service.verify_password(user_in.password, user.pwd_hashed):
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

    await redis_client.setex(f"blacklist:{raw_token}", ttl, "true")

    return {"message": "logout ok"}


# 后续通过参数合并
@users_router.post("/auth/forget-password/phone", deprecated=True)
async def forget_password(request: Request, user_request: UserResetPhoneRequest):
    encrypted_phone = request.app.state.phone_encrypto.encrypt(phone=user_request.phone)
    user = await User.get_or_none(encrypted_phone=encrypted_phone)

    if not user:
        raise HTTPException(status_code=404, detail="User does not exists")

    redis = request.app.state.Redis
    code = service.generate_code()
    await service.save_code_redis(redis, phone=user_request.phone_number, code=code)

    # TODO 短信服务

    print(f"[DEBUG] 给 {user_request.phone_number} 发送验证码：{code}")

    return {"message": "验证码已发送"}


# TODO 后续升级为防止爆破测试手机号的

@users_router.post("/auth/varify_code", deprecated=True)
async def varify_code(data: VerifyPhoneCodeRequest, request: Request):
    redis = request.app.state.redis
    if not await service.verify_code(redis=redis, phone=data.phone, input_code=data.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    return {"message": "验证成功，可以重置密码"}


@users_router.post("/auth/forget-password/email", deprecated=False, description="邮箱遗忘接口")
async def email_forget_password(request: Request, user_request: UserResetEmailRequest):
    """
    用户点击验证邮箱时启用
    :param request:
    :param user_request:
    :return:
    """
    user_email = user_request.email
    user = await User.get_or_none(email=user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User does not exists")

    redis = request.app.state.redis
    code = service.generate_code()
    # await service.save_email_code(redis, email=user_request.email, code=code)

    # 邮箱服务
    await service.send_email_code(redis, user_request.email, code, ops_type="reset")

    print(f"[DEBUG] 给 {user_request.email} 发送验证码：{code}")

    return {"message": "验证码已发送"}


@users_router.post("/auth/varify_code/email")
async def email_varify_code(request: Request, data: VerifyEmailRequest):
    redis = request.app.state.redis
    reset_token = await service.verify_and_get_reset_token(redis=redis, email=data.email, input_code=data.code)
    if not reset_token:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    return {
        "reset_token": reset_token,
    }


@users_router.post("/auth/reset-password", deprecated=False)
async def reset_password(request: Request, reset_request: UserResetPasswordRequest):
    # 校验密码是否合法
    await service.validate_password(password=reset_request.password)

    redis = request.app.state.redis
    reset_token = request.headers.get("x-reset-token")
    user_id = await service.is_reset_password(redis=redis, token=reset_token)

    new_password = service.hash_password(raw_password=reset_request.password)

    await User.filter(id=user_id).update(pwd_hashed=new_password)

    return {"massage": "密码重置成功"}
