"""
每次调用 article-director/article 接口时都要同时调用reset以清空 redis 中的上下文
"""
from typing import Literal, Dict, Tuple

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.api.article_director import service
from app.api.article_director.article_schemas import UserArticleRequest, UserQuery
from app.models import User
from app.utils.security import get_current_user

article_router = APIRouter()


@article_router.post("/article-director/article")
async def article_director(
        request: Request,
        upload_article: UserArticleRequest,
        lang: Literal["en-US", "fr-FR", "ja-JP"] = "fr-FR",
        user: Tuple[User, Dict] = Depends(get_current_user)
):
    """
    文本形式接口，即直接从文本框中获取
    每次调用本接口的同时都要同时调用reset接口
    :param upload_article:
    :param lang:
    :return:
    """
    redis = request.app.state.redis

    article_lang = "法语" if lang == "fr-FR" else "日语"

    user_id = user[0].id
    article = upload_article.title_content

    # 读取历史对话
    session = await service.get_session(redis_client=redis, user_id=user_id)

    # 追加用户输入
    user_prompt = service.set_user_prompt(upload_article, article_lang=article_lang)
    session.append({"role": "user", "content": user_prompt})

    # 调用 EduChat 模型
    completion = service.chat_ecnu_request(session)

    # 取出回答内容
    assistant_reply = completion.choices[0].message.content

    # 保存模型回复
    session.append({"role": "assistant", "content": assistant_reply})

    # 存入 Redis
    await service.save_session(redis, user_id, session)

    return {
        "reply": assistant_reply,
        "tokens": completion.usage.total_tokens,
        "conversation_length": len(session),
    }


@article_router.post("/article-director/question", description="用户进一步询问")
async def further_question(
        request: Request,
        user_prompt: UserQuery,
        user: Tuple[User, Dict] = Depends(get_current_user)
):
    redis = request.app.state.redis

    user_id = user[0].id

    # 读取历史对话
    session = await service.get_session(redis_client=redis, user_id=user_id)

    # 追加用户输入
    session.append({"role": "user", "content": user_prompt.query})

    # 调用 EduChat 模型
    completion = service.chat_ecnu_request(session)

    # 取出回答内容
    assistant_reply = completion.choices[0].message.content

    # 保存模型回复
    session.append({"role": "assistant", "content": assistant_reply})

    # 存入 Redis
    await service.save_session(redis, user_id, session)

    return {
        "reply": assistant_reply,
        "tokens": completion.usage.total_tokens,
        "conversation_length": len(session),
    }

@article_router.post("/article-director/reset", description="重置上下文")
async def reset_conversation(request: Request, user: Tuple[User, Dict] = Depends(get_current_user)):
    user_id = user[0].id
    redis = request.app.state.redis
    await service.reset_session(redis, user_id)
    return {"message": f"已重置用户 {user_id} 的作文对话记录"}
