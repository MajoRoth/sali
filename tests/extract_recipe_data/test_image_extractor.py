"""Tests for direct visual Receipt Image extraction."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sali.receipt_extraction.errors import HostedReceiptError
from sali.receipt_extraction.image_extractor import (
    RECEIPT_IMAGE_EXTRACTION_PROMPT,
    ReceiptImageExtractor,
    ReceiptImageInspection,
)
from sali.receipt_extraction.models import NormalizedReceipt
from sali.receipt_extraction.receipt_image import ReceiptImage


def valid_receipt() -> NormalizedReceipt:
    return NormalizedReceipt.model_validate(
        {
            "merchant": {
                "name": "Example Market",
                "branch_name": None,
                "branch_number": None,
            },
            "transaction": {
                "receipt_id": None,
                "purchased_at": None,
                "transaction_number": None,
                "type": "purchase",
                "currency": "ILS",
            },
            "totals": {"subtotal": "10.00", "discounts": "0", "total": "10.00"},
            "items": [
                {
                    "position": 1,
                    "code": None,
                    "name": "Example product",
                    "categories": [],
                    "quantity": "1",
                    "unit": "item",
                    "unit_price": "10.00",
                    "gross_total": "10.00",
                    "adjustments": [],
                    "final_total": "10.00",
                }
            ],
        }
    )


def fake_client(inspection: ReceiptImageInspection) -> tuple[object, Mock]:
    parse = Mock(return_value=SimpleNamespace(output_parsed=inspection))
    return SimpleNamespace(responses=SimpleNamespace(parse=parse)), parse


def test_image_extraction_uses_structured_visual_input_without_tools() -> None:
    inspection = ReceiptImageInspection(
        is_receipt_image=True,
        failure_code="none",
        failure_reason=None,
        receipt=valid_receipt(),
    )
    client, parse = fake_client(inspection)

    document = ReceiptImageExtractor(client).extract(
        ReceiptImage(data=b"\xff\xd8\xff\xdb", media_type="image/jpeg")
    )

    assert document.receipt.items[0].name == "Example product"
    request = parse.call_args.kwargs
    assert request["store"] is False
    assert request["text_format"] is ReceiptImageInspection
    assert "tools" not in request
    assert request["input"][0]["content"][1] == {
        "type": "input_image",
        "image_url": "data:image/jpeg;base64,/9j/2w==",
        "detail": "original",
    }


def test_image_extraction_fails_closed_when_the_image_is_not_a_receipt() -> None:
    inspection = ReceiptImageInspection(
        is_receipt_image=False,
        failure_code="not_receipt",
        failure_reason="the image shows a shopping list",
        receipt=None,
    )
    client, _ = fake_client(inspection)

    with pytest.raises(HostedReceiptError, match="could not verify"):
        ReceiptImageExtractor(client).extract(
            ReceiptImage(data=b"\x89PNG\r\n\x1a\n", media_type="image/png")
        )


def test_image_prompt_treats_image_content_as_untrusted_evidence() -> None:
    assert "untrusted evidence" in RECEIPT_IMAGE_EXTRACTION_PROMPT
    assert "Do not browse, search" in RECEIPT_IMAGE_EXTRACTION_PROMPT
    assert "every purchased line item" in RECEIPT_IMAGE_EXTRACTION_PROMPT
