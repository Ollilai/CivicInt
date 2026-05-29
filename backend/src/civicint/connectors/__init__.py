"""Connector registry for municipal document discovery platforms."""

from civicint.connectors.base import BaseConnector, DocumentRef, RateLimiter, is_safe_url
from civicint.connectors.cloudnc import CloudNCConnector
from civicint.connectors.dynasty import DynastyConnector
from civicint.connectors.tweb import TWebConnector

CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "cloudnc": CloudNCConnector,
    "dynasty": DynastyConnector,
    "tweb": TWebConnector,
}


def get_connector(
    platform: str, source_id: int, base_url: str, config: dict | None = None
) -> BaseConnector:
    """Instantiate a connector by platform name.

    Args:
        platform: Platform identifier (cloudnc, dynasty, tweb).
        source_id: Database source row ID.
        base_url: Root URL for the municipality site.
        config: Optional extra configuration dict.

    Returns:
        An initialised connector instance.

    Raises:
        ValueError: If the platform is not registered.
    """
    connector_class = CONNECTOR_REGISTRY.get(platform)
    if not connector_class:
        raise ValueError(
            f"Unknown platform: {platform}. Available: {', '.join(CONNECTOR_REGISTRY)}"
        )
    return connector_class(source_id=source_id, base_url=base_url, config=config)


__all__ = [
    "CONNECTOR_REGISTRY",
    "BaseConnector",
    "CloudNCConnector",
    "DocumentRef",
    "DynastyConnector",
    "RateLimiter",
    "TWebConnector",
    "get_connector",
    "is_safe_url",
]
