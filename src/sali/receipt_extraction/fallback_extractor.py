"""Merchant-agnostic routing between hosted and rendered receipt evidence."""

from __future__ import annotations

from typing import Protocol

if __package__:
    from .errors import HostedReceiptError, ReceiptInspectionFailure
    from .models import ReceiptDocument
    from .rendered_evidence import RenderedReceiptEvidence
else:
    from errors import HostedReceiptError, ReceiptInspectionFailure
    from models import ReceiptDocument
    from rendered_evidence import RenderedReceiptEvidence

RENDERABLE_FAILURE_CODES = frozenset(
    {
        "unreachable",
        "blocked",
        "insufficient_evidence",
    }
)


class _UrlReceiptExtractor(Protocol):
    def extract(self, url: str) -> ReceiptDocument: ...


class _ReceiptRenderer(Protocol):
    def render(self, url: str) -> RenderedReceiptEvidence: ...


class _EvidenceReceiptExtractor(Protocol):
    def extract(self, evidence: RenderedReceiptEvidence) -> ReceiptDocument: ...


class AutoReceiptExtractor:
    """Prefer hosted retrieval and retry eligible failures with rendered evidence."""

    def __init__(
        self,
        *,
        hosted_extractor: _UrlReceiptExtractor,
        renderer: _ReceiptRenderer,
        rendered_extractor: _EvidenceReceiptExtractor,
    ) -> None:
        self._hosted_extractor = hosted_extractor
        self._renderer = renderer
        self._rendered_extractor = rendered_extractor

    def extract(self, url: str) -> ReceiptDocument:
        try:
            return self._hosted_extractor.extract(url)
        except ReceiptInspectionFailure as hosted_failure:
            if hosted_failure.failure_code not in RENDERABLE_FAILURE_CODES:
                raise
            hosted_failure_code = hosted_failure.failure_code
            hosted_failure_reason = hosted_failure.failure_reason
            hosted_failure_diagnostics = hosted_failure.diagnostics

        try:
            evidence = self._renderer.render(url)
            return self._rendered_extractor.extract(evidence)
        except HostedReceiptError as fallback_failure:
            hosted_details = (
                "hosted extraction failed "
                f"({hosted_failure_code}): "
                f"{hosted_failure_reason}"
            )
            if hosted_failure_diagnostics:
                hosted_details += f" [{hosted_failure_diagnostics}]"
            raise HostedReceiptError(
                f"{hosted_details}; rendered fallback failed: {fallback_failure}"
            ) from fallback_failure


__all__ = ["RENDERABLE_FAILURE_CODES", "AutoReceiptExtractor"]
