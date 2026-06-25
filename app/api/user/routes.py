from datetime import datetime, timezone
from typing import Tuple, Dict

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Depends, Request
from tortoise.exceptions import IntegrityError

from app.api.user.user_schemas import UserIn, UpdateUserRequest, UserLoginRequest, UserResetPhoneRequest, \
    VerifyPhoneCodeRequest, UserResetEmailRequest, UserResetPasswordRequest, VerifyEmailRequest, RefreshTokenRequest, \
    LogoutRequest, BindPhoneRequest
from app.core.redis import get_redis
from app.models.base import ReservedWords, User, Language
from app.utils.security import get_current_user
from . import service
from .auth_wechat.routes import auth_wechat_router
from .id_verfication.routes import id_verification_router

users_router = APIRouter()

users_router.include_router(auth_wechat_router, prefix="/auth/wechat", tags=["wechat login APIs"])
users_router.include_router(id_verification_router, prefix="/auth/id_verify", tags=["ID Verification APIs"])


@users_router.post("/register")
async def register(req: Request, user_in: UserIn):
    await service.validate_username(user_in.username)
    await service.validate_password(user_in.password)
    await service.validate_email_exists(user_in.email)

    hashed_pwd = service.hash_password(user_in.password)

    lang_pref = await Language.get(code=user_in.lang_pref)

    try:
        new_user = await User.create(
            name=user_in.username,
            email=user_in.email or None,
            pwd_hashed=hashed_pwd,
            language=lang_pref,
        )
    except IntegrityError:
        raise HTTPException(status_code=400, detail="用户名或邮箱已被注册")

    token = service.token_issuer(user_id=new_user.id, is_admin=new_user.is_admin)

    return {
        "id": new_user.id,
        "message": "register success",
        "access_token": token,
        "token_type": "bearer",
    }


@users_router.post("/phone")
async def bind_phone(
        req: Request,
        body: BindPhoneRequest,
        current_user: Tuple[User, Dict] = Depends(get_current_user),
):
    user, _ = current_user
    if user.phone_hash:
        raise HTTPException(status_code=400, detail="手机号已绑定")

    phone = req.app.state.phone_encrypto.normalize(body.phone_number)
    phone_hash = req.app.state.phone_encrypto.hash(phone)
    await service.validate_phone_available(phone_hash)

    phone_ok = await service.verify_phone_code(
        redis=req.app.state.redis,
        phone=phone,
        input_code=body.code,
    )
    if not phone_ok:
        raise HTTPException(status_code=400, detail="短信验证码错误或已过期")

    user.encrypted_phone = req.app.state.phone_encrypto.encrypt(phone)
    user.phone_hash = phone_hash
    await user.save(update_fields=["encrypted_phone", "phone_hash"])

    return {"message": "手机号绑定成功"}


@users_router.post("/phone_verify")
async def bind_phone_verify(req: Request, user_phone: UserResetPhoneRequest):
    phone = req.app.state.phone_encrypto.normalize(user_phone.phone_number)
    phone_hash = req.app.state.phone_encrypto.hash(phone)
    await service.validate_phone_available(phone_hash)

    code = service.generate_code()
    redis = req.app.state.redis
    await service.send_phone_code(redis=redis, phone=phone, code=code, ops_type="reg")

    return {"message": "验证码已发送"}


@users_router.post("/register/email_verify")
async def register_email_verify(req: Request, user_email: UserResetEmailRequest):
    await service.validate_email_exists(user_email.email)

    code = service.generate_code()
    redis = req.app.state.redis

    await service.save_varify_code(redis, email=user_email.email, code=code)
    await service.send_email_code(
        redis=redis,
        email=user_email.email,
        code=code,
        ops_type="reg"
    )

    print(f"[DEBUG] 给 {user_email.email} 发送验证码：{code}")

    return {"message": "验证码已发送"}


@users_router.post("/register/phone_verify")
async def register_phone_verify(req: Request, user_phone: UserResetPhoneRequest):
    phone = req.app.state.phone_encrypto.normalize(user_phone.phone_number)
    phone_hash = req.app.state.phone_encrypto.hash(phone)
    await service.validate_phone_available(phone_hash)

    code = service.generate_code()
    redis = req.app.state.redis
    await service.send_phone_code(redis=redis, phone=phone, code=code, ops_type="reg")

    return {"message": "验证码已发送"}


