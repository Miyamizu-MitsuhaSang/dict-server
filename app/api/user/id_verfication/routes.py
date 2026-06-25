from fastapi import APIRouter, Depends

from app.api.user.id_verfication import service
from app.api.user.id_verfication.id_verification_schemas import IdVerificationRequest
from app.models import User
from app.utils.security import get_current_user

id_verification_router = APIRouter()

@id_verification_router.post(
    path="/verify",
    description="核验用户身份信息",
    dependencies=[Depends(get_current_user)],
    deprecated=True,
)
async def verify(id_info: IdVerificationRequest, current_user: User = Depends(get_current_user)):
    verification_response = await service.id_verify(id_info.model_dump())

    return verification_response

@id_verification_router.post(
    path="/verify_phone",
    description="注入用户手机号",
    dependencies=[Depends(get_current_user)],
    deprecated=True,
)
async def verify_phone():
    pass