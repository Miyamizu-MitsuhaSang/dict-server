import random
import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import Literal

import bcrypt
from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from redis.asyncio import Redis

from app.core.email_utils import send_email
from app.core.reset_utils import create_reset_token, save_reset_jti, verify_and_consume_reset_token, ResetTokenError
from app.models.base import ReservedWords, User
from app.utils.message_sender import MessageSender
from settings import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 20
REFRESH_TOKEN_EXPIRE_DAYS = 30
ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_HOURS * 60 * 60
REFRESH_TOKEN_EXPIRE_SECONDS = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
REFRESH_TOKEN_PREFIX = "auth:refresh"


# 校验用户名是否符合规则且未被保留词占用。
async def validate_username(username: str) -> None:
    # 长度限制
    if not (3 <= len(username) <= 20):
        raise HTTPException(status_code=400, detail='用户名长度必须在3到20个字符之间')
    # 只能包含字母、数字和下划线
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', username):
        raise HTTPException(status_code=400, detail='用户名只能包含字母、数字和下划线，且不能以数字开头')
    # 保留词
    reserved_words = await ReservedWords.filter(category="username").values_list("reserved", flat=True)
    if username.lower() in {w.lower() for w in reserved_words}:
        raise HTTPException(status_code=400, detail="用户名为保留关键词，请更换")


# 校验密码长度、复杂度和允许字符集。
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


# 检查邮箱是否已被注册。
async def validate_email_exists(email: str):
    if not email:
        return
    user = await User.get_or_none(email=email)
    if user:
        raise HTTPException(status_code=400, detail="邮箱已经被使用，请更换其他邮箱后重试")


# 检查手机号哈希是否已被注册。
async def validate_phone_available(phone_hash: str):
    user = await User.get_or_none(phone_hash=phone_hash)
    if user:
        raise HTTPException(status_code=400, detail="手机号已经被使用，请更换其他手机号后重试")


# 校验明文密码是否与数据库中的哈希值匹配。
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


# 对用户明文密码进行哈希加密。
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


# 生成指定长度的数字验证码。
def generate_code(length=6):
    return "".join([str(random.randint(0, 9)) for _ in range(length)])


# 将短信验证码写入 Redis。
async def save_code_redis(redis: Redis, phone: str, code: str, expire: int = 300):
    await redis.setex(f"sms:{phone}", expire, code)


# 保存手机验证码，和短信验证码共用同一份 Redis key。
async def save_phone_code(redis: Redis, phone: str, code: str, expire: int = 300):
    await save_code_redis(redis=redis, phone=phone, code=code, expire=expire)


# 验证短信验证码是否正确，成功后删除缓存。
async def varify_phone_code(redis: Redis, phone: str, input_code: str):
    return await verify_phone_code(redis=redis, phone=phone, input_code=input_code)


# 验证手机验证码是否正确，成功后删除缓存。
async def verify_phone_code(redis: Redis, phone: str, input_code: str):
    stored = await redis.get(f"sms:{phone}")
    if stored == input_code:
        await redis.delete(f"sms:{phone}")
        return True
    return False


# 发送短信验证码并同步保存到 Redis。
async def send_sms_code(redis: Redis, phone: str, code: str, ops_type: Literal["reg", "wechat", "reset"]):
    await send_phone_code(redis=redis, phone=phone, code=code, ops_type=ops_type)


# 发送手机验证码并同步保存到 Redis。
async def send_phone_code(redis: Redis, phone: str, code: str, ops_type: Literal["reg", "wechat", "reset"]):
    ops_dict = {
        "reg": "用户注册",
        "wechat": "微信登录/绑定",
        "reset": "密码重置",
    }
    sender = MessageSender()
    await sender.send_sms(phone=phone, code=code)
    await save_phone_code(redis, phone, code)
    print(f"[DEBUG][SMS] 给 {phone} 发送验证码：{code}，用途：{ops_dict[ops_type]}")


# 将邮箱验证码写入 Redis。
async def save_email_code(redis: Redis, email: str, code: str, expire: int = 300):
    await redis.setex(f"email:{email}", expire, code)


# 兼容旧命名：保存邮箱验证码。
async def save_varify_code(redis: Redis, email: str, code: str, expire: int = 300):
    await save_email_code(redis=redis, email=email, code=code, expire=expire)


