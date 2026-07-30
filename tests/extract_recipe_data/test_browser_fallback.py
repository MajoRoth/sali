"""Tests for generic browser-rendered receipt fallback."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.extract_recipe_data.errors import (
    HostedReceiptError,
    ReceiptInspectionFailure,
)
from scripts.extract_recipe_data.fallback_extractor import AutoReceiptExtractor
from scripts.extract_recipe_data.hosted_extractor import HostedReceiptInspection
from scripts.extract_recipe_data.models import NormalizedReceipt, validate_and_reconcile
from scripts.extract_recipe_data.rendered_evidence import (
    BrowserReceiptRenderer,
    PublicNetworkPolicy,
    RenderedEvidenceReceiptExtractor,
    RenderedPageSnapshot,
    RenderedReceiptEvidence,
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
            "totals": {
                "subtotal": "10.00",
                "discounts": "0",
                "total": "10.00",
            },
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


def test_auto_extractor_falls_back_for_hosted_retrieval_failure() -> None:
    hosted = Mock()
    hosted.extract.side_effect = ReceiptInspectionFailure(
        failure_code="unreachable",
        failure_reason="Failed to fetch the page: Cache miss.",
        diagnostics="web_search_call status=completed action=open_page",
    )
    evidence = RenderedReceiptEvidence(
        requested_url="https://receipt.example/id",
        final_url="https://receipt.example/id",
        page_title="Receipt",
        visible_text="Example product 10.00\nTotal 10.00",
        screenshot_data_url=None,
    )
    renderer = Mock()
    renderer.render.return_value = evidence
    rendered_extractor = Mock()
    rendered_extractor.extract.return_value = receipt_document()

    document = AutoReceiptExtractor(
        hosted_extractor=hosted,
        renderer=renderer,
        rendered_extractor=rendered_extractor,
    ).extract("https://receipt.example/id")

    assert document.receipt.items[0].name == "Example product"
    renderer.render.assert_called_once_with("https://receipt.example/id")
    rendered_extractor.extract.assert_called_once_with(evidence)


def test_auto_extractor_does_not_render_after_hosted_success() -> None:
    document = receipt_document()
    hosted = Mock()
    hosted.extract.return_value = document
    renderer = Mock()
    rendered_extractor = Mock()

    result = AutoReceiptExtractor(
        hosted_extractor=hosted,
        renderer=renderer,
        rendered_extractor=rendered_extractor,
    ).extract("https://receipt.example/id")

    assert result is document
    renderer.render.assert_not_called()
    rendered_extractor.extract.assert_not_called()


@pytest.mark.parametrize("failure_code", ["not_receipt", "refused"])
def test_auto_extractor_does_not_render_non_retrieval_failures(
    failure_code: str,
) -> None:
    failure = ReceiptInspectionFailure(
        failure_code=failure_code,
        failure_reason="The page is not purchase evidence.",
    )
    hosted = Mock()
    hosted.extract.side_effect = failure
    renderer = Mock()
    rendered_extractor = Mock()

    with pytest.raises(ReceiptInspectionFailure) as raised:
        AutoReceiptExtractor(
            hosted_extractor=hosted,
            renderer=renderer,
            rendered_extractor=rendered_extractor,
        ).extract("https://receipt.example/id")

    assert raised.value is failure
    renderer.render.assert_not_called()
    rendered_extractor.extract.assert_not_called()


def test_browser_renderer_is_generic_and_rejects_cross_host_redirects() -> None:
    driver = Mock()
    driver.capture.return_value = RenderedPageSnapshot(
        final_url="https://other.example/receipt",
        page_title="Receipt",
        visible_text="Example product 10.00",
        screenshot_png=None,
    )
    renderer = BrowserReceiptRenderer(driver=driver)

    with pytest.raises(HostedReceiptError, match="different hostname"):
        renderer.render("https://receipt.example/id")

    driver.capture.assert_called_once_with(
        "https://receipt.example/id",
        allowed_hostname="receipt.example",
    )


def test_browser_renderer_bounds_text_and_drops_oversized_screenshot() -> None:
    driver = Mock()
    driver.capture.return_value = RenderedPageSnapshot(
        final_url="https://receipt.example/id",
        page_title=" Receipt ",
        visible_text="  123456789  ",
        screenshot_png=b"too-large",
    )

    evidence = BrowserReceiptRenderer(
        driver=driver,
        max_text_chars=5,
        max_screenshot_bytes=3,
    ).render("https://receipt.example/id")

    assert evidence.page_title == "Receipt"
    assert evidence.visible_text == "12345"
    assert evidence.screenshot_data_url is None


def test_browser_network_policy_rejects_private_and_insecure_destinations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def private_address(*_args, **_kwargs):
        return [(None, None, None, None, ("127.0.0.1", 443))]

    monkeypatch.setattr(
        "scripts.extract_recipe_data.rendered_evidence.socket.getaddrinfo",
        private_address,
    )
    policy = PublicNetworkPolicy()

    assert not policy.permits("http://public.example/receipt")
    assert not policy.permits("file:///etc/passwd")
    assert not policy.permits("https://private.example/receipt")
    assert not policy.permits("https://127.0.0.1/receipt")


def test_browser_network_policy_accepts_public_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def public_address(*_args, **_kwargs):
        return [(None, None, None, None, ("93.184.216.34", 443))]

    monkeypatch.setattr(
        "scripts.extract_recipe_data.rendered_evidence.socket.getaddrinfo",
        public_address,
    )

    assert PublicNetworkPolicy().permits("https://receipt.example/id")


def test_rendered_evidence_request_uses_text_and_screenshot_without_web_search() -> None:
    inspection = HostedReceiptInspection(
        is_digital_receipt=True,
        failure_code="none",
        failure_reason=None,
        receipt=receipt_document().receipt,
    )
    parse = Mock(
        return_value=SimpleNamespace(
            output_parsed=inspection,
            output=[],
        )
    )
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    evidence = RenderedReceiptEvidence(
        requested_url="https://receipt.example/id",
        final_url="https://receipt.example/id",
        page_title="Receipt",
        visible_text="Example product 10.00\nTotal 10.00",
        screenshot_data_url="data:image/png;base64,c25hcHNob3Q=",
    )

    document = RenderedEvidenceReceiptExtractor(client).extract(evidence)

    assert document.receipt.totals.total == "10.00"
    request = parse.call_args.kwargs
    assert "tools" not in request
    assert request["text_format"] is HostedReceiptInspection
    content = request["input"][0]["content"]
    assert content[0]["type"] == "input_text"
    assert "Example product 10.00" in content[0]["text"]
    assert content[1] == {
        "type": "input_image",
        "image_url": "data:image/png;base64,c25hcHNob3Q=",
        "detail": "original",
    }
    assert "untrusted data" in request["instructions"]
    assert "Do not browse" in request["instructions"]


def test_auto_extractor_reports_both_failures() -> None:
    hosted = Mock()
    hosted.extract.side_effect = ReceiptInspectionFailure(
        failure_code="blocked",
        failure_reason="robots policy denied hosted retrieval",
        diagnostics="web_search_call status=completed action=open_page",
    )
    renderer = Mock()
    renderer.render.side_effect = HostedReceiptError(
        "browser navigation timed out after 30 seconds"
    )

    with pytest.raises(
        HostedReceiptError,
        match=(
            "hosted extraction failed \\(blocked\\).*"
            "web_search_call status=completed.*"
            "rendered fallback failed: browser navigation timed out"
        ),
    ):
        AutoReceiptExtractor(
            hosted_extractor=hosted,
            renderer=renderer,
            rendered_extractor=Mock(),
        ).extract("https://receipt.example/id")
