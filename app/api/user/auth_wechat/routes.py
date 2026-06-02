import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.user import service as user_service
from app.api.user.user_schemas import MiniProgramLoginRequest, WechatBindExistingRequest, WechatCodeLoginRequest, \
    UserResetPhoneRequest, WechatPhoneCompleteRequest
from app.models.base import User
from app.utils.security import get_current_user, get_optional_current_user
from settings import settings
from . import service

auth_wechat_router = APIRouter()


def _build_frontend_redirect(base_url: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


def _current_user_or_none(user_payload):
    if not user_payload:
        return None
    return user_payload[0]


@auth_wechat_router.get("/login")
async def wechat_login(request: Request):
    service.ensure_wechat_settings()
    state = secrets.token_urlsafe(16)
    await service.save_state(
        request.app.state.redis,
        state,
        {
            "action": "login",
            "provider": service.WECHAT_OPEN_PROVIDER,
            "login_type": "wechat_open",
        },
    )
    return RedirectResponse(service.build_authorize_url(state))


@auth_wechat_router.post("/bind/start")
async def wechat_bind_start(
        request: Request,
        user_payload=Depends(get_current_user),
):
    user, _ = user_payload
    service.ensure_wechat_settings()

    state = secrets.token_urlsafe(16)
    await service.save_state(
        request.app.state.redis,
        state,
        {
            "action": "bind",
            "user_id": user.id,
            "provider": service.WECHAT_OPEN_PROVIDER,
            "login_type": "wechat_open",
        },
    )
    return {
        "authorize_url": service.build_authorize_url(state),
        "message": "请跳转到微信授权页完成绑定",
    }


@auth_wechat_router.get("/callback")
async def wechat_callback(
        request: Request,
        code: str | None = Query(default=None),
        state: str | None = Query(default=None),
):
    service.ensure_wechat_settings()

    if not code or not state:
        detail = "微信回调缺少 code 或 state"
        if settings.WECHAT_CALLBACK_FAILURE_URL:
            return RedirectResponse(
                _build_frontend_redirect(settings.WECHAT_CALLBACK_FAILURE_URL, {"error": detail})
            )
        raise HTTPException(status_code=400, detail=detail)

    state_payload = await service.consume_state(request.app.state.redis, state)
    if not state_payload:
        detail = "无效或过期的微信登录 state"
        if settings.WECHAT_CALLBACK_FAILURE_URL:
            return RedirectResponse(
                _build_frontend_redirect(settings.WECHAT_CALLBACK_FAILURE_URL, {"error": detail})
            )
        raise HTTPException(status_code=400, detail=detail)

    token_data = await service.wechat_exchange_code_for_token(code)
    openid = token_data["openid"]
    access_token = token_data["access_token"]
    unionid = token_data.get("unionid")

    profile = None
    try:
        profile = await service.wechat_get_userinfo(access_token=access_token, openid=openid)
    except HTTPException:
        profile = None

    action = state_payload.get("action") or "login"
    provider = state_payload.get("provider") or service.WECHAT_OPEN_PROVIDER
    login_type = state_payload.get("login_type") or "wechat_open"

    if action == "bind":
        user_id = state_payload.get("user_id")
        user = await User.get_or_none(id=user_id).prefetch_related("language")
        if not user:
            raise HTTPException(status_code=404, detail="待绑定用户不存在")
        await service.bind_wechat_identity_to_user(
            user=user,
            provider=provider,
            openid=openid,
            unionid=unionid,
            profile=profile,
        )
        result = {
            "status": "bound",
            "message": "微信绑定成功",
            "user": {
                "id": user.id,
                "username": user.name,
            },
        }
        if settings.WECHAT_CALLBACK_SUCCESS_URL:
            return RedirectResponse(
                _build_frontend_redirect(
                    settings.WECHAT_CALLBACK_SUCCESS_URL,
                    {"status": "bound", "login_type": login_type},
                )
            )
        return JSONResponse(result)

    login_result = await service.resolve_wechat_login(
        redis=request.app.state.redis,
        provider=provider,
        openid=openid,
        unionid=unionid,
        profile=profile,
        login_type=login_type,
    )

    if settings.WECHAT_CALLBACK_SUCCESS_URL:
        if login_result.get("status") == "need_phone":
            return RedirectResponse(
                _build_frontend_redirect(
                    settings.WECHAT_CALLBACK_SUCCESS_URL,
                    {
                        "status": "need_phone",
                        "bind_ticket": login_result["bind_ticket"],
                        "login_type": login_result["login_type"],
                    },
                )
            )
        return RedirectResponse(
            _build_frontend_redirect(
                settings.WECHAT_CALLBACK_SUCCESS_URL,
                {
                    "token": login_result["access_token"],
                    "login_type": login_type,
                },
            )
        )

    return JSONResponse(login_result)


@auth_wechat_router.post("/bind/existing")
async def wechat_bind_existing(request: Request, body: WechatBindExistingRequest):
    result = await service.bind_existing_account_with_ticket(
        redis=request.app.state.redis,
        bind_ticket=body.bind_ticket,
        username=body.username,
        password=body.password,
    )
    return JSONResponse(result)


@auth_wechat_router.post("/phone_verify")
async def wechat_phone_verify(
        request: Request,
        body: UserResetPhoneRequest,
        bind_ticket: str = Query(...),
):
    await service.load_bind_ticket(request.app.state.redis, bind_ticket)
    phone = request.app.state.phone_encrypto.normalize(body.phone_number)
    code = user_service.generate_code()
    await user_service.send_sms_code(
        redis=request.app.state.redis,
        phone=phone,
        code=code,
        ops_type="wechat",
    )
    return {"message": "验证码已发送"}


@auth_wechat_router.post("/complete_by_phone")
async def wechat_complete_by_phone(request: Request, body: WechatPhoneCompleteRequest):
    phone = request.app.state.phone_encrypto.normalize(body.phone_number)
    phone_hash = request.app.state.phone_encrypto.hash(phone)
    encrypted_phone = request.app.state.phone_encrypto.encrypt(phone)
    result = await service.complete_wechat_with_phone(
        redis=request.app.state.redis,
        bind_ticket=body.bind_ticket,
        phone=phone,
        phone_hash=phone_hash,
        encrypted_phone=encrypted_phone,
        code=body.code,
    )
    return JSONResponse(result)


@auth_wechat_router.post("/mini/login")
async def wechat_mini_login(
        request: Request,
        body: MiniProgramLoginRequest,
        current_user_payload=Depends(get_optional_current_user),
):
    service.ensure_wechat_mini_settings()

    session_data = await service.wechat_mini_exchange_code_for_session(body.code)
    result = await service.resolve_or_bind_wechat_login(
        redis=request.app.state.redis,
        provider=service.WECHAT_MINI_PROVIDER,
        openid=session_data["openid"],
        unionid=session_data.get("unionid"),
        profile=None,
        login_type="wechat_miniapp",
        current_user=_current_user_or_none(current_user_payload),
    )
    return JSONResponse(result)


@auth_wechat_router.post("/app/login")
async def wechat_app_login(
        request: Request,
        body: WechatCodeLoginRequest,
        current_user_payload=Depends(get_optional_current_user),
):
    service.ensure_wechat_settings()

    token_data = await service.wechat_exchange_code_for_token(body.code)
    openid = token_data["openid"]
    access_token = token_data["access_token"]
    unionid = token_data.get("unionid")

    profile = None
    try:
        profile = await service.wechat_get_userinfo(access_token=access_token, openid=openid)
    except HTTPException:
        profile = None

    result = await service.resolve_or_bind_wechat_login(
        redis=request.app.state.redis,
        provider=service.WECHAT_OPEN_PROVIDER,
        openid=openid,
        unionid=unionid,
        profile=profile,
        login_type="wechat_app",
        current_user=_current_user_or_none(current_user_payload),
    )
    return JSONResponse(result)
