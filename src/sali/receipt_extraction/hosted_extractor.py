"""OpenAI-hosted browsing implementation for receipt extraction."""

from __future__ import annotations

import json
from typing import Any, Protocol

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

if __package__:
    from .configuration import (
        HOSTED_EXTRACTION_PROMPT,
        MAX_OUTPUT_TOKENS,
        MODEL,
    )
    from .credentials import ApiKeyProvider
    from .errors import HostedReceiptError
    from .inspection import HostedReceiptInspection, ReceiptInspectionVerifier
    from .models import (
        ReceiptDocument,
        SemanticValidationError,
        validate_and_reconcile,
    )
    from .url_validation import ReceiptUrlValidator
else:
    from configuration import HOSTED_EXTRACTION_PROMPT, MAX_OUTPUT_TOKENS, MODEL
    from credentials import ApiKeyProvider
    from errors import HostedReceiptError
    from inspection import HostedReceiptInspection, ReceiptInspectionVerifier
    from models import (
        ReceiptDocument,
        SemanticValidationError,
        validate_and_reconcile,
    )
    from url_validation import ReceiptUrlValidator


class _ResponsesAPI(Protocol):
    def parse(self, **kwargs: Any) -> Any: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesAPI


class HostedReceiptExtractor:
    """Extract and reconcile a receipt using an initialized OpenAI client."""

    def __init__(
        self,
        client: _OpenAIClient,
        url_validator: ReceiptUrlValidator | None = None,
    ) -> None:
        self._client = client
        self._url_validator = url_validator or ReceiptUrlValidator()

    def extract(self, url: str) -> ReceiptDocument:
        normalized_url, hostname = self._url_validator.validate(url)
        response = self._request_inspection(normalized_url, hostname)
        inspection = self._parse_inspection(response.output_parsed)
        self._ensure_verified(inspection, response)

        try:
            return validate_and_reconcile(inspection.receipt)
        except SemanticValidationError as exc:
            raise HostedReceiptError(
                "the hosted receipt failed local reconciliation"
            ) from exc

    def _request_inspection(self, normalized_url: str, hostname: str) -> Any:
        try:
            return self._client.responses.parse(
                model=MODEL,
                reasoning={"effort": "low"},
                store=False,
                tools=[
                    {
                        "type": "web_search",
                        "external_web_access": True,
                        "search_context_size": "low",
                        "filters": {"allowed_domains": [hostname]},
                    }
                ],
                tool_choice="required",
                instructions=HOSTED_EXTRACTION_PROMPT,
                input=json.dumps(
                    {"digital_receipt_url": normalized_url},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                text_format=HostedReceiptInspection,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
        except ValidationError as exc:
            raise HostedReceiptError(
                "OpenAI returned an invalid hosted receipt inspection"
            ) from exc
        except OpenAIError as exc:
            raise HostedReceiptError(
                "the OpenAI hosted receipt request failed"
            ) from exc

    @staticmethod
    def _parse_inspection(value: Any) -> HostedReceiptInspection:
        return ReceiptInspectionVerifier.parse(value, evidence_kind="hosted")

    @classmethod
    def _ensure_verified(
        cls,
        inspection: HostedReceiptInspection,
        response: Any,
    ) -> None:
        tool_diagnostics = cls._web_search_diagnostics(response)
        ReceiptInspectionVerifier.ensure_verified(
            inspection,
            source="OpenAI",
            diagnostics=tool_diagnostics or None,
        )

    @staticmethod
    def _web_search_diagnostics(response: Any) -> str:
        diagnostics: list[str] = []
        for item in getattr(response, "output", []):
            if getattr(item, "type", None) != "web_search_call":
                continue
            status = getattr(item, "status", "unknown")
            action = getattr(getattr(item, "action", None), "type", "unknown")
            diagnostics.append(f"web_search_call status={status} action={action}")
        return "; ".join(diagnostics)


class OpenAIReceiptExtractor:
    """Create the API client and run hosted extraction with browser fallback."""

    def __init__(self, api_key_provider: ApiKeyProvider | None = None) -> None:
        self._api_key_provider = api_key_provider or ApiKeyProvider()

    def extract(self, url: str) -> ReceiptDocument:
        if __package__:
            from .agentic_extractor import BrowserReceiptExtractor
            from .fallback_extractor import AutoReceiptExtractor
        else:
            from agentic_extractor import BrowserReceiptExtractor
            from fallback_extractor import AutoReceiptExtractor

        api_key = self._api_key_provider.load()
        with OpenAI(api_key=api_key, timeout=180.0, max_retries=0) as client:
            validator = ReceiptUrlValidator()
            extractor = AutoReceiptExtractor(
                browser_extractor=BrowserReceiptExtractor(
                    client,
                    url_validator=validator,
                ),
                hosted_extractor=HostedReceiptExtractor(client, validator),
            )
            return extractor.extract(url)
