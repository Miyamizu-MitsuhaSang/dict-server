"""
访问日志脱敏工具。

monitor 会打印接口访问记录，但不能把 token、密码、验证码等敏感信息直接打到控制台。
这个文件专门负责“哪些字段需要隐藏”和“如何隐藏”。
"""

from urllib.parse import parse_qsl, urlencode


# query 参数中命中这些名字时，会被替换为 ******。
SENSITIVE_QUERY_KEYS = {
    "access_token",
    "authorization",
    "code",
    "email_code",
    "password",
    "phone",
    "refresh_token",
    "token",
}

MASK = "******"


def sanitize_query_string(query: str) -> str:
    """
    对 URL query 参数做脱敏。

    示例：
    token=abc&lang=fr-FR -> token=******&lang=fr-FR

    这里只处理 URL 后面的 query，不读取请求体，避免影响上传文件和表单接口。
    """
    if not query:
        return ""

    sanitized_pairs = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY_KEYS:
            sanitized_pairs.append((key, MASK))
        else:
            sanitized_pairs.append((key, value))

    return urlencode(sanitized_pairs)
