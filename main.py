from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

import app.utils.audio_init
from app.api.admin.router import admin_router
from app.api.ai_assist.routes import ai_router
from app.api.article_director.routes import article_router
from app.api.make_comments.routes import comment_router
from app.api.pronounciation_test.routes import pron_test_router
from app.api.redis_test import redis_test_router
from app.api.search_dict.routes import dict_search
from app.api.translator import translator_router
from app.api.user.routes import users_router
from app.api.util_api.routes import ulit_router
from app.api.word_comment.routes import word_comment_router
from app.core.redis import init_redis, close_redis
from app.utils.phone_encrypt import PhoneEncrypt
from settings import ONLINE_SETTINGS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    app.state.redis = await init_redis()
    # phone_encrypt
    app.state.phone_encrypto = PhoneEncrypt.from_env()  # 接口中通过 Request 访问
    try:
        yield
    finally:
        await close_redis()


app = FastAPI(lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_tortoise(
    app=app,
    config=ONLINE_SETTINGS,
)

app.include_router(users_router, tags=["User API"], prefix="/users")
app.include_router(admin_router, tags=["Administrator API"], prefix="/admin")
app.include_router(dict_search, tags=["Dictionary Search API"])

app.include_router(redis_test_router, tags=["Redis Test-Only API"])

app.include_router(translator_router, tags=["Translation API"])

app.include_router(ai_router, tags=["AI Assist API"], prefix="/ai_assist")

app.include_router(comment_router, tags=["Comment API"])

app.include_router(word_comment_router, tags=["Word Comment API"], prefix="/comment/word")

app.include_router(pron_test_router, tags=["Pron Test API"], prefix="/test/pron")

app.include_router(article_router, tags=["Article API"])

app.include_router(ulit_router, tags=["Util Functions API"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
