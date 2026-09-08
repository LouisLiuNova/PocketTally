"""顶层 API 路由。"""

from fastapi import APIRouter

from app.api.routes.accounts import router as accounts_router
from app.api.routes.categories import router as categories_router
from app.api.routes.health import router as health_router
from app.api.routes.statistics import router as statistics_router
from app.api.routes.tags import router as tags_router
from app.api.routes.transactions import router as transactions_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(tags_router)
api_router.include_router(transactions_router)
api_router.include_router(statistics_router)
