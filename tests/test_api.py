"""HTTP contract tests for the Digital Receipt extraction API."""

from fastapi.testclient import TestClient

from sali.api import create_app
from sali.cart_comparison.catalog import CatalogUnavailableError
from sali.cart_comparison.models import CartComparison, StoreCart
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


def cart_comparison(store_total: str = "15.00") -> CartComparison:
    return CartComparison(
        currency="ILS",
        receipt_total="10.00",
        matched=[],
        unmatched=[],
        complete_carts=[
            StoreCart(
                store_id="s1",
                store_name="נס ציונה",
                city="נס ציונה",
                address="החרש 9",
                chain_id="7290875100001",
                chain_name="שופרסל",
                complete=True,
                priced_items=1,
                total_items=1,
                total=store_total,
                missing=[],
                chain_level_estimate=False,
            )
        ],
        partial_carts=[],
        warnings=[],
    )


def test_compare_ranks_stores_for_an_already_extracted_receipt() -> None:
    seen: list[tuple[str, str | None]] = []

    def compare(document, city):
        seen.append((document.receipt.items[0].name, city))
        return cart_comparison()

    response = TestClient(create_app(compare_cart=compare)).post(
        "/api/carts/compare",
        json={
            "document": receipt_document().model_dump(mode="json"),
            "city": "נס ציונה",
        },
    )

    assert response.status_code == 200
    assert response.json()["complete_carts"][0]["total"] == "15.00"
    assert seen == [("Example product", "נס ציונה")]


def test_compare_url_extracts_then_prices_the_cart_in_one_call() -> None:
    extracted: list[str] = []

    def extract(url: str):
        extracted.append(url)
        return receipt_document()

    response = TestClient(
        create_app(extract, compare_cart=lambda _document, _city: cart_comparison())
    ).post(
        "/api/carts/compare-url",
        json={"url": "https://receipt.example/order/1"},
    )

    assert response.status_code == 200
    assert extracted == ["https://receipt.example/order/1"]
    assert response.json()["complete_carts"][0]["chain_name"] == "שופרסל"


def test_compare_url_rejects_an_untrusted_link_before_extracting_it() -> None:
    def extract(_url: str):
        raise AssertionError("a rejected URL must never be opened")

    response = TestClient(create_app(extract)).post(
        "/api/carts/compare-url",
        json={"url": "http://localhost/receipt"},
    )

    assert response.status_code == 422
    assert _error_without_id(response) == {
        "code": "invalid_url",
        "message": "Use a public HTTPS link to a receipt.",
    }


def test_compare_image_extracts_the_upload_then_prices_the_cart() -> None:
    response = TestClient(
        create_app(
            extract_receipt_image=lambda _image: receipt_document(),
            compare_cart=lambda _document, city: cart_comparison(
                "20.00" if city == "חיפה" else "15.00"
            ),
        )
    ).post(
        "/api/carts/compare-image",
        files={"image": ("receipt.jpg", b"\xff\xd8\xff" + b"0" * 64, "image/jpeg")},
        data={"city": "חיפה"},
    )

    assert response.status_code == 200
    assert response.json()["complete_carts"][0]["total"] == "20.00"


def test_compare_reports_an_unreachable_price_database_without_internal_detail() -> (
    None
):
    def compare(_document, _city):
        raise CatalogUnavailableError(
            "http://34.165.235.189:8000 refused the connection"
        )

    response = TestClient(create_app(compare_cart=compare)).post(
        "/api/carts/compare",
        json={"document": receipt_document().model_dump(mode="json")},
    )

    assert response.status_code == 503
    assert _error_without_id(response) == {
        "code": "price_database_unavailable",
        "message": "The price database is temporarily unavailable. Please try again.",
    }
    assert "34.165.235.189" not in response.text
    assert _correlation_id(response)


def test_compare_rejects_a_body_without_a_receipt_document() -> None:
    response = TestClient(create_app()).post("/api/carts/compare", json={})

    assert response.status_code == 422
    assert _error_without_id(response) == {
        "code": "invalid_request",
        "message": "A Receipt Document is required.",
    }


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
