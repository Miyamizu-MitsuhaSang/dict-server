from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from app.core.redis import redis_client
from settings import settings

STATE_TTL_SECONDS = 300
WECHAT_APPID = settings.WECHAT_APPID
WECHAT_SECRET = settings.WECHAT_SECRET


async def put_state(state: str) -> None:
    key = f"wechat:oauth:state:{state}"
    # SET key value EX ttl
    await redis_client.set(key, "1", ex=STATE_TTL_SECONDS)


async def pop_state_if_valid(state: str) -> bool:
    key = f"wechat:oauth:state:{state}"

    # 原子性：GET + DEL
    value = await redis_client.getdel(key)
    return value is not None

async def wechat_exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    文档：sns/oauth2/access_token
    返回：access_token, openid, unionid(可能), refresh_token 等
    """
    url = "https://api.weixin.qq.com/sns/oauth2/access_token"
    params = {
        "appid": WECHAT_APPID,
        "secret": WECHAT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        data = r.json()

    # 微信错误返回通常包含 errcode/errmsg
    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"WeChat token error: {data}")
    if "openid" not in data or "access_token" not in data:
        raise HTTPException(status_code=400, detail=f"Unexpected WeChat response: {data}")
    return data

async def wechat_get_userinfo(access_token: str, openid: str) -> Dict[str, Any]:
    """
    scope=snsapi_login 才能拿到用户信息
    """
    url = "https://api.weixin.qq.com/sns/userinfo"
    params = {"access_token": access_token, "openid": openid, "lang": "zh_CN"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        data = r.json()
    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"WeChat userinfo error: {data}")
    return data

async def get_or_create_user_by_wechat(openid: str, unionid: Optional[str], profile: Optional[Dict[str, Any]]) -> str:
    """
    返回站内 user_id。
    你需要接入数据库：用 openid/unionid 查找用户，不存在则创建。
    profile 里可能有 nickname/headimgurl 等。
    """
    # 示例：直接用 openid 当 user_id（真实项目不要这样）
    return f"wechat:{openid}"
