from fastapi import APIRouter, Depends

from app.api.admin.admin_articles.routes import admin_banner_router
from app.utils.security import is_admin_user

admin_router = APIRouter(dependencies=[Depends(is_admin_user)])

admin_router.include_router(admin_banner_router, prefix="/article")
