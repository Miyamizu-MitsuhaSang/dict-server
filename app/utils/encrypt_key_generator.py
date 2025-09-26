"""
本脚本对于同一个加密密钥只允许生成一次
"""
import secrets

key = secrets.token_hex(32)  # 生成 32字节 (256 bit) 十六进制字符串
print(key)
print(len(key))  # 64个字符 (32字节 -> hex编码 = 64字符)
