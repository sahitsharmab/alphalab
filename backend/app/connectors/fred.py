"""Connector for the FRED release-dates API (trust 9).

``/fred/release/dates`` with ``include_release_dates_with_no_data=true``
returns FUTURE scheduled dates for official economic releases (CPI, PPI,
jobs report, GDP, ...) — verified empirically 2026-07-12. Requires a free
API key; per FRED terms the product must display: "This product uses the
FRED® API but is not endorsed or certified by the Federal Reserve Bank of
St. Louis." (shown in the workspace footer).

The API key travels only as a request param — it never appears in stored
URLs, raw payloads, or logs.
"""

import time
from datetime import date

import httpx

from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    ConnectorHealth,
    ConnectorMetadata,
    FetchResult,
)

PROVIDER = "fred"
DATASET_RELEASE_DATES = "release.dates"

#: Far-future sentinel FRED accepts for "give me all scheduled dates".
_REALTIME_END = "9999-12-31"


class FredConnector(BaseConnector):
    """Retrieves scheduled release dates for official economic data."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        base_url: str = "https://api.stlouisfed.org",
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
    ) -> None:
        super().__init__(client, max_attempts, backoff_base_seconds)
        if not api_key:
            raise ValueError("FredConnector requires an API key (ALPHALAB_FRED_API_KEY)")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="FredConnector",
            provider=PROVIDER,
            base_url=self._base_url,
            datasets=(DATASET_RELEASE_DATES,),
        )

    async def fetch_release_dates(self, release_id: int, start: date) -> FetchResult:
        """Scheduled dates for one release, from ``start`` onward."""
        url = (
            f"{self._base_url}/fred/release/dates"
            f"?release_id={release_id}"
            f"&realtime_start={start.isoformat()}"
            f"&realtime_end={_REALTIME_END}"
            "&include_release_dates_with_no_data=true"
            "&sort_order=asc&limit=120&file_type=json"
        )
        return await self._get_text(url, DATASET_RELEASE_DATES, params={"api_key": self._api_key})

    async def health(self) -> ConnectorHealth:
        start = time.perf_counter()
        try:
            # CPI (release 10) is the busiest release — a good liveness probe.
            await self.fetch_release_dates(10, date.today())
        except ConnectorError as exc:
            return ConnectorHealth(status="unavailable", error=str(exc))
        return ConnectorHealth(
            status="ok", latency_ms=round((time.perf_counter() - start) * 1000, 2)
        )
