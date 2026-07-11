"""Connector for Yahoo Finance daily price history.

Uses the public v8 chart endpoint (verified 2026-07-12): no API key, but a
browser-like User-Agent is required. Yahoo is an unofficial source (see
PROJECT.md source-risk notes); the connector abstraction is the protection
— downstream code only ever sees normalized MarketBar data.
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

PROVIDER = "yahoo"
DATASET_DAILY_BARS = "market.daily_bars"

_CHART_PATH = "/v8/finance/chart"
#: Health probes use a liquid, permanent symbol.
_HEALTH_SYMBOL = "SPY"


class YahooConnector(BaseConnector):
    """Retrieves daily OHLCV history (with adjusted close) per symbol."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = "https://query1.finance.yahoo.com",
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
    ) -> None:
        super().__init__(client, max_attempts, backoff_base_seconds)
        self._base_url = base_url.rstrip("/")

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="YahooConnector",
            provider=PROVIDER,
            base_url=self._base_url,
            datasets=(DATASET_DAILY_BARS,),
        )

    async def fetch_daily_history(self, symbol: str, range_: str = "10y") -> FetchResult:
        """Download up to ``range_`` of daily bars for ``symbol`` (raw JSON)."""
        url = (
            f"{self._base_url}{_CHART_PATH}/{symbol}"
            f"?range={range_}&interval=1d&includeAdjustedClose=true"
        )
        return await self._get_text(url, DATASET_DAILY_BARS)

    async def health(self) -> ConnectorHealth:
        start = time.perf_counter()
        try:
            await self.fetch_daily_history(_HEALTH_SYMBOL, range_="5d")
        except ConnectorError as exc:
            return ConnectorHealth(status="unavailable", error=str(exc))
        return ConnectorHealth(
            status="ok", latency_ms=round((time.perf_counter() - start) * 1000, 2)
        )
