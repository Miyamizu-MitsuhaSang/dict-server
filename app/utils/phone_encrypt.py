import base64
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv

load_dotenv()


class PhoneEncrypt:
    def __init__(self, key: bytes):
        self.key = key
        if len(self.key) not in (16, 24, 32):
            raise ValueError("AES 密钥必须是 16/24/32 字节")

    @classmethod
    def from_env(cls):
        hex_key = os.getenv("AES_SECRET_KEY")
        return cls(bytes.fromhex(hex_key))

    def encrypt(self, phone: str) -> str:
        """
        加密手机号 -> 返回 Base64 字符串
        :return iv为解密初始数
                ct为加密密文
        """
        cipher = AES.new(self.key, AES.MODE_CBC)  # 随机 IV
        ct_bytes = cipher.encrypt(pad(phone.encode(), AES.block_size))
        iv = base64.b64encode(cipher.iv).decode()
        ct = base64.b64encode(ct_bytes).decode()
        return f"{iv}:{ct}"

    def decrypt(self, data: str) -> str:
        """解密 Base64 字符串 -> 返回手机号"""
        iv_b64, ct_b64 = data.split(":")
        iv = base64.b64decode(iv_b64)
        ct = base64.b64decode(ct_b64)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode()


def main():
    phone_encrypt = PhoneEncrypt()
    encrypted = phone_encrypt.encrypt("13568847988")
    print(encrypted)

    decrypted = phone_encrypt.decrypt(encrypted)
    print(decrypted)


if __name__ == '__main__':
    main()