# 发送邮箱验证码并保存缓存中的验证码。
async def send_email_code(redis: Redis, email: str, code: str, ops_type: Literal["reg", "reset"]):
    await save_email_code(redis, email, code)

    ops_dict = {
        "reg": "用户注册",
        "reset": "密码重置",
    }
    subject = "Lexiverse 用户邮箱验证码"
    content = f"""<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="utf-8">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Lexiverse 验证码</title>
    <style>
      @media (prefers-color-scheme: dark) {{
        body, .email-body {{ background: #0f172a !important; color: #e5e7eb !important; }}
        .card {{ background: #111827 !important; border-color: #374151 !important; }}
        .muted {{ color: #9ca3af !important; }}
        .code-box {{ background:#1f2937 !important; color:#fff !important; border-color:#374151 !important; }}
      }}
    </style>
    </head>
    <body style="margin:0;padding:0;background:#f5f7fb;font-family:'Microsoft Yahei','Arial',sans-serif;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fb;">
        <tr>
          <td align="center" style="padding:24px;">
            <table role="presentation" width="600" cellpadding="0" cellspacing="0" class="email-body" style="width:600px;max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;">

              <!-- Header -->
              <tr>
                <td style="background:linear-gradient(90deg,#4f46e5,#06b6d4);padding:22px 24px;">
                  <h1 style="margin:0;font-size:18px;line-height:1.4;color:#ffffff;">Lexiverse 验证码</h1>
                  <p class="muted" style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,.85);">安全身份校验</p>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:20px 24px;">

                  <p style="margin-top:0;font-size:15px;color:#111827;">您好，</p>
                  <p style="font-size:15px;color:#111827;">
                    您正在进行 <strong>{ops_dict[ops_type]}</strong> 操作
                  </p>

                  <div class="card" style="margin:18px 0;padding:18px;border:1px solid #e5e7eb;border-radius:10px;background:#ffffff;text-align:center;">
                    <div style="font-size:13px;color:#6b7280;margin-bottom:6px;">您的验证码</div>

                    <div class="code-box" style="display:inline-block;padding:12px 24px;border:1px solid #e5e7eb;border-radius:8px;background:#f9fafb;font-size:26px;font-weight:bold;color:#d9534f;letter-spacing:4px;">
                      {code}
                    </div>

                    <div class="muted" style="margin-top:10px;font-size:12px;color:#6b7280;">
                      有效期 5 分钟，请勿泄露给他人
                    </div>
                  </div>

                  <p class="muted" style="margin-top:16px;font-size:12px;color:#9ca3af;">
                    如果这不是您本人的操作，请忽略此邮件
                  </p>

                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding:16px 24px;border-top:1px solid #e5e7eb;">
                  <table width="100%">
                    <tr>
                      <td align="left" class="muted" style="font-size:12px;color:#9ca3af;">
                        这是一封系统通知邮件，请勿直接回复
                      </td>
                      <td align="right" class="muted" style="font-size:12px;color:#9ca3af;">
                        Lexiverse 安全中心
                      </td>
                    </tr>
                    """

    send_email(email, subject, content)


# 验证邮箱验证码是否正确。
async def verify_email_code(redis: Redis, email: str, input_code: str) -> bool:
    stored = await redis.get(f"email:{email}")
    if stored == input_code:
        await redis.delete(f"email:{email}")
        return True
    return False


# 根据邮箱生成找回密码用的重置 token。
async def __get_reset_token(redis: Redis, email: str):
    user = await User.get_or_none(email=email)
    if user is None:
        return None

    reset_token, jti = create_reset_token(user_id=user.id, expire_seconds=300)

    await save_reset_jti(redis, user.id, jti=jti, expire_seconds=300)

    return reset_token


# 先校验邮箱验证码，再返回可用于重置密码的 token。
async def verify_and_get_reset_token(redis: Redis, email: str, input_code: str):
    ok = await verify_email_code(redis, email, input_code)
    if not ok:
        return None

    return await __get_reset_token(redis, email)


# 根据手机号生成找回密码用的重置 token。
async def __get_reset_token_by_phone(redis: Redis, phone_hash: str):
    user = await User.get_or_none(phone_hash=phone_hash)
    if user is None:
        return None

    reset_token, jti = create_reset_token(user_id=user.id, expire_seconds=300)
    await save_reset_jti(redis, user.id, jti=jti, expire_seconds=300)
    return reset_token


# 先校验手机验证码，再返回可用于重置密码的 token。
async def verify_and_get_reset_token_by_phone(redis: Redis, phone: str, phone_hash: str, input_code: str):
    ok = await verify_phone_code(redis, phone=phone, input_code=input_code)
    if not ok:
        return None

    return await __get_reset_token_by_phone(redis, phone_hash=phone_hash)


