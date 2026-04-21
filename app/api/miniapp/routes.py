from fastapi import APIRouter, Request

from app.api.miniapp import service
from app.api.miniapp.miniapp_schemas import MiniappHomeResponse

miniapp_router = APIRouter()


@miniapp_router.get("/home", response_model=MiniappHomeResponse)
async def get_home(request: Request):
    return await service.get_miniapp_home_payload(request.app.state.redis)
