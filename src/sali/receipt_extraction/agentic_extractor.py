"""Extract a receipt by letting the model read and explore a live page.

The model is handed the page's markup, text, and screenshot up front, which is
enough for most receipts in a single turn. When it is not — the items are behind
a control, or markup reduction dropped something — the model calls a tool and
looks again instead of failing.

Extraction is then reconciled locally. Reconciliation rejects arithmetic the
model got wrong, and because that is a flaky per-attempt failure rather than a
property of the page, a rejected attempt is retried against the same captured
evidence with more reasoning effort rather than a fresh render.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from openai import OpenAIError
from pydantic import ValidationError

if __package__:
    from .configuration import (
        MAX_EXTRACTION_ATTEMPTS,
        MAX_OUTPUT_TOKENS,
        MAX_PAGE_TOOL_CALLS,
        MAX_RENDER_ATTEMPTS,
        MODEL,
        PAGE_EXTRACTION_PROMPT,
        REASONING_EFFORT_BY_ATTEMPT,
    )
    from .errors import HostedReceiptError, ReceiptInspectionFailure
    from .inspection import HostedReceiptInspection, ReceiptInspectionVerifier
    from .models import ReceiptDocument, SemanticValidationError, validate_and_reconcile
    from .page_session import ReceiptPageSession
    from .rendered_evidence import RenderedReceiptEvidence
else:
    from configuration import (
        MAX_EXTRACTION_ATTEMPTS,
        MAX_OUTPUT_TOKENS,
        MAX_PAGE_TOOL_CALLS,
        MAX_RENDER_ATTEMPTS,
        MODEL,
        PAGE_EXTRACTION_PROMPT,
        REASONING_EFFORT_BY_ATTEMPT,
    )
    from errors import HostedReceiptError, ReceiptInspectionFailure
    from inspection import HostedReceiptInspection, ReceiptInspectionVerifier
    from models import ReceiptDocument, SemanticValidationError, validate_and_reconcile
    from page_session import ReceiptPageSession
    from rendered_evidence import RenderedReceiptEvidence


class _PageTools(Protocol):
    """The subset of a live page the model is allowed to drive."""

    def reduced_html(self) -> str: ...
    def raw_html(self) -> str: ...
    def click_text(self, text: str) -> str: ...


PAGE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "click_text",
        "description": (
            "Click the first element on the receipt page whose visible text "
            "contains the given string, then return the page's markup as it "
            "looks afterwards. Use this to open a collapsed section that holds "
            "the line items."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Visible text of the control to click.",
                }
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_raw_html",
        "description": (
            "Return the page's unreduced HTML. Use this only when the reduced "
            "markup looks like it dropped receipt content."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]


class AgenticReceiptExtractor:
    """Run the extraction conversation for one receipt page and reconcile it."""

    def __init__(
        self,
        client: Any,
        *,
        max_attempts: int = MAX_EXTRACTION_ATTEMPTS,
        max_tool_calls: int = MAX_PAGE_TOOL_CALLS,
    ) -> None:
        self._client = client
        self._max_attempts = max(1, max_attempts)
        self._max_tool_calls = max(0, max_tool_calls)

    def extract(
        self,
        evidence: RenderedReceiptEvidence,
        tools: _PageTools | None = None,
    ) -> ReceiptDocument:
        """Extract and reconcile one receipt, retrying rejected arithmetic."""
        reconciliation_failure: SemanticValidationError | None = None

        for attempt in range(self._max_attempts):
            inspection = self._inspect(evidence, tools, attempt=attempt)
            ReceiptInspectionVerifier.ensure_verified(
                inspection,
                source="Page extraction",
            )
            try:
                return validate_and_reconcile(inspection.receipt)
            except SemanticValidationError as exc:
                # A different sample of the same page may reconcile, so keep the
                # failure and try again rather than ending the request here.
                reconciliation_failure = exc

        raise HostedReceiptError(
            f"the receipt failed local reconciliation on all {self._max_attempts} "
            f"attempts: {reconciliation_failure}"
        ) from reconciliation_failure

    def _inspect(
        self,
        evidence: RenderedReceiptEvidence,
        tools: _PageTools | None,
        *,
        attempt: int,
    ) -> HostedReceiptInspection:
        conversation: list[Any] = [
            {"role": "user", "content": self._opening_content(evidence)}
        ]
        effort = REASONING_EFFORT_BY_ATTEMPT[
            min(attempt, len(REASONING_EFFORT_BY_ATTEMPT) - 1)
        ]

        executed = 0
        while True:
            # Once the budget is spent, tools stop being offered and any call
            # the model makes anyway is ignored, so exploration is bounded no
            # matter how the model behaves.
            allow_tools = tools is not None and executed < self._max_tool_calls
            response = self._request(
                conversation,
                effort=effort,
                allow_tools=allow_tools,
            )
            calls = (
                [
                    item
                    for item in getattr(response, "output", []) or []
                    if getattr(item, "type", None) == "function_call"
                ]
                if allow_tools
                else []
            )
            if not calls:
                return ReceiptInspectionVerifier.parse(
                    response.output_parsed,
                    evidence_kind="page",
                )
            # Every call in a response must be answered or the next request is
            # malformed, so a response that overruns the budget is still served.
            for call in calls:
                conversation.append(call)
                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": self._run_tool(tools, call),
                    }
                )
                executed += 1

    @staticmethod
    def _run_tool(tools: _PageTools, call: Any) -> str:
        name = getattr(call, "name", "")
        try:
            arguments = json.loads(getattr(call, "arguments", "") or "{}")
        except json.JSONDecodeError:
            return "error: arguments were not valid JSON"

        try:
            if name == "click_text":
                return tools.click_text(str(arguments.get("text", "")))
            if name == "read_raw_html":
                return tools.raw_html()
        except (LookupError, ValueError) as exc:
            return f"error: {exc}"
        except Exception as exc:  # noqa: BLE001 - a tool must not end extraction
            return f"error: the page could not complete that action ({exc})"
        return f"error: unknown tool {name!r}"

    @staticmethod
    def _opening_content(evidence: RenderedReceiptEvidence) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": json.dumps(
                    evidence.model_dump(
                        mode="json",
                        exclude={"screenshot_data_url"},
                    ),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            }
        ]
        if evidence.screenshot_data_url is not None:
            content.append(
                {
                    "type": "input_image",
                    "image_url": evidence.screenshot_data_url,
                    "detail": "original",
                }
            )
        return content

    def _request(
        self,
        conversation: list[Any],
        *,
        effort: str,
        allow_tools: bool = True,
    ) -> Any:
        request: dict[str, Any] = {
            "model": MODEL,
            "reasoning": {"effort": effort},
            "store": False,
            "instructions": PAGE_EXTRACTION_PROMPT,
            "input": conversation,
            "text_format": HostedReceiptInspection,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }
        if allow_tools and self._max_tool_calls:
            request["tools"] = PAGE_TOOLS

        try:
            return self._client.responses.parse(**request)
        except ValidationError as exc:
            raise HostedReceiptError(
                "OpenAI returned an invalid page receipt inspection"
            ) from exc
        except OpenAIError as exc:
            raise HostedReceiptError("the OpenAI page receipt request failed") from exc


#: Verdicts that describe the page not having loaded rather than not being a
#: receipt. A merchant app that served an error, or a navigation that timed out,
#: is worth opening again; "this is a product catalog" is not.
RENDER_RETRYABLE_CODES = frozenset({"unreachable", "blocked", "insufficient_evidence"})


class BrowserReceiptExtractor:
    """Open one receipt URL in a live browser and extract it agentically."""

    def __init__(
        self,
        client: Any,
        *,
        max_render_attempts: int = MAX_RENDER_ATTEMPTS,
        **session_options: Any,
    ) -> None:
        self._extractor = AgenticReceiptExtractor(client)
        self._max_render_attempts = max(1, max_render_attempts)
        self._session_options = session_options

    def extract(self, url: str) -> ReceiptDocument:
        """Extract one receipt, reopening the page when the render itself fails.

        Navigation timeouts and merchant apps that transiently serve an error
        page are both fixed by opening the page again, and neither is visible to
        the model-call retries inside `AgenticReceiptExtractor`.
        """
        last_failure: HostedReceiptError = HostedReceiptError(
            "the receipt page could not be opened"
        )

        for _ in range(self._max_render_attempts):
            try:
                with ReceiptPageSession(url, **self._session_options) as session:
                    return self._extractor.extract(session.evidence(), tools=session)
            except ReceiptInspectionFailure as failure:
                if failure.failure_code not in RENDER_RETRYABLE_CODES:
                    raise
                last_failure = failure
            except HostedReceiptError as failure:
                last_failure = failure

        raise last_failure


__all__ = [
    "PAGE_TOOLS",
    "AgenticReceiptExtractor",
    "BrowserReceiptExtractor",
    "ReceiptInspectionFailure",
]
