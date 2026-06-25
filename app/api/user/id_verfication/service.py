import asyncio
import json

from fastapi import HTTPException
from tencentcloud.common import credential
from tencentcloud.common.exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.faceid.v20180301 import models, faceid_client

from settings import settings

async def id_verify(real_name: str, id_number: str):
    try:
        cred = credential.Credential(settings.TENCENTCLOUD_SECRET_ID, settings.TENCENTCLOUD_SECRET_KEY)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "faceid.tencentcloudapi.com"

        # 实例化一个client选项，可选的，没有特殊需求可以跳过
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        # 实例化要请求产品的client对象,clientProfile是可选的
        client = faceid_client.FaceidClient(cred, "", clientProfile)

        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.IdCardVerificationRequest()
        params = {
            "IdCard": real_name,
            "Name": id_number,
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个IdCardVerificationResponse的实例，与请求对象对应
        resp = client.IdCardVerification(req)
        # 输出json格式的字符串回包
        print(resp.to_json_string())
        return resp.to_json_string()

    except TencentCloudSDKException as err:
        print(err)
        raise HTTPException(status_code=400, detail=err.message)

async def main():
    await id_verify()

if __name__ == '__main__':
    asyncio.run(main())