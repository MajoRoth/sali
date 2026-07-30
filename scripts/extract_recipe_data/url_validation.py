"""Validation and normalization for public receipt URLs."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

if __package__:
    from .configuration import MAX_URL_CHARS
    from .errors import HostedReceiptError
else:
    from configuration import MAX_URL_CHARS
    from errors import HostedReceiptError

UNSAFE_URL_CHARS_RE = re.compile(r"[\x00-\x20\x7f\\]")


class ReceiptUrlValidator:
    """Enforce the public HTTPS policy required by hosted browsing."""

    def __init__(self, max_url_chars: int = MAX_URL_CHARS) -> None:
        self._max_url_chars = max_url_chars

    def validate(self, url: str) -> tuple[str, str]:
        if not isinstance(url, str) or not url or len(url) > self._max_url_chars:
            raise HostedReceiptError("Digital Receipt URL is invalid")
        if url != url.strip() or UNSAFE_URL_CHARS_RE.search(url):
            raise HostedReceiptError("Digital Receipt URL is invalid")

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise HostedReceiptError("Digital Receipt URL is invalid") from exc

        if (
            parsed.scheme.casefold() != "https"
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or "@" in parsed.netloc
            or port not in (None, 443)
        ):
            raise HostedReceiptError("Digital Receipt URL must be public HTTPS")

        normalized_host = self._normalize_hostname(hostname)
        if (
            not normalized_host
            or "." not in normalized_host
            or ".." in normalized_host
            or normalized_host == "localhost"
            or normalized_host.endswith((".localhost", ".local"))
        ):
            raise HostedReceiptError("Digital Receipt URL must use a public hostname")

        normalized_url = urlunsplit(
            (
                "https",
                normalized_host,
                parsed.path or "/",
                parsed.query,
                parsed.fragment,
            )
        )
        return normalized_url, normalized_host

    @staticmethod
    def _normalize_hostname(hostname: str) -> str:
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            try:
                return hostname.rstrip(".").encode("idna").decode("ascii").casefold()
            except UnicodeError as exc:
                raise HostedReceiptError("Digital Receipt URL is invalid") from exc
        raise HostedReceiptError("Digital Receipt URL must use a public hostname")
