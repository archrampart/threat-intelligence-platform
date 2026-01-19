from typing import Any, Dict

from app.services.base_client import BaseThreatClient


class VirusTotalMockClient(BaseThreatClient):
    """Basit bir VirusTotal mock client."""

    async def query(self, ioc_type: str, ioc_value: str) -> Dict[str, Any]:
        keywords = ["malware", "phish", "botnet"]
        suspicious = any(keyword in ioc_value.lower() for keyword in keywords)

        if suspicious:
            risk_score = 0.85
            status = "malicious"
            message = "VirusTotal mock: malicious keyword detected"
        else:
            risk_score = 0.15
            status = "harmless"
            message = "VirusTotal mock: no malicious indicators"

        return {
            "source": "virustotal",
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "risk_score": risk_score,
            "status": status,
            "message": message,
            "raw": {
                "mock": True,
                "detected_keywords": keywords if suspicious else [],
            },
        }
