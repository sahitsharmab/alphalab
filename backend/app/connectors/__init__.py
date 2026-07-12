"""Connectors retrieve data from external providers. Nothing more.

Responsibilities: downloading, authentication, retries, rate limits,
returning raw responses. Never: indicator math, AI reasoning, business
logic (ARCHITECTURE.md, Connectors).
"""

from app.connectors.base import BaseConnector, ConnectorHealth, ConnectorMetadata, FetchResult
from app.connectors.federal_reserve import FederalReserveConnector
from app.connectors.nowflation import NowflationConnector
from app.connectors.sec_edgar import SecEdgarConnector
from app.connectors.yahoo import YahooConnector
from app.connectors.yahoo_news import YahooNewsConnector

__all__ = [
    "BaseConnector",
    "ConnectorHealth",
    "ConnectorMetadata",
    "FederalReserveConnector",
    "FetchResult",
    "NowflationConnector",
    "SecEdgarConnector",
    "YahooConnector",
    "YahooNewsConnector",
]
