"""The extraction conversation: page tools, retries, and fail-closed verdicts."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from sali.receipt_extraction.agentic_extractor import AgenticReceiptExtractor
from sali.receipt_extraction.errors import (
    HostedReceiptError,
    ReceiptInspectionFailure,
)
from sali.receipt_extraction.inspection import HostedReceiptInspection
from sali.receipt_extraction.rendered_evidence import RenderedReceiptEvidence

EVIDENCE = RenderedReceiptEvidence(
    requested_url="https://receipt.example/id",
    final_url="https://receipt.example/id",
    page_title="Receipt",
    page_html="<table><tr><td>Total</td><td>10.00</td></tr></table>",
    visible_text="Total 10.00",
    screenshot_data_url=None,
)

RECEIPT = {
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


def _inspection(receipt: dict[str, Any] | None = RECEIPT) -> HostedReceiptInspection:
    return HostedReceiptInspection.model_validate(
        {
            "is_digital_receipt": receipt is not None,
            "failure_code": "none" if receipt is not None else "not_receipt",
            "failure_reason": None if receipt is not None else "a product catalog",
            "receipt": receipt,
        }
    )


def _unbalanced_receipt() -> dict[str, Any]:
    """Item totals that do not add up to the stated receipt total."""
    receipt = {key: value for key, value in RECEIPT.items()}
    receipt["totals"] = {"subtotal": "10.00", "discounts": "0", "total": "99.00"}
    return receipt


class FakeResponses:
    """Replays a scripted sequence of model responses and records requests."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = FakeResponses(responses)


class FakePage:
    """A page whose items only appear after the right control is clicked."""

    def __init__(self) -> None:
        self.clicks: list[str] = []
        self.raw_reads = 0

    def reduced_html(self) -> str:
        return EVIDENCE.page_html

    def raw_html(self) -> str:
        self.raw_reads += 1
        return "<html>raw</html>"

    def click_text(self, text: str) -> str:
        self.clicks.append(text)
        if "details" not in text:
            raise LookupError(f"could not click {text!r}: no such element")
        return "<table><tr><td>Milk</td><td>10.00</td></tr></table>"


def _final(parsed: HostedReceiptInspection) -> SimpleNamespace:
    return SimpleNamespace(output=[], output_parsed=parsed)


def _tool_call(name: str, arguments: str, call_id: str = "call_1") -> SimpleNamespace:
    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=arguments,
        call_id=call_id,
    )


