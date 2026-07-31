"""Routing between browser and hosted retrieval, and the network policy."""

from __future__ import annotations

import socket
from unittest.mock import Mock

import pytest

from sali.receipt_extraction.errors import (
    HostedReceiptError,
    ReceiptInspectionFailure,
)
from sali.receipt_extraction.fallback_extractor import AutoReceiptExtractor
from sali.receipt_extraction.models import NormalizedReceipt, validate_and_reconcile
from sali.receipt_extraction.rendered_evidence import PublicNetworkPolicy

URL = "https://receipt.example/id"


def receipt_document():
    receipt = NormalizedReceipt.model_validate(
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
    return validate_and_reconcile(receipt)


def test_browser_runs_first_and_hosted_is_never_called_on_success() -> None:
    """Hosted retrieval cannot open most receipt links, so it must not lead."""
    browser = Mock()
    browser.extract.return_value = receipt_document()
    hosted = Mock()

    document = AutoReceiptExtractor(
        browser_extractor=browser,
        hosted_extractor=hosted,
    ).extract(URL)

    assert document.receipt.items[0].name == "Example product"
    browser.extract.assert_called_once_with(URL)
    hosted.extract.assert_not_called()


def test_hosted_covers_an_unavailable_browser() -> None:
    browser = Mock()
    browser.extract.side_effect = HostedReceiptError(
        "browser extraction is unavailable because Playwright is not installed"
    )
    hosted = Mock()
    hosted.extract.return_value = receipt_document()

    document = AutoReceiptExtractor(
        browser_extractor=browser,
        hosted_extractor=hosted,
    ).extract(URL)

    assert document.receipt.items[0].name == "Example product"
    hosted.extract.assert_called_once_with(URL)


@pytest.mark.parametrize("failure_code", ["unreachable", "blocked"])
def test_retrieval_failures_get_a_hosted_second_opinion(failure_code: str) -> None:
    browser = Mock()
    browser.extract.side_effect = ReceiptInspectionFailure(
        failure_code=failure_code,
        failure_reason="the page could not be read",
    )
    hosted = Mock()
    hosted.extract.return_value = receipt_document()

    document = AutoReceiptExtractor(
        browser_extractor=browser,
        hosted_extractor=hosted,
    ).extract(URL)

    assert document.receipt.totals.total == "10.00"
    hosted.extract.assert_called_once_with(URL)


@pytest.mark.parametrize("failure_code", ["not_receipt", "refused"])
def test_definitive_verdicts_are_not_retried(failure_code: str) -> None:
    """ "This is not a receipt" is evidence about the page, not a fetch problem."""
    browser = Mock()
    browser.extract.side_effect = ReceiptInspectionFailure(
        failure_code=failure_code,
        failure_reason="the page is a product catalog",
    )
    hosted = Mock()

    with pytest.raises(ReceiptInspectionFailure) as raised:
        AutoReceiptExtractor(
            browser_extractor=browser,
            hosted_extractor=hosted,
        ).extract(URL)

    assert raised.value.failure_code == failure_code
    hosted.extract.assert_not_called()


def test_both_failures_are_reported_together() -> None:
    browser = Mock()
    browser.extract.side_effect = ReceiptInspectionFailure(
        failure_code="insufficient_evidence",
        failure_reason="no line items were visible",
    )
    hosted = Mock()
    hosted.extract.side_effect = HostedReceiptError("hosted retrieval returned nothing")

    with pytest.raises(HostedReceiptError) as raised:
        AutoReceiptExtractor(
            browser_extractor=browser,
            hosted_extractor=hosted,
        ).extract(URL)

    message = str(raised.value)
    assert "browser extraction failed" in message
    assert "no line items were visible" in message
    assert "hosted fallback failed" in message
    assert "hosted retrieval returned nothing" in message


def test_network_policy_rejects_private_and_insecure_destinations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def private_address(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", private_address)
    policy = PublicNetworkPolicy()

    assert policy.permits("http://receipt.example/id") is False
    assert policy.permits("https://receipt.example/id") is False
    assert policy.permits("https://127.0.0.1/id") is False
    assert policy.permits("about:blank") is True


def test_network_policy_accepts_public_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def public_address(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", public_address)
    policy = PublicNetworkPolicy()

    assert policy.permits("https://receipt.example/id") is True
