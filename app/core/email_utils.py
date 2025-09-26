import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def send_email(to_email: str, subject: str, content: str):
    msg = MIMEText(content, "html", "utf-8")
    msg["From"] = formataddr(("noreply-Lexiverse", SMTP_USER))
    msg["To"] = to_email
    msg["Subject"] = subject

    try:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        code, response = server.login(SMTP_USER, SMTP_PASS)
        print(f"[DEBUG] 登录响应: {code}, {response}")
        result = server.sendmail(SMTP_USER, [to_email], msg.as_string())
        print(f"[DEBUG] sendmail 返回: {result}")
        print(f"[DEBUG] 邮件已发送到 {to_email}")
        try:
            server.quit()  # 主动关闭连接
        except smtplib.SMTPResponseException as e:
            if e.smtp_code == -1:
                # QQ 邮箱常见问题：断开时返回非标准响应
                print(f"[WARN] 邮件发送成功，但服务器关闭连接时异常: {e.smtp_error}")
            else:
                raise
    except smtplib.SMTPAuthenticationError:
        print("[ERROR] 邮件认证失败，请检查账号和授权码是否正确")
        raise
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}")
        raise

def main(receiver: str, code: int = 123456):
    content_model = content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height:1.6;">
                <h2 style="color:#4CAF50;">Lexiverse 验证码</h2>
                <p>您好，</p>
                <p>您正在进行 <b>密码重置</b> 操作。</p>
                <p>
                  您的验证码是：
                  <span style="font-size: 24px; font-weight: bold; color: #d9534f;">{code}</span>
                </p>
                <p>有效期 5 分钟，请勿泄露给他人。</p>
                <hr>
                <p style="font-size: 12px; color: #999;">
                  如果这不是您本人的操作，请忽略此邮件。
                </p>
              </body>
            </html>
            """
    send_email(to_email=receiver, subject='Test Email', content=content_model)
    # send_email(to_email="GodricTan@gmail.com", subject="Test Email", content=content_model)

if __name__ == '__main__':
    xza = "3480039769@qq.com"
    bb = "1530799205@qq.com"
    me = "GodricTan@gmail.com"
    main(xza, code=123833)