def _calling(*calls: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(output=list(calls), output_parsed=None)


def test_a_single_confident_read_needs_no_tools() -> None:
    client = FakeClient([_final(_inspection())])
    page = FakePage()

    document = AgenticReceiptExtractor(client).extract(EVIDENCE, tools=page)

    assert document.receipt.items[0].name == "Example product"
    assert page.clicks == []
    assert len(client.responses.requests) == 1


def test_the_model_can_click_to_reveal_collapsed_line_items() -> None:
    """The case that motivated the tool loop: items behind a details control."""
    client = FakeClient(
        [
            _calling(_tool_call("click_text", '{"text": "receipt details"}')),
            _final(_inspection()),
        ]
    )
    page = FakePage()

    document = AgenticReceiptExtractor(client).extract(EVIDENCE, tools=page)

    assert page.clicks == ["receipt details"]
    assert document.receipt.totals.total == "10.00"

    followup = client.responses.requests[1]["input"]
    outputs = [item for item in followup if isinstance(item, dict)]
    tool_result = next(
        item for item in outputs if item.get("type") == "function_call_output"
    )
    assert "Milk" in tool_result["output"]


def test_a_failed_click_is_reported_to_the_model_rather_than_ending_extraction() -> (
    None
):
    client = FakeClient(
        [
            _calling(_tool_call("click_text", '{"text": "nonexistent"}')),
            _final(_inspection()),
        ]
    )
    page = FakePage()

    AgenticReceiptExtractor(client).extract(EVIDENCE, tools=page)

    followup = client.responses.requests[1]["input"]
    tool_result = next(
        item
        for item in followup
        if isinstance(item, dict) and item.get("type") == "function_call_output"
    )
    assert tool_result["output"].startswith("error:")


def test_the_model_can_ask_for_unreduced_markup() -> None:
    client = FakeClient(
        [
            _calling(_tool_call("read_raw_html", "{}")),
            _final(_inspection()),
        ]
    )
    page = FakePage()

    AgenticReceiptExtractor(client).extract(EVIDENCE, tools=page)

    assert page.raw_reads == 1


def test_rejected_arithmetic_is_retried_against_the_same_page() -> None:
    """Reconciliation failure is a flaky attempt, not a property of the page."""
    client = FakeClient(
        [
            _final(_inspection(_unbalanced_receipt())),
            _final(_inspection()),
        ]
    )
    page = FakePage()

    document = AgenticReceiptExtractor(client).extract(EVIDENCE, tools=page)

    assert document.receipt.totals.total == "10.00"
    assert len(client.responses.requests) == 2
    assert page.clicks == [], "a retry must not re-render or re-explore the page"


def test_reasoning_effort_escalates_across_attempts() -> None:
    client = FakeClient(
        [
            _final(_inspection(_unbalanced_receipt())),
            _final(_inspection(_unbalanced_receipt())),
            _final(_inspection()),
        ]
    )

    AgenticReceiptExtractor(client).extract(EVIDENCE, tools=FakePage())

    efforts = [request["reasoning"]["effort"] for request in client.responses.requests]
    assert efforts == ["low", "medium", "high"]


def test_persistent_bad_arithmetic_still_fails_closed() -> None:
    client = FakeClient([_final(_inspection(_unbalanced_receipt()))] * 3)

    with pytest.raises(HostedReceiptError) as raised:
        AgenticReceiptExtractor(client).extract(EVIDENCE, tools=FakePage())

    assert "all 3 attempts" in str(raised.value)
    assert len(client.responses.requests) == 3


def test_a_non_receipt_verdict_is_not_retried() -> None:
    client = FakeClient([_final(_inspection(None))])

    with pytest.raises(ReceiptInspectionFailure) as raised:
        AgenticReceiptExtractor(client).extract(EVIDENCE, tools=FakePage())

    assert raised.value.failure_code == "not_receipt"
    assert len(client.responses.requests) == 1


def test_the_tool_budget_is_bounded() -> None:
    """A model that only ever calls tools is forced to answer from what it has."""
    call = _calling(_tool_call("click_text", '{"text": "receipt details"}'))
    client = FakeClient([call, call, _final(_inspection())])
    page = FakePage()

    AgenticReceiptExtractor(client, max_tool_calls=2).extract(EVIDENCE, tools=page)

    assert len(page.clicks) == 2
    assert client.responses.requests[-1].get("tools") is None


def test_tool_calls_past_the_budget_are_ignored_rather_than_obeyed() -> None:
    """Exploration stays bounded even if the model calls tools it wasn't offered."""
    call = _calling(_tool_call("click_text", '{"text": "receipt details"}'))
    client = FakeClient([call, _final(_inspection())])
    page = FakePage()

    document = AgenticReceiptExtractor(client, max_tool_calls=1).extract(
        EVIDENCE, tools=page
    )

    assert len(page.clicks) == 1
    assert document.receipt.totals.total == "10.00"


def test_evidence_carries_html_and_omits_the_screenshot_from_text() -> None:
    client = FakeClient([_final(_inspection())])

    AgenticReceiptExtractor(client).extract(EVIDENCE, tools=None)

    content = client.responses.requests[0]["input"][0]["content"]
    payload = content[0]["text"]
    assert "page_html" in payload
    assert "<table>" in payload
    assert "screenshot_data_url" not in payload


class FakeSession:
    """Stands in for a live page, scripted to fail then succeed."""

    opened = 0

    def __init__(self, outcomes: list[Any]) -> None:
        self._outcomes = outcomes

    def __call__(self, url: str, **_options: Any):
        outcome = self._outcomes[min(FakeSession.opened, len(self._outcomes) - 1)]
        FakeSession.opened += 1
        return _SessionContext(outcome)


class _SessionContext:
    def __init__(self, outcome: Any) -> None:
        self._outcome = outcome

    def __enter__(self):
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self

    def __exit__(self, *_args) -> None:
        return None

    def evidence(self) -> RenderedReceiptEvidence:
        return EVIDENCE

    def reduced_html(self) -> str:
        return EVIDENCE.page_html

    def raw_html(self) -> str:
        return "<html>raw</html>"

    def click_text(self, text: str) -> str:
        return EVIDENCE.page_html


def _browser_extractor(monkeypatch, outcomes, responses):
    from sali.receipt_extraction import agentic_extractor as module

    FakeSession.opened = 0
    monkeypatch.setattr(module, "ReceiptPageSession", FakeSession(outcomes))
    return module.BrowserReceiptExtractor(FakeClient(responses))


def test_a_navigation_timeout_reopens_the_page(monkeypatch) -> None:
    """Observed in the wild: Page.goto exceeded its timeout on a slow load."""
    extractor = _browser_extractor(
        monkeypatch,
        [HostedReceiptError("browser navigation timed out after 30 seconds"), None],
        [_final(_inspection())],
    )

    document = extractor.extract("https://receipt.example/id")

    assert document.receipt.totals.total == "10.00"
    assert FakeSession.opened == 2


def test_a_merchant_error_page_reopens_the_page(monkeypatch) -> None:
    """Observed in the wild: the merchant app rendered 'Failed to deserialize'.

    The model correctly reported `unreachable` for a page that held no receipt,
    but the page itself was fine on a second open.
    """
    from sali.receipt_extraction import agentic_extractor as module

    FakeSession.opened = 0
    monkeypatch.setattr(module, "ReceiptPageSession", FakeSession([None]))

    attempts = {"n": 0}
    original = module.AgenticReceiptExtractor.extract

    def flaky(self, evidence, tools=None):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ReceiptInspectionFailure(
                failure_code="unreachable",
                failure_reason="the page displays only an application error",
            )
        return original(self, evidence, tools)

    monkeypatch.setattr(module.AgenticReceiptExtractor, "extract", flaky)
    extractor = module.BrowserReceiptExtractor(FakeClient([_final(_inspection())]))

    document = extractor.extract("https://receipt.example/id")

    assert FakeSession.opened == 2
    assert document.receipt.totals.total == "10.00"


def test_a_non_receipt_verdict_does_not_reopen_the_page(monkeypatch) -> None:
    from sali.receipt_extraction import agentic_extractor as module

    FakeSession.opened = 0
    monkeypatch.setattr(module, "ReceiptPageSession", FakeSession([None]))
    extractor = module.BrowserReceiptExtractor(FakeClient([_final(_inspection(None))]))

    with pytest.raises(ReceiptInspectionFailure):
        extractor.extract("https://receipt.example/id")

    assert FakeSession.opened == 1, "a definitive verdict must not be retried"
