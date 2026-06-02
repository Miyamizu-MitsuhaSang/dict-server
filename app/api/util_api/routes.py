from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request

ulit_router = APIRouter()


class AboutUsResponse(BaseModel):
    app_name: str
    version: str
    description: str
    website: str
    team: str


ABOUT_US_PAYLOAD = AboutUsResponse(
    app_name="Lexiverse",
    version="2.1",
    description="面向小语种学习者的词典与学习平台，提供法语/日语查词、文化阅读、AI 辅助、翻译与发音测评能力。",
    website="https://lexiverse.com.cn",
    team="Lexiverse 团队",
)


@ulit_router.get("/about-us", response_model=AboutUsResponse, tags=["public info"])
async def get_about_us():
    return ABOUT_US_PAYLOAD

@ulit_router.get("/search_time", tags=["search times"])
async def get_search_time(request: Request):
    redis = request.app.state.redis

    key = f"search_time"

    count = await redis.get(key)
    if not count:
        await redis.set(key, value=0)
        count = 0
    return {
        "count": int(count),
    }

@ulit_router.get("/search/reset", tags=["search times reset"])
async def reset_search_time(request: Request):
    redis = request.app.state.redis
    key = f"search_time"

    count = await redis.set(key, 0)
    return {
        "message": "search times reset successfully",
    }
