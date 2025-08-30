import redis
from fastapi import APIRouter, Depends
from app.core.redis import redis_client, get_redis

redis_test_router = APIRouter()

@redis_test_router.get("/ping-redis")
async def ping_redis(r: redis.Redis = Depends(get_redis)):
    return {"pong": await r.ping()}
