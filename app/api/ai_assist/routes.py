import os
from typing import Dict, Tuple

import httpx
from fastapi import APIRouter, HTTPException, Depends
from starlette.requests import Request

from app.api.ai_assist import service
from app.api.ai_assist.ai_schemas import AIAnswerResponse, AIAnswerOut, AIQuestionRequest
from app.api.ai_assist.utils.redis_memory import get_chat_history, save_message, clear_chat_history
from app.models import User
from app.utils.security import get_current_user

ai_router = APIRouter()

ZJU_AI_URL = 'https://chat.zju.edu.cn/api/ai/v1/chat/completions'
AI_API_KEY = os.getenv("AI_ASSIST_KEY")
MAX_USAGE_PER = 100

CHAT_TTL = 7200


@ai_router.post("/word/exp", deprecated=False)
async def dict_exp(
        request: Request,
        Q: AIQuestionRequest,
        user: Tuple[User, Dict] = Depends(get_current_user)
):
    """
    该接口仅用于查词页面且为具有MCP功能的
    :param request:
    :param Q:
    :param user:
    :return:
    """
    if user[0].token_usage > MAX_USAGE_PER and not user[0].is_admin:
        raise HTTPException(status_code=400, detail="本月API使用量已超")

    redis = request.app.state.redis

    user_id = str(user[0].id)
    word = Q.word
    question = Q.question

    await service.get_and_set_last_key(redis, word=word, user_id=user_id)

    history = await get_chat_history(redis, user_id, word)

    prompt = (
        f"用户正在学习词语「{word}」。"
        f"请回答与该词相关的问题：{question}\n"
    )

    messages = [
        {"role": "system", "content": "你是一位语言词典助手，回答要简洁、自然，适合初学者理解。只回答与词汇有关的问题。"},
    ]
    messages.extend(history)
    messages.append(
        {"role": "user", "content": prompt}
    )

    payload = {
        "model": "deepseek-r1-671b",
        "messages": messages,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(ZJU_AI_URL, json=payload, headers=headers)

            # 如果状态码不是200，抛异常
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            # 用 Pydantic 模型验证和解析返回结果
            ai_resp = AIAnswerResponse(**resp.json())

            answer = ai_resp.get_answer()

            await save_message(redis, user_id, word, "user", question)
            await save_message(redis, user_id, word, "assistant", answer)

            return AIAnswerOut(
                word=word,
                answer=ai_resp.get_answer(),
                model=ai_resp.model,
                tokens_used=ai_resp.usage.total_tokens if ai_resp.usage else None
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI调用失败: {str(e)}")


@ai_router.post("/univer")
async def universal_main():
    pass


@ai_router.post("/clear")
async def clear_history(word: str, request: Request, user: Tuple[User, Dict] = Depends(get_current_user)):
    redis = request.app.state.redis
    user_id = str(user[0].id)
    await clear_chat_history(redis, user_id, word)
    return {"msg": f"已清除 {word} 的聊天记录"}
