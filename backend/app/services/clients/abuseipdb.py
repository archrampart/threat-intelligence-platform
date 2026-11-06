from typing import Any, Dict

from app.services.base_client import BaseThreatClient


class AbuseIPDBMockClient(BaseThreatClient):
    """AbuseIPDB mock client based on simple keyword heuristics."""

    async def query(self, ioc_type: str, ioc_value: str) -> Dict[str, Any]:
        if ioc_type != "ip":
            return {
                "source": "abuseipdb",
                "ioc_type": ioc_type,
                "ioc_value": ioc_value,
                "risk_score": None,
                "status": "not_supported",
                "message": "AbuseIPDB only supports IP indicators",
            }

        risky_octets = {"666", "999", "123"}
        suspicious = any(octet in ioc_value for octet in risky_octets)

        risk_score = 0.7 if suspicious else 0.1
        status = "reported" if suspicious else "clean"
        message = "AbuseIPDB mock: abuse confidence score simulated"

        return {
            "source": "abuseipdb",
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "risk_score": risk_score,
            "status": status,
            "message": message,
            "raw": {
                "mock": True,
                "abuse_confidence": risk_score * 100,
            },
        }
