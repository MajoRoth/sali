"""Tests for extracting a verified total from a partial Receipt Image."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sali.receipt_extraction.errors import HostedReceiptError
from sali.receipt_extraction.image_total_extractor import (
    RECEIPT_IMAGE_TOTAL_EXTRACTION_PROMPT,
    ReceiptImageTotalExtractor,
    ReceiptImageTotalInspection,
)
from sali.receipt_extraction.receipt_image import ReceiptImage


def fake_client(inspection: ReceiptImageTotalInspection) -> tuple[object, Mock]:
    parse = Mock(return_value=SimpleNamespace(output_parsed=inspection))
    return SimpleNamespace(responses=SimpleNamespace(parse=parse)), parse


def test_total_extraction_accepts_a_receipt_without_readable_line_items() -> None:
    inspection = ReceiptImageTotalInspection.model_validate(
        {
            "is_receipt_image": True,
            "failure_code": "none",
            "failure_reason": None,
            "total": {"total": "268.54", "currency": "ILS"},
        }
    )
    client, parse = fake_client(inspection)

    document = ReceiptImageTotalExtractor(client).extract(
        ReceiptImage(data=b"\xff\xd8\xff\xdb", media_type="image/jpeg")
    )

    assert document.total == "268.54"
    assert document.currency == "ILS"
    assert document.warnings == ["partial: receipt line items were not extracted"]
    request = parse.call_args.kwargs
    assert request["store"] is False
    assert request["text_format"] is ReceiptImageTotalInspection
    assert "tools" not in request
    assert request["input"][0]["content"][1]["detail"] == "original"


def test_total_extraction_fails_when_the_final_total_is_unreadable() -> None:
    inspection = ReceiptImageTotalInspection.model_validate(
        {
            "is_receipt_image": False,
            "failure_code": "insufficient_evidence",
            "failure_reason": "the final paid total is blurred",
            "total": None,
        }
    )
    client, _ = fake_client(inspection)

    with pytest.raises(HostedReceiptError, match="could not verify"):
        ReceiptImageTotalExtractor(client).extract(
            ReceiptImage(data=b"\x89PNG\r\n\x1a\n", media_type="image/png")
        )


def test_total_prompt_does_not_require_item_rows() -> None:
    assert "does not need readable item rows" in RECEIPT_IMAGE_TOTAL_EXTRACTION_PROMPT
    assert "Do not infer a cart" in RECEIPT_IMAGE_TOTAL_EXTRACTION_PROMPT
