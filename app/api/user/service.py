import random
import re
from typing import Literal

import bcrypt
from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError
from redis.asyncio import Redis

from app.core.email_utils import send_email
from app.core.reset_utils import create_reset_token, save_reset_jti, verify_and_consume_reset_token, ResetTokenError
from app.models.base import ReservedWords, User


# 登陆校验
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


async def validate_email_exists(email: str):
    user = await User.get_or_none(email=email)
    if user:
        raise HTTPException(status_code=400, detail="邮箱已经被使用，请更换其他邮箱后重试")


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


# 生成随机验证码
def generate_code(length=6):
    return "".join([str(random.randint(0, 9)) for _ in range(length)])


# PHONE MESSAGE
async def save_code_redis(redis: Redis, phone: str, code: str, expire: int = 300):
    await redis.setex(f"sms:{phone}", expire, code)


async def varify_phone_code(redis: Redis, phone: str, input_code: str):
    stored = await redis.get(f"sms:{phone}")
    return stored is not None and stored.decode() == input_code


# EMAIL
async def save_email_code(redis: Redis, email: str, code: str, expire: int = 300):
    await redis.setex(f"email:{email}", expire, code)


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


async def verify_email_code(redis: Redis, email: str, input_code: str) -> bool:
    stored = await redis.getdel(f"email:{email}")
    if stored is None or stored != input_code:
        return False
    return True


async def __get_reset_token(redis: Redis, email: str):
    user = await User.get_or_none(email=email)
    if user is None:
        return None

    reset_token, jti = create_reset_token(user_id=user.id, expire_seconds=300)

    await save_reset_jti(redis, user.id, jti=jti, expire_seconds=300)

    return reset_token


async def verify_and_get_reset_token(redis: Redis, email: str, input_code: str):
    ok = await verify_email_code(redis, email, input_code)
    if not ok:
        return None

    return await __get_reset_token(redis, email)


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
