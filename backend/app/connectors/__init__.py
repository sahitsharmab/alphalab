"""Connectors retrieve data from external providers. Nothing more.

Responsibilities: downloading, authentication, retries, rate limits,
returning raw responses. Never: indicator math, AI reasoning, business
logic (ARCHITECTURE.md, Connectors).
"""

from app.connectors.base import BaseConnector, ConnectorHealth, ConnectorMetadata, FetchResult
from app.connectors.nowflation import NowflationConnector

__all__ = [
    "BaseConnector",
    "ConnectorHealth",
    "ConnectorMetadata",
    "FetchResult",
    "NowflationConnector",
]
