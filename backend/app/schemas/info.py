from datetime import datetime

from pydantic import BaseModel


class AppInfo(BaseModel):
    name: str
    version: str
    environment: str
    api_prefix: str
    docs_url: str | None
    timestamp: datetime
