import json
from typing import AsyncGenerator, Optional

import redis.asyncio as redis

# 全局 Redis 客户端
redis_client: Optional[redis.Redis] = None

# 初始化 Redis（应用启动时调用）
async def init_redis():
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host="127.0.0.1",
            port=6379,
            decode_responses=True,  # 返回 str 而不是 Bytes
        )
    await redis_client.ping()

    return redis_client

async def close_redis():
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
        except Exception:
            pass
        redis_client = None

# FastAPI 依赖注入用的获取方法
async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    global redis_client
    if redis_client is None:
        await init_redis()   # 懒加载，避免 NoneType
    yield redis_client


async def redis_get_json(key: str):
    client = redis_client
    if client is None:
        return None

    value = await client.get(key)
    if not value:
        return None

    return json.loads(value)


async def redis_set_json(key: str, value, ex: int = 300):
    client = redis_client
    if client is None:
        return

    await client.set(key, json.dumps(value, ensure_ascii=False), ex=ex)


async def redis_delete(key: str):
    client = redis_client
    if client is None:
        return

    await client.delete(key)