from redis import Redis

from app.api.ai_assist.utils.redis_memory import clear_chat_history

CHAT_TTL = 7200


async def get_and_set_last_key(redis: Redis, word: str, user_id: str):
    last_key = f"last_word:{user_id}"
    last_word = await redis.get(last_key)

    # 如果上一次查的词和这次不同，就清空旧词的记录
    if last_word and last_word.decode() != word:
        await clear_chat_history(redis, user_id, last_word.decode())

    # 更新当前词
    await redis.set(last_key, word, ex=CHAT_TTL)
