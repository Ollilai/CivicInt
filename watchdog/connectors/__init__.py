# Connectors package
from watchdog.connectors.base import BaseConnector, DocumentRef
from watchdog.connectors.cloudnc import CloudNCConnector
from watchdog.connectors.dynasty import DynastyConnector
from watchdog.connectors.tweb import TWebConnector
from watchdog.connectors.municipal_website import MunicipalWebsiteConnector

__all__ = [
    "BaseConnector",
    "DocumentRef",
    "CloudNCConnector",
    "DynastyConnector",
    "TWebConnector",
    "MunicipalWebsiteConnector",
]
