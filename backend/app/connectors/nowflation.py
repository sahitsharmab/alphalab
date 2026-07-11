"""Connector for Nowflation (https://nowflation.com).

Nowflation publishes open CSV exports of its daily market-price inflation
gauge (base January 2018 = 100). No API key, no advertised rate limits.
We use only the documented CSV export endpoints; the dashboard's JSON
endpoints are undocumented and not reachable outside the browser context
(verified 2026-07-11, see DECISIONS.md Session 003).
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

PROVIDER = "nowflation"
DATASET_HEADLINE = "inflation.headline"

_HEADLINE_PATH = "/api/inflation/export/headline.csv"


class NowflationConnector(BaseConnector):
    """Retrieves Nowflation's daily headline inflation gauge."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = "https://nowflation.com",
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
    ) -> None:
        super().__init__(client, max_attempts, backoff_base_seconds)
        self._base_url = base_url.rstrip("/")

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="NowflationConnector",
            provider=PROVIDER,
            base_url=self._base_url,
            datasets=(DATASET_HEADLINE,),
        )

    async def fetch_headline(self) -> FetchResult:
        """Download the full daily headline gauge CSV (2018 → today)."""
        return await self._get_text(f"{self._base_url}{_HEADLINE_PATH}", DATASET_HEADLINE)

    async def health(self) -> ConnectorHealth:
        start = time.perf_counter()
        try:
            await self.fetch_headline()
        except ConnectorError as exc:
            return ConnectorHealth(status="unavailable", error=str(exc))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return ConnectorHealth(status="ok", latency_ms=latency_ms)
