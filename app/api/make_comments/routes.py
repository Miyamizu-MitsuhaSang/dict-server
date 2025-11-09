from typing import Tuple

from fastapi import APIRouter, Depends

from app.api.make_comments.comment_schemas import Feedback
from app.core.email_utils import send_email
from app.models import User
from app.utils.security import get_current_user

comment_router = APIRouter()


@comment_router.post("/improvements")
async def new_comment(
        upload: Feedback,
        user: Tuple[User, dict] = Depends(get_current_user)
):
    user_id = user[0].id
    username = user[0].name
    type = upload.report_part
    mail_text = upload.text
    sender = "no-reply@lexiverse.com.cn"
    receivers = ["GodricTan@gmail.com"]

    if type == "dict_fr":
        receivers.append("3480039769@qq.com") # 3480039769@qq.com

    content = f"""<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="utf-8">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>用户反馈通知</title>
    <style>
      @media (prefers-color-scheme: dark) {{
        body, .email-body {{ background: #0f172a !important; color: #e5e7eb !important; }}
        .card {{ background: #111827 !important; border-color: #374151 !important; }}
        .muted {{ color: #9ca3af !important; }}
        .badge {{ background: #1f2937 !important; color: #e5e7eb !important; border-color:#374151 !important; }}
      }}
    </style>
    </head>
    <body style="margin:0;padding:0;background:#f5f7fb;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fb;">
        <tr>
          <td align="center" style="padding:24px;">
            <table role="presentation" width="600" cellpadding="0" cellspacing="0" class="email-body" style="width:600px;max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;">
              <tr>
                <td style="background:linear-gradient(90deg,#4f46e5,#06b6d4);padding:22px 24px;">
                  <h1 style="margin:0;font-size:18px;line-height:1.4;color:#ffffff;">新的用户反馈</h1>
                  <p class="muted" style="margin:4px 0 0 0;font-size:12px;color:rgba(255,255,255,.85);">来自平台反馈中心</p>
                </td>
              </tr>

              <tr>
                <td style="padding:20px 24px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding:0 0 12px 0;font-size:14px;color:#111827;">
                        <strong>用户：</strong><span>{username}</span>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 0 12px 0;">
                        <span class="badge" style="display:inline-block;padding:6px 10px;border:1px solid #e5e7eb;border-radius:999px;font-size:12px;line-height:1;color:#374151;background:#f9fafb;">
                          反馈板块：{type}
                        </span>
                      </td>
                    </tr>
                  </table>

                  <div class="card" style="margin-top:8px;border:1px solid #e5e7eb;border-radius:10px;background:#ffffff;">
                    <div style="padding:16px 18px;">
                      <div style="font-size:13px;color:#6b7280;margin-bottom:8px;">反馈内容</div>
                      <div style="font-size:15px;line-height:1.7;color:#111827;white-space:pre-wrap;">
                        {mail_text}
                      </div>
                    </div>
                  </div>

                  <p class="muted" style="margin:16px 0 0 0;font-size:12px;color:#6b7280;">
                    您收到此邮件是因为系统检测到有新的反馈提交。请在后台查看详情并进行处理。
                  </p>
                </td>
              </tr>

              <tr>
                <td style="padding:16px 24px;border-top:1px solid #e5e7eb;">
                  <table width="100%" role="presentation" cellpadding="0" cellspacing="0">
                    <tr>
                      <td align="left" class="muted" style="font-size:12px;color:#9ca3af;">
                        这是一封系统通知邮件，请勿直接回复。
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>"""

    for receiver in receivers:
        send_email(to_email=receiver, subject="用户反馈", content=content)

    return {"massages": "feedback succeed"}
