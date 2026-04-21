import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.user.user_schemas import MiniProgramLoginRequest
from settings import settings
from . import service

auth_wechat_router = APIRouter()


def _build_frontend_redirect(base_url: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


@auth_wechat_router.get("/login")
async def wechat_login(request: Request):
    """
    1) 生成 state 防 CSRF
    2) 跳转到微信开放平台扫码登录页
    """
    service.ensure_wechat_settings()

    state = secrets.token_urlsafe(16)
    await service.put_state(request.app.state.redis, state)

    authorize_url = service.build_authorize_url(state)
    return RedirectResponse(authorize_url)


@auth_wechat_router.get("/callback")
async def wechat_callback(
        request: Request,
        code: str | None = Query(default=None),
        state: str | None = Query(default=None),
):
    """
    微信扫码回调：
    校验 state -> 用 code 换 openid/access_token -> 查找或创建站内用户 -> 签发站内 JWT
    """
    service.ensure_wechat_settings()

    if not code or not state:
        detail = "微信回调缺少 code 或 state"
        if settings.WECHAT_CALLBACK_FAILURE_URL:
            return RedirectResponse(
                _build_frontend_redirect(settings.WECHAT_CALLBACK_FAILURE_URL, {"error": detail})
            )
        raise HTTPException(status_code=400, detail=detail)

    if not await service.pop_state_if_valid(request.app.state.redis, state):
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

    login_result = await service.finalize_wechat_login(
        redis=request.app.state.redis,
        provider=service.WECHAT_OPEN_PROVIDER,
        openid=openid,
        unionid=unionid,
        profile=profile,
        login_type="wechat_open",
    )

    if settings.WECHAT_CALLBACK_SUCCESS_URL:
        redirect_url = _build_frontend_redirect(
            settings.WECHAT_CALLBACK_SUCCESS_URL,
            {
                "token": login_result["access_token"],
                "login_type": "wechat",
            },
        )
        return RedirectResponse(redirect_url)

    return JSONResponse(login_result)


@auth_wechat_router.post("/mini/login")
async def wechat_mini_login(request: Request, body: MiniProgramLoginRequest):
    service.ensure_wechat_mini_settings()

    session_data = await service.wechat_mini_exchange_code_for_session(body.code)
    openid = session_data["openid"]
    unionid = session_data.get("unionid")

    login_result = await service.finalize_wechat_login(
        redis=request.app.state.redis,
        provider=service.WECHAT_MINI_PROVIDER,
        openid=openid,
        unionid=unionid,
        profile=None,
        login_type="wechat_miniapp",
    )
    return JSONResponse(login_result)
