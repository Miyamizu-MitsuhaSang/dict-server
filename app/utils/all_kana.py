import jaconv
import pykakasi

kks = pykakasi.kakasi()
kks.setMode("H", "a")  # 平假名 -> ascii (罗马字)
kks.setMode("K", "a")  # 片假名 -> ascii
kks.setMode("J", "a")  # 汉字   -> ascii
kks.setMode("r", "Hepburn")  # 转换成 Hepburn 罗马字
conv = kks.getConverter()


def all_in_kana(text: str) -> str:
    """
    将输入统一转换为平假名，支持：
    - 平假名
    - 片假名
    - 罗马字 (Hepburn 转写)

    返回：平假名字符串
    """
    if not text:
        return ""

    # 1. 片假名 → 平假名
    normalized = jaconv.kata2hira(text)

    # 2. 如果里面含有罗马字字符，就先转成假名
    if any("a" <= ch.lower() <= "z" for ch in normalized):
        hira = conv.do(normalized)  # 罗马字 -> 平假名
        normalized = jaconv.kata2hira(hira)

    # 3. 再次片假名 -> 平假名保险
    normalized = jaconv.kata2hira(normalized)

    return normalized