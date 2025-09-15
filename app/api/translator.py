from typing import Tuple
from wsgiref import headers

import httpx
import random
import json
from hashlib import md5

import requests
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


@translator_router.post('/translate', response_model=TransResponse)
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


@translator_router.post('/translate/debug')
async def test_translate(
        query: str,
        from_lang: str = "auto",
        to_lang: str = 'zh',
        admin_user: Tuple[User, dict] = Depends(is_admin_user)
):
    raw = await baidu_translation(query, from_lang, to_lang)
    return TransResponse(translated_text=raw)
