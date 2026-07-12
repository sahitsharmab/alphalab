"""Connector for Yahoo Finance per-ticker news RSS (trust 7 — ADR-011).

Aggregated, commentary-heavy coverage keyed to a ticker (verified
2026-07-12). Weak evidence but useful context; the trust level carries
that judgment, not silent filtering.
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

PROVIDER = "yahoo_news"
DATASET_TICKER_NEWS = "news.ticker_headlines"

_HEALTH_SYMBOL = "SPY"


class YahooNewsConnector(BaseConnector):
    """Retrieves per-ticker news headlines from Yahoo Finance RSS."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = "https://feeds.finance.yahoo.com",
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
    ) -> None:
        super().__init__(client, max_attempts, backoff_base_seconds)
        self._base_url = base_url.rstrip("/")

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="YahooNewsConnector",
            provider=PROVIDER,
            base_url=self._base_url,
            datasets=(DATASET_TICKER_NEWS,),
        )

    async def fetch_ticker_news(self, symbol: str) -> FetchResult:
        url = f"{self._base_url}/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        return await self._get_text(url, DATASET_TICKER_NEWS)

    async def health(self) -> ConnectorHealth:
        start = time.perf_counter()
        try:
            await self.fetch_ticker_news(_HEALTH_SYMBOL)
        except ConnectorError as exc:
            return ConnectorHealth(status="unavailable", error=str(exc))
        return ConnectorHealth(
            status="ok", latency_ms=round((time.perf_counter() - start) * 1000, 2)
        )
