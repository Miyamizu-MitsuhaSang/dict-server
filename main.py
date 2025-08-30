from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from tortoise.contrib.fastapi import register_tortoise

from app.api.redis_test import redis_test_router
from app.utils import redis_client
from settings import TORTOISE_ORM
from app.api.users import users_router
from app.api.admin.router import admin_router
from app.api.search import dict_search
from app.core.redis import init_redis, close_redis
import app.models.signals


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    await init_redis()
    try:
        yield
    finally:
        await close_redis()


app = FastAPI(lifespan=lifespan)

import debug.httpdebugger

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_tortoise(
    app=app,
    config=TORTOISE_ORM,
)

app.include_router(users_router, tags=["User API"], prefix="/users")
app.include_router(admin_router, tags=["Administrator API"], prefix="/admin")
app.include_router(dict_search, tags=["Dictionary Search API"])

app.include_router(redis_test_router, tags=["Redis Test-Only API"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
