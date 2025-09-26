import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Tuple

from dotenv import load_dotenv
from fastapi import HTTPException
from jose import jwt, ExpiredSignatureError, JWTError
from redis.asyncio import Redis

load_dotenv()

RESET_SECRET_KEY = os.getenv("RESET_SECRET_KEY")
ALGORITHM = 'HS256'


class ResetTokenError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=400, detail=message)


def create_reset_token(user_id: int, expire_seconds: int = 300) -> Tuple[str, str]:
    """生成 reset_token (JWT) 和 jti"""
    jti = uuid.uuid4().hex
    payload = {
        'sub': str(user_id),
        'purpose': 'reset_pw',
        'exp': datetime.now(timezone.utc) + timedelta(hours=2),
        'jti': jti,
    }

    token = jwt.encode(payload, RESET_SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


async def save_reset_jti(redis: Redis, user_id: int, jti: str, expire_seconds: int = 300):
    """把 jti 存到 Redis，设置过期时间"""
    await redis.setex(f"reset:{user_id}", expire_seconds, jti)


async def verify_and_consume_reset_token(redis: Redis, token: str) -> int | None:
    """
    验证 reset_token：
    - 校验签名、过期时间、用途
    - 校验 Redis 里 jti 是否匹配
    - 如果通过，删除 Redis 记录，确保一次性
    - 返回 user_id，否则 None
    """
    try:
        # 1. 解码并验证签名
        payload = jwt.decode(token, RESET_SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})

        # 2. 校验用途
        if payload.get("purpose") != "reset_pw":
            return None

        user_id = int(payload.get("sub"))
        jti = payload.get("jti")

        stored = await redis.getdel(f"reset:{user_id}")
        if stored is None or stored != jti:
            raise ResetTokenError("Token 非法或已过期")

        return user_id

    except ExpiredSignatureError as e:
        raise ExpiredSignatureError(e)
    except JWTError as e:
        raise JWTError(e)
