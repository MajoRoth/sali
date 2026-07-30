"""Domain-specific failures for hosted receipt extraction."""

from typing import Literal


class HostedReceiptError(RuntimeError):
    """A safe failure from the hosted-browsing receipt experiment."""


class InvalidReceiptUrlError(HostedReceiptError):
    """The caller supplied a URL outside the public Digital Receipt policy."""


FailureCode = Literal[
    "none",
    "unreachable",
    "blocked",
    "not_receipt",
    "insufficient_evidence",
    "refused",
]


class ReceiptInspectionFailure(HostedReceiptError):
    """A structured, evidence-based failure returned by an inspection stage."""

    def __init__(
        self,
        *,
        failure_code: FailureCode,
        failure_reason: str,
        diagnostics: str | None = None,
        source: str = "OpenAI",
    ) -> None:
        self.failure_code = failure_code
        self.failure_reason = failure_reason
        self.diagnostics = diagnostics

        message = (
            f"{source} could not verify an extractable Digital Receipt "
            f"({failure_code}): {failure_reason}"
        )
        if diagnostics:
            message += f" [{diagnostics}]"
        super().__init__(message)


class OutputExistsError(FileExistsError):
    """Raised when output replacement was not explicitly authorized."""


__all__ = [
    "FailureCode",
    "HostedReceiptError",
    "InvalidReceiptUrlError",
    "OutputExistsError",
    "ReceiptInspectionFailure",
]
