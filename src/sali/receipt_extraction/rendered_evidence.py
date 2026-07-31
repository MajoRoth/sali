"""Network policy and the bounded evidence captured from a receipt page."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict


class PublicNetworkPolicy:
    """Reject non-HTTPS and non-public browser network destinations."""

    def __init__(self) -> None:
        self._approved_hosts: set[str] = set()

    def permits(self, url: str) -> bool:
        parsed = urlsplit(url)
        if parsed.scheme in {"about", "blob", "data"}:
            return True
        if parsed.scheme.casefold() != "https" or not parsed.hostname:
            return False

        hostname = parsed.hostname.rstrip(".").casefold()
        if hostname in self._approved_hosts:
            return True
        if self._is_public_hostname(hostname):
            self._approved_hosts.add(hostname)
            return True
        return False

    @staticmethod
    def _is_public_hostname(hostname: str) -> bool:
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            return False

        try:
            addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError):
            return False

        if not addresses:
            return False
        return all(
            ipaddress.ip_address(address[4][0]).is_global for address in addresses
        )


class RenderedReceiptEvidence(BaseModel):
    """Bounded evidence handed to the extraction model for one receipt page.

    `page_html` is the primary evidence and is deliberately not filtered by
    visibility: real receipts keep their line items in collapsed sections that a
    visible-text capture would silently discard.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    requested_url: str
    final_url: str
    page_title: str
    page_html: str
    visible_text: str
    screenshot_data_url: str | None


__all__ = [
    "PublicNetworkPolicy",
    "RenderedReceiptEvidence",
]
