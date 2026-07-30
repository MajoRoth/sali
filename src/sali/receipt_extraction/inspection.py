"""Structured receipt inspection and verification shared by extraction paths."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

if __package__:
    from .errors import FailureCode, HostedReceiptError, ReceiptInspectionFailure
    from .models import NormalizedReceipt
else:
    from errors import FailureCode, HostedReceiptError, ReceiptInspectionFailure
    from models import NormalizedReceipt


class HostedReceiptInspection(BaseModel):
    """Structured intermediate result before local receipt reconciliation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_digital_receipt: bool
    failure_code: FailureCode
    failure_reason: str | None
    receipt: NormalizedReceipt | None


class ReceiptInspectionVerifier:
    """Validate one structured inspection and fail closed when it is unverified."""

    @staticmethod
    def parse(value: Any, *, evidence_kind: str) -> HostedReceiptInspection:
        if value is None:
            raise HostedReceiptError(
                f"OpenAI did not return a {evidence_kind} receipt inspection"
            )
        if isinstance(value, HostedReceiptInspection):
            return value
        try:
            return HostedReceiptInspection.model_validate(value)
        except ValidationError as exc:
            raise HostedReceiptError(
                f"OpenAI returned an invalid {evidence_kind} receipt inspection"
            ) from exc

    @staticmethod
    def ensure_verified(
        inspection: HostedReceiptInspection,
        *,
        source: str,
        diagnostics: str | None = None,
    ) -> None:
        if (
            not inspection.is_digital_receipt
            or inspection.failure_code != "none"
            or inspection.failure_reason is not None
            or inspection.receipt is None
        ):
            raise ReceiptInspectionFailure(
                failure_code=inspection.failure_code,
                failure_reason=(
                    inspection.failure_reason
                    or "the model returned no specific failure reason"
                ),
                diagnostics=diagnostics,
                source=source,
            )


__all__ = ["HostedReceiptInspection", "ReceiptInspectionVerifier"]
