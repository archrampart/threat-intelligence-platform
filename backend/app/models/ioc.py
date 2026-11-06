from datetime import datetime, timezone
from typing import List

from app.schemas.ioc import IOCQueryRequest, IOCQueryResponse, IOCSourceResult
from app.services.client_registry import client_registry


class IOCQueryModel:
    def __init__(self, payload: IOCQueryRequest) -> None:
        self.payload = payload
        self.sources = payload.sources or client_registry.list_clients()

    async def execute(self) -> IOCQueryResponse:
        results: List[IOCSourceResult] = []

        for source_name in self.sources:
            client = client_registry.get(source_name)
            if client is None:
                results.append(
                    IOCSourceResult(
                        source=source_name,
                        status="unknown_source",
                        description="Source client not registered",
                    )
                )
                continue

            raw = await client.query(self.payload.ioc_type, self.payload.ioc_value)
            results.append(
                IOCSourceResult(
                    source=source_name,
                    status=raw.get("status", "pending"),
                    risk_score=raw.get("risk_score"),
                    description=raw.get("message"),
                    raw=raw,
                )
            )

        return IOCQueryResponse(
            ioc_type=self.payload.ioc_type,
            ioc_value=self.payload.ioc_value,
            overall_risk=None,
            queried_sources=results,
            queried_at=datetime.now(timezone.utc),
        )
