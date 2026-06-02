import json
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from redis.asyncio import Redis

from app.api.user import service as user_service
from app.models.base import Language, OAuthIdentity, User
from settings import settings

STATE_TTL_SECONDS = 300
BIND_TICKET_TTL_SECONDS = 600

WECHAT_OPEN_PROVIDER = "wechat_open"
WECHAT_MINI_PROVIDER = "wechat_miniapp"
WECHAT_PROVIDER_SET = (WECHAT_OPEN_PROVIDER, WECHAT_MINI_PROVIDER)


def ensure_wechat_settings() -> None:
    if not settings.WECHAT_OPEN_APPID or not settings.WECHAT_OPEN_SECRET or not settings.WECHAT_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="WECHAT_OPEN_APPID/WECHAT_OPEN_SECRET/WECHAT_REDIRECT_URI not configured",
        )


def ensure_wechat_mini_settings() -> None:
    if not settings.WECHAT_MINI_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise HTTPException(
            status_code=500,
            detail="WECHAT_MINI_APPID/WECHAT_MINIAPP_SECRET not configured",
        )


def build_authorize_url(state: str) -> str:
    query = urlencode(
        {
            "appid": settings.WECHAT_OPEN_APPID,
            "redirect_uri": settings.WECHAT_REDIRECT_URI,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": state,
        }
    )
    return f"https://open.weixin.qq.com/connect/qrconnect?{query}#wechat_redirect"


async def save_state(redis_client: Redis, state: str, payload: Dict[str, Any]) -> None:
    await redis_client.set(
        f"wechat:oauth:state:{state}",
        json.dumps(payload, ensure_ascii=False),
        ex=STATE_TTL_SECONDS,
    )


async def consume_state(redis_client: Redis, state: str) -> Optional[Dict[str, Any]]:
    raw = await redis_client.getdel(f"wechat:oauth:state:{state}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def save_bind_ticket(
        redis_client: Redis,
        *,
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
        login_type: str,
) -> str:
    bind_ticket = secrets.token_urlsafe(24)
    payload = {
        "provider": provider,
        "openid": openid,
        "unionid": unionid,
        "profile": profile,
        "login_type": login_type,
    }
    await redis_client.set(
        f"wechat:bind:ticket:{bind_ticket}",
        json.dumps(payload, ensure_ascii=False),
        ex=BIND_TICKET_TTL_SECONDS,
    )
    return bind_ticket


async def load_bind_ticket(redis_client: Redis, bind_ticket: str) -> Dict[str, Any]:
    raw = await redis_client.get(f"wechat:bind:ticket:{bind_ticket}")
    if not raw:
        raise HTTPException(status_code=400, detail="bind_ticket 无效或已过期")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="bind_ticket 格式错误")

    required = ("provider", "openid", "login_type")
    if any(not payload.get(key) for key in required):
        raise HTTPException(status_code=400, detail="bind_ticket 数据不完整")
    return payload


async def revoke_bind_ticket(redis_client: Redis, bind_ticket: str) -> None:
    await redis_client.delete(f"wechat:bind:ticket:{bind_ticket}")


