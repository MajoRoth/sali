"""Merchant-agnostic routing between browser and hosted receipt retrieval.

The browser runs first. Hosted retrieval reads from a crawl cache, and receipt
links are almost always short opaque tokens pointing at client-rendered pages,
so hosted browsing routinely cannot fetch them at all — putting it first spent
real latency on a request that was going to fail. It stays as the fallback for
when no local browser is available.
"""

from __future__ import annotations

from typing import Protocol

if __package__:
    from .errors import HostedReceiptError, ReceiptInspectionFailure
    from .models import ReceiptDocument
else:
    from errors import HostedReceiptError, ReceiptInspectionFailure
    from models import ReceiptDocument

#: A verdict of "this is not a receipt" is definitive evidence about the page
#: rather than a retrieval problem, so it is never given a second opinion.
DEFINITIVE_FAILURE_CODES = frozenset({"not_receipt", "refused"})


class _UrlReceiptExtractor(Protocol):
    def extract(self, url: str) -> ReceiptDocument: ...


class AutoReceiptExtractor:
    """Extract with a live browser, falling back to hosted retrieval."""

    def __init__(
        self,
        *,
        browser_extractor: _UrlReceiptExtractor,
        hosted_extractor: _UrlReceiptExtractor,
    ) -> None:
        self._browser_extractor = browser_extractor
        self._hosted_extractor = hosted_extractor

    def extract(self, url: str) -> ReceiptDocument:
        try:
            return self._browser_extractor.extract(url)
        except ReceiptInspectionFailure as browser_failure:
            if browser_failure.failure_code in DEFINITIVE_FAILURE_CODES:
                raise
            first_failure: HostedReceiptError = browser_failure
        except HostedReceiptError as browser_failure:
            first_failure = browser_failure

        try:
            return self._hosted_extractor.extract(url)
        except HostedReceiptError as hosted_failure:
            raise HostedReceiptError(
                f"browser extraction failed: {first_failure}; "
                f"hosted fallback failed: {hosted_failure}"
            ) from hosted_failure


__all__ = ["DEFINITIVE_FAILURE_CODES", "AutoReceiptExtractor"]
