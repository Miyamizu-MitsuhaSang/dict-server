import redis.asyncio as redis
from typing import AsyncGenerator, Optional

# 全局 Redis 客户端
redis_client: Optional[redis.Redis] = None

# 初始化 Redis（应用启动时调用）
async def init_redis():
    global redis_client
    if redis_client is None:
        redis_client = await redis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True,  # 返回 str 而不是 Bytes
        )
    await redis_client.ping()

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
    assert redis_client is not None, "Redis 未初始化"
    yield redis_client