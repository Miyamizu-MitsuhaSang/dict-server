import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from redis.asyncio import Redis

from app.api.user.service import hash_password, build_login_response
from app.models.base import Language, OAuthIdentity, User
from settings import settings

STATE_TTL_SECONDS = 300
WECHAT_OPEN_PROVIDER = "wechat_open"
WECHAT_MINI_PROVIDER = "wechat_miniapp"
WECHAT_PROVIDER_SET = (WECHAT_OPEN_PROVIDER, WECHAT_MINI_PROVIDER)


def ensure_wechat_settings() -> None:
    if not settings.WECHAT_MINI_APPID or not settings.WECHAT_MINIAPP_SECRET or not settings.WECHAT_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="WECHAT_MINI_APPID/WECHAT_MINIAPP_SECRET/WECHAT_REDIRECT_URI not configured",
        )


def ensure_wechat_mini_settings() -> None:
    if not settings.WECHAT_MINI_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise HTTPException(
            status_code=500,
            detail="WECHAT_MINI_APPID/WECHAT_MINIAPP_SECRET not configured",
        )


async def put_state(redis_client: Redis, state: str) -> None:
    key = f"wechat:oauth:state:{state}"
    await redis_client.set(key, "1", ex=STATE_TTL_SECONDS)


async def pop_state_if_valid(redis_client: Redis, state: str) -> bool:
    key = f"wechat:oauth:state:{state}"
    value = await redis_client.getdel(key)
    return value is not None


def build_authorize_url(state: str) -> str:
    query = urlencode(
        {
            "appid": settings.WECHAT_MINI_APPID,
            "redirect_uri": settings.WECHAT_REDIRECT_URI,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": state,
        }
    )
    return f"https://open.weixin.qq.com/connect/qrconnect?{query}#wechat_redirect"


async def wechat_exchange_code_for_token(code: str) -> Dict[str, Any]:
    url = "https://api.weixin.qq.com/sns/oauth2/access_token"
    params = {
        "appid": settings.WECHAT_MINI_APPID,
        "secret": settings.WECHAT_MINIAPP_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"WeChat token error: {data}")
    if "openid" not in data or "access_token" not in data:
        raise HTTPException(status_code=400, detail=f"Unexpected WeChat response: {data}")
    return data


async def wechat_get_userinfo(access_token: str, openid: str) -> Dict[str, Any]:
    url = "https://api.weixin.qq.com/sns/userinfo"
    params = {"access_token": access_token, "openid": openid, "lang": "zh_CN"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"WeChat userinfo error: {data}")
    return data


async def wechat_mini_exchange_code_for_session(code: str) -> Dict[str, Any]:
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_MINI_APPID,
        "secret": settings.WECHAT_MINIAPP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"WeChat mini session error: {data}")
    if "openid" not in data or "session_key" not in data:
        raise HTTPException(status_code=400, detail=f"Unexpected WeChat mini response: {data}")
    return data


async def _get_default_language() -> Language:
    language, _ = await Language.get_or_create(code="private", defaults={"name": "Private"})
    return language


async def _generate_unique_username() -> str:
    for _ in range(10):
        candidate = f"wx_{secrets.token_hex(4)}"
        exists = await User.filter(name=candidate).exists()
        if not exists:
            return candidate
    raise HTTPException(status_code=500, detail="生成微信用户名失败，请稍后重试")


def _build_placeholder_email(identifier: str) -> str:
    safe_identifier = "".join(ch for ch in identifier if ch.isalnum()).lower()[:64]
    return f"wechat_{safe_identifier}@wx.local"


async def _create_user_for_wechat(
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
) -> User:
    identifier = unionid or openid
    language = await _get_default_language()
    username = await _generate_unique_username()
    email = _build_placeholder_email(identifier)
    password_hash = hash_password(secrets.token_urlsafe(24))

    portrait = "#"
    if profile and isinstance(profile, dict):
        portrait = profile.get("headimgurl") or "#"

    return await User.create(
        name=username,
        email=email,
        pwd_hashed=password_hash,
        portrait=portrait,
        language=language,
    )


async def _sync_identity_profile(identity: OAuthIdentity, profile: Optional[Dict[str, Any]], unionid: Optional[str]) -> None:
    updates: Dict[str, Any] = {}
    if unionid and identity.unionid != unionid:
        updates["unionid"] = unionid
    if profile is not None:
        updates["profile"] = profile

    if updates:
        await OAuthIdentity.filter(id=identity.id).update(**updates)

    portrait = profile.get("headimgurl") if profile else None
    if portrait and identity.user.portrait != portrait:
        await User.filter(id=identity.user_id).update(portrait=portrait)


async def get_or_create_user_by_wechat(
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
) -> tuple[User, bool]:
    identity = await OAuthIdentity.get_or_none(provider=provider, openid=openid).prefetch_related("user")
    if identity:
        await _sync_identity_profile(identity=identity, profile=profile, unionid=unionid)
        await identity.fetch_related("user")
        return identity.user, False

    if unionid:
        identity = await (
            OAuthIdentity.filter(provider__in=WECHAT_PROVIDER_SET, unionid=unionid)
            .prefetch_related("user")
            .first()
        )
        if identity:
            if identity.provider == provider:
                await OAuthIdentity.filter(id=identity.id).update(
                    openid=openid,
                    unionid=unionid,
                    profile=profile,
                )
            else:
                await OAuthIdentity.create(
                    user=identity.user,
                    provider=provider,
                    openid=openid,
                    unionid=unionid,
                    profile=profile,
                )
            portrait = profile.get("headimgurl") if profile else None
            if portrait and identity.user.portrait != portrait:
                await User.filter(id=identity.user_id).update(portrait=portrait)
            await identity.fetch_related("user")
            return identity.user, False

    user = await _create_user_for_wechat(openid=openid, unionid=unionid, profile=profile)
    await OAuthIdentity.create(
        user=user,
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
    )
    return user, True


async def finalize_wechat_login(
        redis: Redis,
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
        login_type: str,
) -> Dict[str, Any]:
    user, is_new_user = await get_or_create_user_by_wechat(
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
    )
    await user.fetch_related("language")
    return await build_login_response(
        redis=redis,
        user=user,
        login_type=login_type,
        is_new_user=is_new_user,
    )
