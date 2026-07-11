"""Connector contract shared by every external-provider adapter.

Every connector implements ``metadata()`` and ``health()`` and returns raw
provider responses as ``FetchResult`` values. Retrieval goes through
``_get_text`` which provides retry with exponential backoff for transient
failures.
"""

import asyncio
import hashlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Literal

import httpx
import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)

#: HTTP status codes treated as transient and retried.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class ConnectorMetadata(BaseModel):
    """Static description of a connector."""

    model_config = ConfigDict(frozen=True)

    name: str
    provider: str
    base_url: str
    datasets: tuple[str, ...]


class ConnectorHealth(BaseModel):
    """Result of probing the external provider."""

    status: Literal["ok", "unavailable"]
    latency_ms: float | None = None
    error: str | None = None


class FetchResult(BaseModel):
    """A raw provider response plus retrieval metadata.

    ``retrieved_at`` becomes the ``as_of`` timestamp during storage for
    providers that expose no publication vintage (ADR-004).
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    dataset: str
    url: str
    content: str
    content_hash: str
    retrieved_at: datetime


class ConnectorError(Exception):
    """Raised when a connector exhausts retries or receives a fatal response."""

    def __init__(self, provider: str, url: str, message: str) -> None:
        self.provider = provider
        self.url = url
        super().__init__(f"[{provider}] {url}: {message}")


class BaseConnector(ABC):
    """Base class for all connectors."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
    ) -> None:
        self._client = client
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds

    @abstractmethod
    def metadata(self) -> ConnectorMetadata:
        """Static description of this connector."""

    @abstractmethod
    async def health(self) -> ConnectorHealth:
        """Probe the external provider."""

    async def _get_text(self, url: str, dataset: str) -> FetchResult:
        """GET ``url`` with retries and wrap the body as a ``FetchResult``."""
        provider = self.metadata().provider
        last_error = ""
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.get(url)
            except httpx.TransportError as exc:
                last_error = f"transport error: {exc}"
            else:
                if response.status_code == 200:
                    content = response.text
                    return FetchResult(
                        provider=provider,
                        dataset=dataset,
                        url=url,
                        content=content,
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        retrieved_at=datetime.now(UTC),
                    )
                last_error = f"HTTP {response.status_code}"
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    raise ConnectorError(provider, url, last_error)
            logger.warning(
                "connector_fetch_retry",
                provider=provider,
                url=url,
                attempt=attempt,
                max_attempts=self._max_attempts,
                error=last_error,
            )
            if attempt < self._max_attempts:
                await asyncio.sleep(self._backoff_base_seconds * 2 ** (attempt - 1))
        raise ConnectorError(
            provider, url, f"failed after {self._max_attempts} attempts: {last_error}"
        )