# 校验重置密码 token 是否有效并消耗掉它。
async def is_reset_password(redis: Redis, token: str):
    try:
        user_id = await verify_and_consume_reset_token(redis=redis, token=token)
        return user_id
    except ResetTokenError as e:
        print(e)
        raise ResetTokenError("Token 非法或已过期")
    except ExpiredSignatureError as e:
        print(e)
    except JWTError as e:
        print(e)


# 生成登录访问令牌。
def token_issuer(
        user_id: str,
        is_admin: bool,
        *,
        login_type: str = "password",
) -> str:
    """
    登录 token 生成器

    Parameters
    ----------
    user_id: str
        用户ID
    is_admin: bool
        用户是否为管理权限用户

    Returns
    -------
    str
        token
    """
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "is_admin": is_admin,
        "type": "access",
        "login_type": login_type,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    return token

# 生成 refresh token 对应的 Redis 键。
def _refresh_key(jti: str) -> str:
    return f"{REFRESH_TOKEN_PREFIX}:{jti}"


# 生成 refresh token。
def _encode_refresh_token(user_id: int, jti: str, *, login_type: str = "password") -> str:
    payload = {
        "user_id": user_id,
        "jti": jti,
        "type": "refresh",
        "login_type": login_type,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


# 解析并校验 refresh token。
def decode_refresh_token(refresh_token: str) -> dict:
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="refresh token 已过期")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的 refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="token 类型错误")
    if not payload.get("jti") or not payload.get("user_id"):
        raise HTTPException(status_code=401, detail="refresh token 载荷缺失")

    return payload


# 把 refresh token 的会话写入 Redis。
async def save_refresh_session(redis: Redis, user_id: int, jti: str) -> None:
    await redis.set(_refresh_key(jti), str(user_id), ex=REFRESH_TOKEN_EXPIRE_SECONDS)


# 从 Redis 中撤销 refresh token 会话。
async def revoke_refresh_session(redis: Redis, jti: str) -> None:
    await redis.delete(_refresh_key(jti))


# 生成一对访问令牌和刷新令牌。
async def issue_token_pair(
        redis: Redis,
        user_id: int,
        is_admin: bool,
        *,
        login_type: str = "password",
) -> dict:
    access_token = token_issuer(
        user_id=user_id,
        is_admin=is_admin,
        login_type=login_type,
    )
    refresh_jti = secrets.token_urlsafe(24)
    refresh_token = _encode_refresh_token(
        user_id=user_id,
        jti=refresh_jti,
        login_type=login_type,
    )
    await save_refresh_session(redis=redis, user_id=user_id, jti=refresh_jti)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        "refresh_expires_in": REFRESH_TOKEN_EXPIRE_SECONDS,
    }


# 将用户对象序列化为接口返回结构。
def serialize_user(user: User, *, login_type: str | None = None) -> dict:
    lang_pref = "private"
    if getattr(user, "language", None) is not None:
        lang_pref = user.language.code
    phone_bound = bool(getattr(user, "encrypted_phone", None) or getattr(user, "phone_hash", None))

    return {
        "id": user.id,
        "username": user.name,
        "is_admin": user.is_admin,
        "lang_pref": lang_pref,
        "portrait": user.portrait,
        "login_type": login_type,
        "phone_bound": phone_bound,
    }


# 构造登录后的完整响应体。
async def build_login_response(
        redis: Redis,
        user: User,
        *,
        login_type: str = "password",
        is_new_user: bool = False,
) -> dict:
    if getattr(user, "language", None) is None:
        await user.fetch_related("language")

    token_pair = await issue_token_pair(
        redis=redis,
        user_id=user.id,
        is_admin=user.is_admin,
        login_type=login_type,
    )

    return {
        **token_pair,
        "user": serialize_user(user, login_type=login_type),
        "is_new_user": is_new_user,
    }


# 使用 refresh token 刷新当前登录会话。
async def refresh_user_session(redis: Redis, refresh_token: str) -> dict:
    payload = decode_refresh_token(refresh_token)
    user_id = int(payload["user_id"])
    jti = payload["jti"]

    stored_user_id = await redis.get(_refresh_key(jti))
    if stored_user_id is None or stored_user_id != str(user_id):
        raise HTTPException(status_code=401, detail="refresh token 已失效")

    user = await User.get_or_none(id=user_id).prefetch_related("language")
    if not user:
        await revoke_refresh_session(redis=redis, jti=jti)
        raise HTTPException(status_code=401, detail="用户不存在")

    await revoke_refresh_session(redis=redis, jti=jti)

    login_type = payload.get("login_type") or "password"
    return await build_login_response(
        redis=redis,
        user=user,
        login_type=login_type,
    )
