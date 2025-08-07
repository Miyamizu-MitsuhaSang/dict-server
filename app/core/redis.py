import redis.asyncio as redis
from typing import AsyncGenerator

# 全局 Redis 客户端
redis_client: redis.Redis

# 初始化 Redis（应用启动时调用）
async def init_redis_pool():
    global redis_client
    redis_client = await redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True,  # 返回 str 而不是 Bytes
    )

# FastAPI 依赖注入用的获取方法
async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    yield redis_client