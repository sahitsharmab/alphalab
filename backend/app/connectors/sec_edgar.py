"""Connector for SEC EDGAR (Tier 1 evidence, trust 10 — ADR-011).

Uses only official endpoints (verified 2026-07-12):

* ``https://www.sec.gov/files/company_tickers.json`` — ticker → CIK map
* ``https://data.sec.gov/submissions/CIK{cik}.json`` — filing history

SEC fair-access policy: declare a User-Agent with contact information and
stay under 10 requests/second. Our per-workspace usage is two requests.
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

PROVIDER = "sec_edgar"
DATASET_SUBMISSIONS = "filings.submissions"
DATASET_TICKER_MAP = "reference.company_tickers"

#: Health probes use a permanent, high-volume filer (Micron's CIK works,
#: but Apple's is the conventional canary).
_HEALTH_CIK = "0000320193"


class SecEdgarConnector(BaseConnector):
    """Retrieves company filing histories from SEC EDGAR."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        data_base_url: str = "https://data.sec.gov",
        www_base_url: str = "https://www.sec.gov",
        user_agent: str = "AlphaLab/0.1 (personal research)",
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
    ) -> None:
        super().__init__(client, max_attempts, backoff_base_seconds)
        self._data_base_url = data_base_url.rstrip("/")
        self._www_base_url = www_base_url.rstrip("/")
        self._user_agent = user_agent

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="SecEdgarConnector",
            provider=PROVIDER,
            base_url=self._data_base_url,
            datasets=(DATASET_SUBMISSIONS, DATASET_TICKER_MAP),
        )

    async def fetch_ticker_map(self) -> FetchResult:
        """Download the official ticker → CIK mapping."""
        return await self._get_text(
            f"{self._www_base_url}/files/company_tickers.json",
            DATASET_TICKER_MAP,
            headers={"User-Agent": self._user_agent},
        )

    async def fetch_submissions(self, cik: str) -> FetchResult:
        """Download the filing history for a zero-padded 10-digit CIK."""
        return await self._get_text(
            f"{self._data_base_url}/submissions/CIK{cik}.json",
            DATASET_SUBMISSIONS,
            headers={"User-Agent": self._user_agent},
        )

    async def health(self) -> ConnectorHealth:
        start = time.perf_counter()
        try:
            await self.fetch_submissions(_HEALTH_CIK)
        except ConnectorError as exc:
            return ConnectorHealth(status="unavailable", error=str(exc))
        return ConnectorHealth(
            status="ok", latency_ms=round((time.perf_counter() - start) * 1000, 2)
        )