@users_router.put("/update", deprecated=False)
async def user_modification(updated_user: UpdateUserRequest,
                            current_user: Tuple[User, Dict] = Depends(get_current_user)):
    """

    :param updated_user: Pydantic 模型验证修改内容（根据JSON内容修改对应字段）
    :param current_user:
    :return:
    """
    user, _ = current_user
    reserved_words = await ReservedWords.filter(category="username").values_list("reserved", flat=True)
    # 验证当前密码
    if not updated_user.current_password:
        raise HTTPException(status_code=400, detail="缺少当前密码")
    if not await service.verify_password(updated_user.current_password, user.pwd_hashed):
        raise HTTPException(status_code=400, detail="原密码错误")

    # 修改用户名（如果提供）
    if updated_user.new_username:
        if updated_user.new_username.lower() in reserved_words:
            raise HTTPException(status_code=400, detail="用户名为保留关键词，请更换")
        user.name = updated_user.new_username

    # 修改密码（如果提供）
    if updated_user.new_password:
        await service.validate_password(updated_user.new_password)
        user.pwd_hashed = service.hash_password(updated_user.new_password)

    if updated_user.new_language:
        lang_pref = await Language.get(code=updated_user.new_language)
        user.language = lang_pref

    await user.save()
    await user.fetch_related("language")

    return {
        "message": "用户信息更新成功",
        "user": service.serialize_user(user),
    }


@users_router.post("/login")
async def user_login(request: Request, user_in: UserLoginRequest):
    user = await User.get_or_none(name=user_in.name).prefetch_related("language")
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not await service.verify_password(user_in.password, user.pwd_hashed):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    return await service.build_login_response(
        redis=request.app.state.redis,
        user=user,
        login_type="password",
    )


@users_router.post("/refresh")
async def refresh_session(request: Request, data: RefreshTokenRequest):
    return await service.refresh_user_session(
        redis=request.app.state.redis,
        refresh_token=data.refresh_token,
    )


@users_router.get("/me")
async def get_my_profile(user_payload: Tuple[User, Dict] = Depends(get_current_user)):
    user, payload = user_payload
    await user.fetch_related("language")
    login_type = payload.get("login_type")
    return service.serialize_user(user, login_type=login_type)


@users_router.post("/logout")
async def user_logout(
        request: Request,
        redis_client: redis.Redis = Depends(get_redis),
        user_data: Tuple[User, Dict] = Depends(get_current_user),
        body: LogoutRequest | None = None,
):
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

    if body and body.refresh_token:
        try:
            refresh_payload = service.decode_refresh_token(body.refresh_token)
        except HTTPException:
            refresh_payload = None

        if refresh_payload and int(refresh_payload.get("user_id")) == user.id:
            await service.revoke_refresh_session(redis=redis_client, jti=refresh_payload["jti"])

    return {"message": "logout ok"}


# 后续通过参数合并
@users_router.post("/auth/forget-password/phone", deprecated=True)
async def forget_password(request: Request, user_request: UserResetPhoneRequest):
    phone = request.app.state.phone_encrypto.normalize(user_request.phone_number)
    phone_hash = request.app.state.phone_encrypto.hash(phone)
    user = await User.get_or_none(phone_hash=phone_hash)

    if not user:
        raise HTTPException(status_code=404, detail="User does not exists")

    redis = request.app.state.redis
    code = service.generate_code()
    await service.send_phone_code(redis=redis, phone=phone, code=code, ops_type="reset")

    print(f"[DEBUG] 给 {phone} 发送验证码：{code}")

    return {"message": "验证码已发送"}


# TODO 后续升级为防止爆破测试手机号的

@users_router.post("/auth/varify_code", deprecated=True)
async def varify_code(data: VerifyPhoneCodeRequest, request: Request):
    redis = request.app.state.redis
    phone = request.app.state.phone_encrypto.normalize(data.phone)
    phone_hash = request.app.state.phone_encrypto.hash(phone)
    reset_token = await service.verify_and_get_reset_token_by_phone(
        redis=redis,
        phone=phone,
        phone_hash=phone_hash,
        input_code=data.code,
    )
    if not reset_token:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    return {
        "reset_token": reset_token,
    }


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

    return {"message": "密码重置成功"}
