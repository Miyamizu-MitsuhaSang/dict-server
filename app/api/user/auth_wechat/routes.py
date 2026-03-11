import secrets

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from settings import settings

auth_wechat_router = APIRouter()


@auth_wechat_router.post("/login")
async def wechat_login():
    """
    1) 生成 state 防 CSRF
    2) 重定向到微信扫码登录页
    """
    WECHAT_APPID = settings.WECHAT_APPID
    WECHAT_SECRET = settings.WECHAT_SECRET

    if not WECHAT_APPID or not WECHAT_SECRET:
        raise HTTPException(status_code=500, detail="WECHAT_APPID/WECHAT_SECRET not configured")

    state = secrets.token_urlsafe(16)

    authorize_url = (
        "https://open.weixin.qq.com/connect/qrconnect"
        f"?appid={WECHAT_APPID}"
        f"&redirect_uri={httpx.URL(settings.WECHAT_REDIRECT_URI)}"
        "&response_type=code"
        "&scope=snsapi_login"
        f"&state={state}"
        "#wechat_redirect"
    )

    return RedirectResponse(authorize_url)

# @auth_wechat_router.get("/callback")
# async def wechat_callback(code: str, state: str):
#     """
#     微信回调：校验 state -> 用 code 换取 access_token/openid -> (可选)拿用户信息 -> 映射站内用户 -> 签发站内token
#     """
#     if not pop_state_if_valid(state):
#         raise HTTPException(status_code=400, detail="Invalid or expired state")
#
#     token_data = await wechat_exchange_code_for_token(code)
#     openid = token_data["openid"]
#     access_token = token_data["access_token"]
#     unionid = token_data.get("unionid")
#
#     # 可选：拿用户资料（昵称头像等），失败也可以不阻断，看你业务
#     profile = None
#     try:
#         profile = await wechat_get_userinfo(access_token, openid)
#     except Exception:
#         profile = None
#
#     user_id = await get_or_create_user_by_wechat(openid, unionid, profile)
#     our_token = issue_our_token(user_id)
#
#     # 你可以：1) 返回 JSON 给前端；2) 重定向回前端页面并带 token；3) 写 Cookie
#     return JSONResponse(
#         {
#             "user_id": user_id,
#             "token": our_token,
#             "wechat_profile": profile,  # 可选返回
#         }
#     )