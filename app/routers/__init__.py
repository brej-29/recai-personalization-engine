from fastapi import APIRouter

from . import admin, health, items, monitoring, recommend, stats, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(stats.router, prefix="/v1")
api_router.include_router(items.router, prefix="/v1")
api_router.include_router(recommend.router, prefix="/v1")
api_router.include_router(users.router, prefix="/v1")
api_router.include_router(admin.admin_router, prefix="/v1")
api_router.include_router(admin.tracking_router, prefix="/v1")
api_router.include_router(monitoring.router)