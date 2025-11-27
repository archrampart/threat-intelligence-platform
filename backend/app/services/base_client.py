from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseThreatClient(ABC):
    """Base class for threat intelligence source clients."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def query(self, ioc_type: str, ioc_value: str) -> Dict[str, Any]:
        """Run query for given IOC and return raw response."""

    @staticmethod
    def normalize_risk(score: float | None) -> str | None:
        if score is None:
            return None
        if score >= 0.8:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"
