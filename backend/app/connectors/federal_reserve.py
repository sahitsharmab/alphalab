"""Connector for the Federal Reserve website calendar (trust 10).

``/json/calendar.json`` is the JSON feed behind the Fed's own calendar
pages (verified 2026-07-12): FOMC meetings/minutes/press conferences,
Beige Book, statistical releases, speeches, testimony. No key required.
"""

import time

import httpx

from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    ConnectorHealth,
    ConnectorMetadata,
    FetchResult,
)

PROVIDER = "federal_reserve"
DATASET_CALENDAR = "calendar.events"


class FederalReserveConnector(BaseConnector):
    """Retrieves the Fed's public event calendar."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = "https://www.federalreserve.gov",
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
    ) -> None:
        super().__init__(client, max_attempts, backoff_base_seconds)
        self._base_url = base_url.rstrip("/")

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="FederalReserveConnector",
            provider=PROVIDER,
            base_url=self._base_url,
            datasets=(DATASET_CALENDAR,),
        )

    async def fetch_calendar(self) -> FetchResult:
        return await self._get_text(f"{self._base_url}/json/calendar.json", DATASET_CALENDAR)

    async def health(self) -> ConnectorHealth:
        start = time.perf_counter()
        try:
            await self.fetch_calendar()
        except ConnectorError as exc:
            return ConnectorHealth(status="unavailable", error=str(exc))
        return ConnectorHealth(
            status="ok", latency_ms=round((time.perf_counter() - start) * 1000, 2)
        )
