import re
from html import unescape


def strip_html_tags(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sanitize_html(html: str) -> str:
    """
    简化版清洗：
    - 去掉 script/style 标签内容
    - 去掉明显的 onxxx 事件属性
    这不是完整生产级 XSS 防护，但比完全裸存强。
    真正上线建议接 bleach 白名单。

    Args:
        html (str): 编辑器上传的 html 源码
    """
    # TODO 接入 bleach 白名单
    if not html:
        return ""

    html = re.sub(
        r"<(script|style).*?>.*?</\1>",
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL
    )
    html = re.sub(
        r"\son\w+\s*=\s*['\"].*?['\"]",
        "",
        html,
        flags=re.IGNORECASE
    )
    html = re.sub(
        r"\sjavascript:",
        "",
        html,
        flags=re.IGNORECASE
    )
    return html