#TODO 更新接口文档
from fastapi import APIRouter
from starlette.requests import Request

ulit_router = APIRouter()

@ulit_router.get("/search_time", tags=["search times"])
async def get_search_time(request: Request):
    redis = request.app.state.redis

    key = f"search_time"

    count = await redis.get(key)
    if not count:
        await redis.set(key, value=0)
        count = 0
    print(count, type(count))
    return {
        "count": int(count),
    }
