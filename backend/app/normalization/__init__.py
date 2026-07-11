"""Normalization layer: converts raw provider payloads into AlphaLab's
internal schemas. Downstream code never sees third-party formats."""


class NormalizationError(Exception):
    """Raised when a raw payload does not match the expected format."""
