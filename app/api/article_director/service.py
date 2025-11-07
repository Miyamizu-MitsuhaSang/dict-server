import json
from typing import List, Dict

from openai import OpenAI
from redis import Redis

from app.api.article_director.article_schemas import UserArticleRequest
from settings import settings

SYSTEM_PROMPT = """
# 背景
你是一个人工智能助手，名字叫EduChat,是一个由华东师范大学开发的教育领域大语言模型。
# 对话主题:作文指导
## 作文指导主题的要求：
EduChat你需要扮演一位经验丰富的语文老师，现在需要帮助一位学生审阅作文并给出修改建议。请按照以下步骤进行：
整体评价：先对作文的整体质量进行简要评价，指出主要优点和需要改进的方向。
亮点分析：具体指出作文中的亮点（如结构、描写、情感表达等方面的优点）。
具体修改建议：针对作文中的不足，从以下几个方面提出具体修改建议，并给出修改后的示例：
语言表达：是否生动、准确？有无冗余或重复？可以如何优化？
细节描写：是否足够具体？能否加入更多感官描写（视觉、听觉、嗅觉、触觉等）使画面更立体？
情感表达：情感是否自然？能否更深入或升华？
结构布局：段落衔接是否自然？开头结尾是否呼应？ （注意：每个建议点都要结合原文具体句子进行分析，并给出修改后的句子或段落作为示例）
写作技巧提示：提供2-3条实用的写作技巧（如动态描写公式、感官交织法等），帮助学生举一反三。
修改效果总结：简要说明按照建议修改后，作文会有哪些方面的提升（如文学性、情感层次、场景沉浸感等）。
请用亲切、鼓励的语气进行点评，保持专业性同时让学生易于接受。
"""


def chat_ecnu_request(
        session: List[Dict[str, str]],
):
    client = OpenAI(
        api_key=settings.ECNU_TEACH_AI_KEY,
        base_url="https://chat.ecnu.edu.cn/open/api/v1"
    )
    completion = client.chat.completions.create(
        model="educhat-r1",
        messages=session,
        temperature=0.8,  # 保持创造性
        top_p=0.9,  # 保持多样性
    )

    return completion


def set_user_prompt(user_article: UserArticleRequest, article_lang: str):
    if user_article.theme is not None:
        user_prompt = f"以下是我的{article_lang}作文，作文体裁为{user_article.article_type}，标题为{user_article.theme}, 请帮我修改：{user_article.content}"
    else:
        user_prompt = f"以下是我的{article_lang}作文，作文体裁为{user_article.article_type}， 请帮我修改：{user_article.content}"

    return user_prompt


async def get_session(redis_client: Redis, user_id: str) -> List[Dict[str, str]]:
    """从 Redis 读取对话上下文"""
    data = await redis_client.get(f"session:{user_id}")
    if data:
        return json.loads(data)
    else:
        # 如果没有记录，创建带 system prompt 的初始会话
        return [{"role": "system", "content": SYSTEM_PROMPT},]


async def save_session(redis_client: Redis, user_id: str, session: List[Dict[str, str]]):
    """保存对话上下文到 Redis"""
    await redis_client.setex(f"session:{user_id}", 86400, json.dumps(session))


async def reset_session(redis_client: Redis, user_id: str):
    """清空用户上下文"""
    await redis_client.delete(f"session:{user_id}")

async def reply_process(reply: str) -> str:
    """
    对原始回答进行字符串预处理
    :param reply: 大模型的原始回答
    :return:
    """
    reply.replace("**", "")
    reply.replace("---", "")
    return reply
