"""HTTP contract tests for the Digital Receipt extraction API."""

from fastapi.testclient import TestClient

from sali.api import create_app
from sali.receipt_extraction.errors import (
    HostedReceiptError,
    ReceiptInspectionFailure,
)
from sali.receipt_extraction.image_validation import MAX_RECEIPT_IMAGE_BYTES
from sali.receipt_extraction.models import (
    NormalizedReceipt,
    ReceiptImageTotalDocument,
    validate_and_reconcile,
)


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


def _error_without_id(response) -> dict[str, str]:
    """The error body minus its correlation id, which is random per request."""
    error = dict(response.json()["error"])
    error.pop("request_id", None)
    return error


def _correlation_id(response) -> str:
    """Every failure carries an id that ties it to one server-side log line."""
    return response.json()["error"]["request_id"]


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
    assert _error_without_id(response) == {
        "code": "invalid_url",
        "message": "Use a public HTTPS link to a receipt.",
    }
    assert _correlation_id(response)


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
    assert _error_without_id(response) == {
        "code": "blocked",
        "message": "The receipt link could not be accessed.",
    }
    assert _correlation_id(response)
    assert "private token" not in response.text
    assert "internal web-search diagnostic" not in response.text


def test_extract_reports_service_failures_without_internal_detail() -> None:
    response = TestClient(
        create_app(
            lambda _url: (_ for _ in ()).throw(HostedReceiptError("missing key"))
        )
    ).post("/api/receipts/extract", json={"url": "https://receipt.example/order/1"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "extraction_unavailable"
    assert "missing key" not in response.text


def test_extract_image_returns_the_same_receipt_document_without_persistence() -> None:
    requested = []

    def extract(image):
        requested.append(image)
        return receipt_document()

    response = TestClient(create_app(extract_receipt_image=extract)).post(
        "/api/receipts/extract-image",
        files={"image": ("receipt.jpg", b"\xff\xd8\xff\xdb", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["receipt"]["items"][0]["name"] == "Example product"
    assert requested[0].media_type == "image/jpeg"
    assert requested[0].data == b"\xff\xd8\xff\xdb"
    assert "receipt.jpg" not in response.text


def test_extract_image_total_returns_a_partial_total_without_persistence() -> None:
    requested = []

    def extract(image):
        requested.append(image)
        return ReceiptImageTotalDocument(
            total="268.54",
            currency="ILS",
            warnings=["partial: receipt line items were not extracted"],
        )

    response = TestClient(create_app(extract_receipt_image_total=extract)).post(
        "/api/receipts/extract-image-total",
        files={"image": ("receipt.jpg", b"\xff\xd8\xff\xdb", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": "268.54",
        "currency": "ILS",
        "warnings": ["partial: receipt line items were not extracted"],
    }
    assert requested[0].media_type == "image/jpeg"
    assert "receipt.jpg" not in response.text


def test_extract_image_rejects_an_invalid_or_missing_upload() -> None:
    client = TestClient(create_app())

    missing = client.post("/api/receipts/extract-image")
    unsupported = client.post(
        "/api/receipts/extract-image",
        files={"image": ("receipt.gif", b"GIF89a", "image/gif")},
    )
    mismatched = client.post(
        "/api/receipts/extract-image",
        files={"image": ("receipt.jpg", b"\x89PNG\r\n\x1a\n", "image/jpeg")},
    )
    oversized = client.post(
        "/api/receipts/extract-image",
        files={
            "image": (
                "receipt.jpg",
                b"\xff\xd8\xff" + b"0" * MAX_RECEIPT_IMAGE_BYTES,
                "image/jpeg",
            )
        },
    )

    assert _error_without_id(missing) == {
        "code": "invalid_request",
        "message": "A receipt image is required.",
    }
    for response in (unsupported, mismatched, oversized):
        assert response.status_code == 422
        assert _error_without_id(response) == {
            "code": "invalid_image",
            "message": "Upload one JPEG, PNG, or WEBP receipt image no larger than 10 MiB.",
        }


def test_extract_image_hides_inspection_and_service_details() -> None:
    inspection_failure = ReceiptInspectionFailure(
        failure_code="not_receipt",
        failure_reason="private receipt text was visible",
    )
    failed = TestClient(
        create_app(
            extract_receipt_image=lambda _image: (_ for _ in ()).throw(
                inspection_failure
            )
        )
    ).post(
        "/api/receipts/extract-image",
        files={"image": ("receipt.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    unavailable = TestClient(
        create_app(
            extract_receipt_image=lambda _image: (_ for _ in ()).throw(
                HostedReceiptError("missing key")
            )
        )
    ).post(
        "/api/receipts/extract-image",
        files={"image": ("receipt.webp", b"RIFF\x00\x00\x00\x00WEBP", "image/webp")},
    )

    assert _error_without_id(failed) == {
        "code": "not_receipt",
        "message": "The image did not show a receipt.",
    }
    assert unavailable.status_code == 503
    assert "missing key" not in unavailable.text


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
