import random
import re

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


async def varify_code(redis: Redis, phone: str, input_code: str):
    stored = await redis.get(f"sms:{phone}")
    return stored is not None and stored.decode() == input_code


# EMAIL
async def save_email_code(redis: Redis, email: str, code: str, expire: int = 300):
    await redis.setex(f"email:{email}", expire, code)


async def send_email_code(redis: Redis, email: str, code: str):
    await save_email_code(redis, email, code)

    subject = "Lexiverse 用户邮箱验证码"
    content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height:1.6;">
            <h2 style="color:#4CAF50;">Lexiverse 验证码</h2>
            <p>您好，</p>
            <p>您正在进行 <b>密码重置</b> 操作。</p>
            <p>
              您的验证码是：
              <span style="font-size: 24px; font-weight: bold; color: #d9534f;">{code}</span>
            </p>
            <p>有效期 5 分钟，请勿泄露给他人。</p>
            <hr>
            <p style="font-size: 12px; color: #999;">
              如果这不是您本人的操作，请忽略此邮件。
            </p>
          </body>
        </html>
        """

    send_email(email, subject, content)


async def __verify_email_code(redis: Redis, email: str, input_code: str) -> bool:
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
    ok = await __verify_email_code(redis, email, input_code)
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
