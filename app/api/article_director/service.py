import json
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any

from openai import OpenAI
from redis import Redis
from starlette.requests import Request
from dateutil.relativedelta import relativedelta

from app.api.article_director.article_schemas import UserArticleRequest
from app.models import User
from app.models.article_director import ArticleDirectorCallLog
from settings import settings

EDUCHAT_BASE_URL = "https://chat.ecnu.edu.cn/open/api/v1"
EDUCHAT_MODEL = "educhat-r1"
EDUCHAT_TEMPERATURE = 0.8
EDUCHAT_TOP_P = 0.9
ARTICLE_DIRECTOR_RETENTION_MONTHS = 6
ARTICLE_DIRECTOR_POLICY_VERSION = "article-director-log-v1"
logger = logging.getLogger(__name__)

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
        base_url=EDUCHAT_BASE_URL
    )
    completion = client.chat.completions.create(
        model=EDUCHAT_MODEL,
        messages=session,
        temperature=EDUCHAT_TEMPERATURE,  # 保持创造性
        top_p=EDUCHAT_TOP_P,  # 保持多样性
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


def text_sha256(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return None


def _safe_str(value: Any, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    text = str(value)
    if max_length is not None and len(text) > max_length:
        return text[:max_length]
    return text


def _usage_value(usage: Any, field_name: str) -> int | None:
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage.get(field_name)
    return getattr(usage, field_name, None)


async def record_article_director_call(
        *,
        request: Request,
        request_id: str,
        user: User,
        token_payload: Dict[str, Any],
        action: str,
        input_text: str,
        status: str,
        lang: str | None = None,
        article_lang: str | None = None,
        article_type: str | None = None,
        theme: str | None = None,
        output_text: str | None = None,
        completion: Any = None,
        latency_ms: int | None = None,
        message_count: int = 0,
        conversation_length_before: int = 0,
        conversation_length_after: int | None = None,
        error: Exception | None = None,
) -> None:
    usage = getattr(completion, "usage", None)
    await ArticleDirectorCallLog.create(
        request_id=request_id,
        user=user,
        login_type=token_payload.get("login_type"),
        endpoint=str(request.url.path),
        method=request.method,
        client_ip=_client_ip(request),
        user_agent=_safe_str(request.headers.get("user-agent"), 512),
        action=action,
        lang=lang,
        article_lang=article_lang,
        article_type=_safe_str(article_type, 60),
        theme=_safe_str(theme, 255),
        input_text=input_text,
        input_hash=text_sha256(input_text),
        input_length=len(input_text or ""),
        output_text=output_text,
        output_hash=text_sha256(output_text),
        output_length=len(output_text) if output_text is not None else None,
        provider="ECNU EduChat",
        model=EDUCHAT_MODEL,
        base_url=EDUCHAT_BASE_URL,
        temperature=EDUCHAT_TEMPERATURE,
        top_p=EDUCHAT_TOP_P,
        system_prompt_hash=text_sha256(SYSTEM_PROMPT),
        message_count=message_count,
        conversation_length_before=conversation_length_before,
        conversation_length_after=conversation_length_after,
        upstream_request_id=_safe_str(getattr(completion, "id", None), 120),
        prompt_tokens=_usage_value(usage, "prompt_tokens"),
        completion_tokens=_usage_value(usage, "completion_tokens"),
        total_tokens=_usage_value(usage, "total_tokens"),
        latency_ms=latency_ms,
        status=status,
        error_code=_safe_str(type(error).__name__ if error else None, 120),
        error_message=_safe_str(error, 2000),
        risk_flags=[],
        blocked=False,
        policy_version=ARTICLE_DIRECTOR_POLICY_VERSION,
        retention_months=ARTICLE_DIRECTOR_RETENTION_MONTHS,
        expires_at=datetime.now() + relativedelta(months=ARTICLE_DIRECTOR_RETENTION_MONTHS),
    )


async def safe_record_article_director_call(**kwargs: Any) -> None:
    try:
        await record_article_director_call(**kwargs)
    except Exception:
        logger.exception("failed to record article director call log")

async def reply_process(reply: str) -> str:
    """
    对原始回答进行字符串预处理
    :param reply: 大模型的原始回答
    :return:
    """
    reply.replace("**", "")
    reply.replace("---", "")
    return reply
