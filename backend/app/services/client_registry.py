from typing import Dict, List

from app.services.base_client import BaseThreatClient
from app.services.mock_client import MockThreatClient


class ThreatClientRegistry:
    def __init__(self) -> None:
        self._clients: Dict[str, BaseThreatClient] = {}

    def register(self, name: str, client: BaseThreatClient) -> None:
        self._clients[name] = client

    def get(self, name: str) -> BaseThreatClient | None:
        return self._clients.get(name)

    def list_clients(self) -> List[str]:
        return list(self._clients.keys())

    def get_all(self) -> Dict[str, BaseThreatClient]:
        return self._clients


client_registry = ThreatClientRegistry()
client_registry.register("mock", MockThreatClient(name="mock"))
