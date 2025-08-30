from fastapi import APIRouter
from app.core.redis import redis_client

redis_test_router = APIRouter()

@redis_test_router.get("/ping-redis")
async def ping_redis():
    return {"pong": await redis_client.ping()}
