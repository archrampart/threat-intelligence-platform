from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.info import AppInfo

router = APIRouter()


@router.get("/info", summary="Application metadata", tags=["info"], response_model=AppInfo)
def get_app_info() -> AppInfo:
    settings = get_settings()
    return AppInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        api_prefix=settings.api_v1_str,
        docs_url=settings.docs_url,
        timestamp=datetime.now(tz=timezone.utc),
    )
