from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn
from tortoise.contrib.fastapi import register_tortoise

from settings import TORTOISE_ORM
from app.api.users import users_router
from app.api.admin.router import admin_router
from app.core.redis import init_redis_pool
import app.models.signals


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis_pool()
    yield
    # 可以加 await redis_client.close() 清理资源


app = FastAPI(lifespan=lifespan)

register_tortoise(
    app=app,
    config=TORTOISE_ORM,
)

app.include_router(users_router, tags=["User API"], prefix="/users")
app.include_router(admin_router, tags=["Administrator API"], prefix="/admin")

if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8000, reload=True)
