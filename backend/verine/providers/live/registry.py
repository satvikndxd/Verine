"""Live connector registry."""

from __future__ import annotations

from .cisa import CisaKevConnector
from .nvd import NvdConnector
from .nws import NwsConnector
from .rss import RssConnector
from .sec import SecConnector
from .statuspage import StatuspageConnector

LIVE_CONNECTOR_CLASSES = {
    "statuspage": StatuspageConnector,
    "cisa_kev": CisaKevConnector,
    "nvd": NvdConnector,
    "nws": NwsConnector,
    "sec_edgar": SecConnector,
    "rss": RssConnector,
}


def live_connector(connector_type: str, transport=None):
    cls = LIVE_CONNECTOR_CLASSES.get(connector_type)
    if cls is None:
        raise KeyError(f"Unknown connector type {connector_type!r}")
    return cls(transport=transport)
