import json
from typing import List, Dict

MAX_HISTORY = 6  # 每个用户保留最近3轮 (user+assistant)
CHAT_TTL = 7200


async def get_chat_history(redis, user_id: str, word: str) -> List[Dict]:
    """
        从 Redis 获取历史消息
        """
    key = f"chat:{user_id}:{word}"
    data = await redis.lrange(key, 0, -1)
    messages = [json.loads(d) for d in data]
    return messages[-MAX_HISTORY:]  # 仅返回最近N条


async def save_message(redis, user_id: str, word: str, role: str, content: str):
    """
    保存单条消息到 Redis
    """
    key = f"chat:{user_id}:{word}"
    msg = msg = json.dumps({"role": role, "content": content})
    await redis.rpush(key, msg)
    # 限制总长度
    await redis.ltrim(key, -MAX_HISTORY, -1)
    await redis.expire(key, CHAT_TTL)


async def clear_chat_history(redis, user_id: str, word: str):
    """
        删除某个用户针对某个词汇的全部聊天记录
        """
    key = f"chat:{user_id}:{word}"
    await redis.delete(key)
