import unicodedata

import jaconv
import pykakasi
from pykakasi import kakasi

# ---- 全局初始化（只做一次）----
_kakasi = kakasi()
_kakasi.setMode("J", "H")  # Kanji -> Hiragana（依据词典近似读音）
_kakasi.setMode("K", "H")  # Katakana -> Hiragana
_kakasi.setMode("H", "H")  # Hiragana -> Hiragana（不变）
# 可选：保留原文空格/标点；如需去除空格可自行处理
_converter = _kakasi.getConverter()

def all_in_kana(text: str) -> str:
    """
    将任意日文输入（汉字/平假名/片假名/半角假名混排）
    统一转换为“标准化的平假名”。
    """
    if not text:
        return ""

    # 1) 规格化（全半角/兼容等）：避免隐形差异
    s = unicodedata.normalize("NFKC", text).strip()

    # 2) 先做假名统一（片假名 -> 平假名；半角片假名也会被 NFKC 规范化）
    #   这一步对只有假名的输入能直接得到平假名
    s = jaconv.kata2hira(s)

    # 3) 用 pykakasi 将汉字（以及残留的片假名）转换为“平假名读音”
    #   - 对纯假名基本保持不变
    #   - 对汉字给出近似读音（依赖内置词典，个别专有名词可能不完美）
    hira = _converter.do(s)

    # 4) 兜底：再转一次平假名，保证输出统一
    hira = jaconv.kata2hira(hira)

    # 5) 可选清洗：去掉多余空白（如果你不想保留空格）
    # hira = "".join(hira.split())

    return hira

if __name__ == '__main__':
    print(all_in_kana('能力'))