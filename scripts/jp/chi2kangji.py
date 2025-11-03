import io
import pandas as pd
import re
import requests
import zipfile

url = "https://www.unicode.org/Public/15.1.0/ucd/Unihan.zip"
print("📦 正在下载 Unihan 数据包...")
r = requests.get(url)
r.raise_for_status()

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    txt = z.read("Unihan_Variants.txt").decode("utf-8") + \
          "\n" + z.read("Unihan_Readings.txt").decode("utf-8")

print("✅ 数据加载成功")

# --- 匹配所需字段 ---
re_simpl = re.compile(r"U\+([0-9A-F]+)\tkSimplifiedVariant\t(U\+[0-9A-F]+)")
re_zvar  = re.compile(r"U\+([0-9A-F]+)\tkZVariant\t(U\+[0-9A-F]+)")
re_jp_on = re.compile(r"U\+([0-9A-F]+)\tkJapaneseOn\t(.+)")
re_jp_kun = re.compile(r"U\+([0-9A-F]+)\tkJapaneseKun\t(.+)")

simpl_map, zvar_map, jp_on, jp_kun = {}, {}, {}, {}

for m in re_simpl.finditer(txt):
    trad_hex, simp_hex = m.groups()
    trad, simp = chr(int(trad_hex, 16)), chr(int(simp_hex, 16))
    simpl_map[trad] = simp

for m in re_zvar.finditer(txt):
    base_hex, var_hex = m.groups()
    base, var = chr(int(base_hex, 16)), chr(int(var_hex, 16))
    zvar_map[base] = var

for m in re_jp_on.finditer(txt):
    code_hex, reading = m.groups()
    char = chr(int(code_hex, 16))
    jp_on[char] = reading.replace(" ", "、")

for m in re_jp_kun.finditer(txt):
    code_hex, reading = m.groups()
    char = chr(int(code_hex, 16))
    jp_kun[char] = reading.replace(" ", "、")

rows = []
for trad, simp in simpl_map.items():
    # 关键：找繁体→日语新字体的异体关系
    if trad in zvar_map:
        jp_char = zvar_map[trad]
        if jp_char in jp_on or jp_char in jp_kun:
            kana_on = jp_on.get(jp_char, "")
            kana_kun = jp_kun.get(jp_char, "")
            kana = kana_on + ("、" + kana_kun if kana_on and kana_kun else kana_kun)
            rows.append([simp, trad, jp_char, kana, "是", "由繁体→简体+异体→日语新字体推导"])

df = pd.DataFrame(rows, columns=["简体汉字", "繁体汉字", "日语汉字", "假名读音", "是否异体", "备注"])
df.to_excel("中日汉字映射表_六列综合版.xlsx", index=False)

print(f"✅ 已生成文件，共 {len(df)} 条记录。")
