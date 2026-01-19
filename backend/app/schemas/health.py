from datetime import datetime

from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    environment: str
