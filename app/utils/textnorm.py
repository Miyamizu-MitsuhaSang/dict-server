import re
import unicodedata


def normalize_text(s: str) -> str:
    """
    规范化字符串，用于搜索/存储 search_text
    - Unicode 标准化
    - 去除重音符号（é -> e）
    - 转小写
    - 去掉前后空格，多空格合并
    """
    if not s:
        return ""
    # 1. Unicode 标准化（NFKD 拆分）
    s = unicodedata.normalize("NFKD", s)
    # 2. 去掉音标/重音符
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # 3. 转小写
    s = s.lower()
    # 4. 去掉首尾空格 & 合并多个空格
    s = re.sub(r"\s+", " ", s.strip())
    return s
