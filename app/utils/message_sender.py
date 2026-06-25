from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.sms.v20210111 import models, sms_client_async

from settings import settings


class MessageSender:
    def __init__(self):
        self.cred = credential.Credential(
            settings.TENCENTCLOUD_SECRET_ID,
            settings.TENCENTCLOUD_SECRET_KEY,
        )

        self.httpProfile = HttpProfile()
        self.httpProfile.reqMethod = "POST"
        self.httpProfile.reqTimeout = 10
        self.httpProfile.endpoint = "sms.tencentcloudapi.com"

        self.clientProfile = ClientProfile()
        self.clientProfile.signMethod = "TC3-HMAC-SHA256"
        self.clientProfile.language = "en-US"
        self.clientProfile.httpProfile = self.httpProfile

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        phone = (phone or "").strip()
        if phone.startswith("+"):
            return phone
        return f"+86{phone}"

    async def send_sms(self, phone: str, code: str, expire_time: str = "5"):
        try:
            client = sms_client_async.SmsClient(self.cred, "ap-guangzhou", self.clientProfile)
            req = models.SendSmsRequest()
            req.SmsSdkAppId = "1401041673"
            req.SignName = "沣东新城之爱百货经营部"
            req.TemplateId = "2657979"
            req.TemplateParamSet = [code, expire_time]
            req.PhoneNumberSet = [self._normalize_phone(phone)]
            req.SessionContext = ""
            req.ExtendCode = ""
            req.SenderId = ""

            return await client.SendSms(req)
        except TencentCloudSDKException as err:
            raise RuntimeError(f"腾讯云短信发送失败: {err}") from err
