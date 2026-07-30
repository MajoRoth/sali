"""HTTP contract tests for the Digital Receipt extraction API."""

from fastapi.testclient import TestClient

from sali.api import create_app
from sali.receipt_extraction.errors import (
    HostedReceiptError,
    ReceiptInspectionFailure,
)
from sali.receipt_extraction.models import NormalizedReceipt, validate_and_reconcile


def receipt_document():
    receipt = NormalizedReceipt.model_validate(
        {
            "merchant": {"name": "Example Market", "branch_name": None, "branch_number": None},
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
                    "code": "0123",
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


def test_extract_returns_a_reconciled_receipt_document_without_persistence() -> None:
    requested: list[str] = []

    def extract(url: str):
        requested.append(url)
        return receipt_document()

    response = TestClient(create_app(extract)).post(
        "/api/receipts/extract",
        json={"url": "https://receipt.example/order/1"},
    )

    assert response.status_code == 200
    assert response.json()["receipt"]["items"][0]["name"] == "Example product"
    assert requested == ["https://receipt.example/order/1"]
    assert "source_url" not in response.text


def test_extract_rejects_an_invalid_url_with_a_safe_contract_error() -> None:
    response = TestClient(create_app()).post(
        "/api/receipts/extract",
        json={"url": "http://localhost/receipt"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "invalid_url", "message": "Use a public HTTPS link to a receipt."}
    }


def test_extract_hides_receipt_and_diagnostic_details_on_verification_failure() -> None:
    def extract(_url: str):
        raise ReceiptInspectionFailure(
            failure_code="blocked",
            failure_reason="receipt data with a private token was visible",
            diagnostics="internal web-search diagnostic",
        )

    response = TestClient(create_app(extract)).post(
        "/api/receipts/extract",
        json={"url": "https://receipt.example/order/1"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "blocked", "message": "The receipt link could not be accessed."}
    }


def test_extract_reports_service_failures_without_internal_detail() -> None:
    response = TestClient(
        create_app(lambda _url: (_ for _ in ()).throw(HostedReceiptError("missing key")))
    ).post("/api/receipts/extract", json={"url": "https://receipt.example/order/1"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "extraction_unavailable"
    assert "missing key" not in response.text


def test_api_allows_the_local_vite_origin_only() -> None:
    response = TestClient(create_app(lambda _url: receipt_document())).options(
        "/api/receipts/extract",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
