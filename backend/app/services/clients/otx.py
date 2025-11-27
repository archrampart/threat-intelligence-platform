from typing import Any, Dict

from app.services.base_client import BaseThreatClient


class OTXMockClient(BaseThreatClient):
    """AlienVault OTX mock client."""

    async def query(self, ioc_type: str, ioc_value: str) -> Dict[str, Any]:
        suspicious = "pulse" in ioc_value.lower() or "threat" in ioc_value.lower()

        risk_score = 0.65 if suspicious else 0.25
        status = "listed" if suspicious else "not_listed"
        message = "OTX mock: pulse match" if suspicious else "OTX mock: no pulse found"

        return {
            "source": "otx",
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "risk_score": risk_score,
            "status": status,
            "message": message,
            "raw": {
                "mock": True,
                "pulse_count": 3 if suspicious else 0,
            },
        }
