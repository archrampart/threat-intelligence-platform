from fastapi import APIRouter

from app.core.config import get_settings
from .routes import alert, api_key, api_source, auth, dashboard, health, info, ioc, watchlist, cve, report, users

settings = get_settings()

api_router = APIRouter()
api_router.include_router(health.router, prefix="", tags=["health"])
api_router.include_router(info.router, prefix="", tags=["info"])
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(api_key.router, tags=["api-keys"])
api_router.include_router(api_source.router, tags=["api-sources"])
api_router.include_router(ioc.router, tags=["ioc"])
api_router.include_router(watchlist.router, tags=["watchlists"])
api_router.include_router(cve.router, tags=["cves"])
api_router.include_router(report.router, tags=["reports"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(alert.router, tags=["alerts"])
