import json
import random
from typing import Tuple, Dict

import httpx
import redis.asyncio as redis_asyncio
from fastapi import APIRouter, Depends, HTTPException

from app.models import User
from app.schemas.trans_schemas import TransResponse, TransRequest
from app.utils.security import is_admin_user, get_current_user
from scripts.md5 import make_md5
from settings import settings

translator_router = APIRouter()

# For list of language codes, please refer to `https://api.fanyi.baidu.com/doc/21`
from_lang = 'en'
to_lang = 'zh'


# endpoint = 'https://api.fanyi.baidu.com'
# path = '/api/trans/vip/translate'
# url = endpoint + path
#
# query = 'Hello World! This is 1st paragraph.\nThis is 2nd paragraph.'
#
# salt = random.randint(32768, 65536)
# sign = make_md5(appid + query + str(salt) + appkey)
#
# headers = {'Content-Type': 'application/x-www-form-urlencoded'}
# payload = {'appid': appid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}
#
#
# # Send request
# r = requests.post(url, params=payload, headers=headers)
# result = r.json()
#
# # Show response
# print(json.dumps(result, indent=4, ensure_ascii=False))

async def baidu_translation(query: str, from_lang: str, to_lang: str):
    url = "http://api.fanyi.baidu.com/api/trans/vip/translate"

    appid = settings.BAIDU_APPID
    appkey = settings.BAIDU_APPKEY

    salt = str(random.randint(32768, 65536))
    sign = make_md5(appid + query + salt + appkey)

    payload = {
        "q": query,
        "from": from_lang,
        "to": to_lang,
        "appid": appid,
        "salt": salt,
        "sign": sign,
    }

    # print(payload)
    #
    # request = httpx.Request(
    #     "POST",
    #     url,
    #     data=payload,
    #     headers={"Content-Type": "application/x-www-form-urlencoded"}
    # )
    # print("完整请求内容:")
    # print("URL:", request.url)
    # print("Headers:", request.headers)
    # print("Body:", request.content.decode("utf-8"))

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            url,
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=response.text)

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if "trans_result" not in data:
        raise HTTPException(status_code=500, detail=data.get("error_msg", "Unknown error"))

    return "\n".join([item["dst"] for item in data["trans_result"]])


redis = redis_asyncio.from_url("redis://localhost", encoding="utf-8", decode_responses=True)


async def rate_limiter(
        user: Tuple[User, Dict] = Depends(get_current_user),
        limit: int = 2,
        window: int = 1
):
    """
        限制每个 IP 在 window 秒内最多 limit 次请求
    """
    client_ip = user[0].id
    key = f"rate limit {client_ip}"

    count = await redis.get(key)

    if count is None:
        # 第一次请求 → 设置计数和过期时间
        await redis.set(key, 1, ex=window)
    elif int(count) < limit:
        await redis.incr(key)
    else:
        raise HTTPException(status_code=429, detail=f"Too many requests")


@translator_router.post('/translate', response_model=TransResponse, dependencies=[Depends(rate_limiter)])
async def translate(
        translate_request: TransRequest,
        user=Depends(get_current_user)
):
    text = await baidu_translation(
        query=translate_request.query,
        from_lang=translate_request.from_lang,
        to_lang=translate_request.to_lang,
    )
    return TransResponse(translated_text=text)


@translator_router.post('/translate/debug', dependencies=[Depends(rate_limiter)])
async def test_translate(
        query: str,
        from_lang: str = "auto",
        to_lang: str = 'zh',
        admin_user: Tuple[User, dict] = Depends(is_admin_user)
):
    """
    尝试使用多次翻译请求接口，要求在前端监听输入在约300ms左右内保持不输入再传入，
    同时后端检查避免多次恶意访问
    :param query: 待翻译文本
    :param from_lang: 源语言，默认auto，百度API自动检测
    :param to_lang: 目标语言，不允许auto
    :param admin_user: 测试接口，仅管理员权限可用
    :return:
    """
    raw = await baidu_translation(query, from_lang, to_lang)
    return TransResponse(translated_text=raw)
