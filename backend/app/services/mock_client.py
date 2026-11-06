from typing import Any, Dict

from app.services.base_client import BaseThreatClient


class MockThreatClient(BaseThreatClient):
    """Simple mock client until real integrations are implemented."""

    async def query(self, ioc_type: str, ioc_value: str) -> Dict[str, Any]:
        return {
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "risk_score": None,
            "status": "pending",
            "message": "Integration not implemented",
        }