async def wechat_exchange_code_for_token(code: str) -> Dict[str, Any]:
    url = "https://api.weixin.qq.com/sns/oauth2/access_token"
    params = {
        "appid": settings.WECHAT_OPEN_APPID,
        "secret": settings.WECHAT_OPEN_SECRET,
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


async def find_bound_user_by_wechat(
        *,
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
) -> Optional[User]:
    identity = await OAuthIdentity.get_or_none(provider=provider, openid=openid).prefetch_related("user")
    if identity:
        await _sync_identity_profile(identity=identity, profile=profile, unionid=unionid)
        await identity.fetch_related("user")
        return identity.user

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
            return identity.user

    return None


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


async def create_user_for_wechat_phone(
        *,
        phone: str,
        phone_hash: str,
        encrypted_phone: str,
        identifier: str,
        profile: Optional[Dict[str, Any]],
) -> User:
    language = await _get_default_language()
    username = await _generate_unique_username()
    password_hash = user_service.hash_password(secrets.token_urlsafe(24))
    portrait = profile.get("headimgurl") if profile else "#"
    if not portrait:
        portrait = "#"

    return await User.create(
        name=username,
        email=_build_placeholder_email(identifier),
        pwd_hashed=password_hash,
        portrait=portrait,
        encrypted_phone=encrypted_phone,
        phone_hash=phone_hash,
        language=language,
    )


async def build_unbound_response(
        redis: Redis,
        *,
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
        login_type: str,
) -> dict:
    bind_ticket = await save_bind_ticket(
        redis,
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
        login_type=login_type,
    )
    return {
        "status": "need_phone",
        "bind_ticket": bind_ticket,
        "login_type": login_type,
        "message": "该微信尚未绑定站内账号，请先完成手机号短信验证，系统将自动匹配或创建账号",
        "wechat_profile": profile,
    }


async def resolve_wechat_login(
        redis: Redis,
        *,
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
        login_type: str,
) -> dict:
    user = await find_bound_user_by_wechat(
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
    )
    if user:
        await user.fetch_related("language")
        return await user_service.build_login_response(
            redis=redis,
            user=user,
            login_type=login_type,
            is_new_user=False,
        )

    return await build_unbound_response(
        redis,
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
        login_type=login_type,
    )


async def resolve_or_bind_wechat_login(
        redis: Redis,
        *,
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
        login_type: str,
        current_user: User | None = None,
) -> dict:
    bound_user = await find_bound_user_by_wechat(
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
    )
    if bound_user:
        await bound_user.fetch_related("language")
        if current_user and bound_user.id != current_user.id:
            raise HTTPException(status_code=409, detail="该微信账号已绑定其他用户")
        return await user_service.build_login_response(
            redis=redis,
            user=bound_user,
            login_type=login_type,
            is_new_user=False,
        )

    if current_user:
        await bind_wechat_identity_to_user(
            user=current_user,
            provider=provider,
            openid=openid,
            unionid=unionid,
            profile=profile,
        )
        await current_user.fetch_related("language")
        return await user_service.build_login_response(
            redis=redis,
            user=current_user,
            login_type=login_type,
            is_new_user=False,
        )

    return await build_unbound_response(
        redis,
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
        login_type=login_type,
    )


async def bind_wechat_identity_to_user(
        *,
        user: User,
        provider: str,
        openid: str,
        unionid: Optional[str],
        profile: Optional[Dict[str, Any]],
) -> None:
    same_provider_identity = await OAuthIdentity.get_or_none(provider=provider, openid=openid).prefetch_related("user")
    if same_provider_identity:
        if same_provider_identity.user_id != user.id:
            raise HTTPException(status_code=409, detail="该微信账号已绑定其他用户")
        await _sync_identity_profile(same_provider_identity, profile=profile, unionid=unionid)
        return

    if unionid:
        same_union_identity = await (
            OAuthIdentity.filter(provider__in=WECHAT_PROVIDER_SET, unionid=unionid)
            .prefetch_related("user")
            .first()
        )
        if same_union_identity:
            if same_union_identity.user_id != user.id:
                raise HTTPException(status_code=409, detail="该微信账号已绑定其他用户")

            existing_current_provider = await OAuthIdentity.get_or_none(
                user_id=user.id,
                provider=provider,
            )
            if existing_current_provider and existing_current_provider.id != same_union_identity.id:
                raise HTTPException(status_code=409, detail="当前账号已绑定其他微信身份")

            if same_union_identity.provider == provider:
                await OAuthIdentity.filter(id=same_union_identity.id).update(
                    openid=openid,
                    unionid=unionid,
                    profile=profile,
                )
            else:
                await OAuthIdentity.create(
                    user=user,
                    provider=provider,
                    openid=openid,
                    unionid=unionid,
                    profile=profile,
                )

            portrait = profile.get("headimgurl") if profile else None
            if portrait and user.portrait != portrait:
                await User.filter(id=user.id).update(portrait=portrait)
            return

    existing_current_provider = await OAuthIdentity.get_or_none(user_id=user.id, provider=provider)
    if existing_current_provider:
        raise HTTPException(status_code=409, detail="当前账号已绑定其他微信身份")

    await OAuthIdentity.create(
        user=user,
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
    )

    portrait = profile.get("headimgurl") if profile else None
    if portrait and user.portrait != portrait:
        await User.filter(id=user.id).update(portrait=portrait)


async def bind_existing_account_with_ticket(
        redis: Redis,
        *,
        bind_ticket: str,
        username: str,
        password: str,
) -> dict:
    bind_payload = await load_bind_ticket(redis, bind_ticket)
    user = await User.get_or_none(name=username).prefetch_related("language")
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not await user_service.verify_password(password, user.pwd_hashed):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    await bind_wechat_identity_to_user(
        user=user,
        provider=bind_payload["provider"],
        openid=bind_payload["openid"],
        unionid=bind_payload.get("unionid"),
        profile=bind_payload.get("profile"),
    )
    await revoke_bind_ticket(redis, bind_ticket)
    await user.fetch_related("language")
    return await user_service.build_login_response(
        redis=redis,
        user=user,
        login_type=bind_payload.get("login_type") or "wechat",
        is_new_user=False,
    )


async def complete_wechat_with_phone(
        redis: Redis,
        *,
        bind_ticket: str,
        phone: str,
        phone_hash: str,
        encrypted_phone: str,
        code: str,
) -> dict:
    bind_payload = await load_bind_ticket(redis, bind_ticket)
    phone_ok = await user_service.varify_phone_code(redis=redis, phone=phone, input_code=code)
    if not phone_ok:
        raise HTTPException(status_code=400, detail="短信验证码错误或已过期")

    user = await User.get_or_none(phone_hash=phone_hash).prefetch_related("language")
    is_new_user = False
    if user is None:
        identifier = bind_payload.get("unionid") or bind_payload["openid"] or phone
        user = await create_user_for_wechat_phone(
            phone=phone,
            phone_hash=phone_hash,
            encrypted_phone=encrypted_phone,
            identifier=identifier,
            profile=bind_payload.get("profile"),
        )
        is_new_user = True

    await bind_wechat_identity_to_user(
        user=user,
        provider=bind_payload["provider"],
        openid=bind_payload["openid"],
        unionid=bind_payload.get("unionid"),
        profile=bind_payload.get("profile"),
    )
    await revoke_bind_ticket(redis, bind_ticket)
    await user.fetch_related("language")
    return await user_service.build_login_response(
        redis=redis,
        user=user,
        login_type=bind_payload.get("login_type") or "wechat",
        is_new_user=is_new_user,
    )
