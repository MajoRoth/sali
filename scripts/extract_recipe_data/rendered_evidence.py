"""Generic browser rendering and OpenAI extraction from rendered evidence."""

from __future__ import annotations

import base64
import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, ValidationError

if __package__:
    from .configuration import (
        BROWSER_NAVIGATION_TIMEOUT_MS,
        BROWSER_SETTLE_TIMEOUT_MS,
        MAX_OUTPUT_TOKENS,
        MAX_RENDERED_TEXT_CHARS,
        MAX_SCREENSHOT_BYTES,
        MODEL,
        RENDERED_EXTRACTION_PROMPT,
    )
    from .errors import HostedReceiptError
    from .hosted_extractor import _OpenAIClient
    from .inspection import HostedReceiptInspection, ReceiptInspectionVerifier
    from .models import (
        ReceiptDocument,
        SemanticValidationError,
        validate_and_reconcile,
    )
    from .url_validation import ReceiptUrlValidator
else:
    from configuration import (
        BROWSER_NAVIGATION_TIMEOUT_MS,
        BROWSER_SETTLE_TIMEOUT_MS,
        MAX_OUTPUT_TOKENS,
        MAX_RENDERED_TEXT_CHARS,
        MAX_SCREENSHOT_BYTES,
        MODEL,
        RENDERED_EXTRACTION_PROMPT,
    )
    from errors import HostedReceiptError
    from hosted_extractor import _OpenAIClient
    from inspection import HostedReceiptInspection, ReceiptInspectionVerifier
    from models import (
        ReceiptDocument,
        SemanticValidationError,
        validate_and_reconcile,
    )
    from url_validation import ReceiptUrlValidator


@dataclass(frozen=True, slots=True)
class RenderedPageSnapshot:
    """Raw evidence returned by a browser driver."""

    final_url: str
    page_title: str
    visible_text: str
    screenshot_png: bytes | None


class RenderedReceiptEvidence(BaseModel):
    """Bounded evidence sent to the receipt extraction model."""

    model_config = ConfigDict(extra="forbid", strict=True)

    requested_url: str
    final_url: str
    page_title: str
    visible_text: str
    screenshot_data_url: str | None


class _BrowserDriver(Protocol):
    def capture(
        self,
        url: str,
        *,
        allowed_hostname: str,
    ) -> RenderedPageSnapshot: ...


class PublicNetworkPolicy:
    """Reject non-HTTPS and non-public browser network destinations."""

    def __init__(self) -> None:
        self._approved_hosts: set[str] = set()

    def permits(self, url: str) -> bool:
        parsed = urlsplit(url)
        if parsed.scheme in {"about", "blob", "data"}:
            return True
        if parsed.scheme.casefold() != "https" or not parsed.hostname:
            return False

        hostname = parsed.hostname.rstrip(".").casefold()
        if hostname in self._approved_hosts:
            return True
        if self._is_public_hostname(hostname):
            self._approved_hosts.add(hostname)
            return True
        return False

    @staticmethod
    def _is_public_hostname(hostname: str) -> bool:
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            return False

        try:
            addresses = socket.getaddrinfo(
                hostname,
                443,
                type=socket.SOCK_STREAM,
            )
        except (socket.gaierror, UnicodeError):
            return False

        if not addresses:
            return False
        return all(
            ipaddress.ip_address(address[4][0]).is_global
            for address in addresses
        )


class PlaywrightBrowserDriver:
    """Capture text and pixels from an isolated, JavaScript-capable browser."""

    def __init__(
        self,
        *,
        navigation_timeout_ms: int = BROWSER_NAVIGATION_TIMEOUT_MS,
        settle_timeout_ms: int = BROWSER_SETTLE_TIMEOUT_MS,
    ) -> None:
        self._navigation_timeout_ms = navigation_timeout_ms
        self._settle_timeout_ms = settle_timeout_ms

    def capture(
        self,
        url: str,
        *,
        allowed_hostname: str,
    ) -> RenderedPageSnapshot:
        try:
            import playwright.sync_api as playwright_api
        except ImportError as exc:
            raise HostedReceiptError(
                "browser fallback is unavailable because Playwright is not installed"
            ) from exc

        network_policy = PublicNetworkPolicy()
        try:
            with playwright_api.sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(
                        accept_downloads=False,
                        java_script_enabled=True,
                        service_workers="block",
                        ignore_https_errors=False,
                        viewport={"width": 1440, "height": 1200},
                    )
                    context.route_web_socket(
                        "**/*",
                        lambda websocket: websocket.close(),
                    )
                    page = context.new_page()
                    page.on("dialog", lambda dialog: dialog.dismiss())
                    page.on("download", lambda download: download.cancel())
                    page.on("popup", lambda popup: popup.close())

                    def route_request(route: Any) -> None:
                        request = route.request
                        request_url = request.url
                        request_hostname = (
                            urlsplit(request_url).hostname or ""
                        ).rstrip(".").casefold()
                        is_main_navigation = (
                            request.is_navigation_request()
                            and request.frame == page.main_frame
                        )
                        if (
                            is_main_navigation
                            and request_hostname != allowed_hostname
                        ):
                            route.abort("blockedbyclient")
                        elif network_policy.permits(request_url):
                            route.continue_()
                        else:
                            route.abort("blockedbyclient")

                    page.route("**/*", route_request)
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=self._navigation_timeout_ms,
                    )
                    try:
                        page.wait_for_load_state(
                            "networkidle",
                            timeout=self._settle_timeout_ms,
                        )
                    except playwright_api.TimeoutError:
                        pass

                    visible_text = self._wait_for_stable_text(
                        page,
                        playwright_error=playwright_api.Error,
                    )
                    page_title = page.title()
                    final_url = page.url
                    screenshot_png = self._capture_screenshot(
                        page,
                        playwright_error=playwright_api.Error,
                    )
                    context.close()
                finally:
                    browser.close()
        except playwright_api.TimeoutError as exc:
            raise HostedReceiptError(
                "browser navigation timed out after "
                f"{self._navigation_timeout_ms // 1000} seconds: {exc}"
            ) from exc
        except playwright_api.Error as exc:
            raise HostedReceiptError(f"browser could not render the receipt: {exc}") from exc

        return RenderedPageSnapshot(
            final_url=final_url,
            page_title=page_title,
            visible_text=visible_text,
            screenshot_png=screenshot_png,
        )

    def _wait_for_stable_text(
        self,
        page: Any,
        *,
        playwright_error: type[Exception],
    ) -> str:
        previous = ""
        stable_samples = 0
        sample_count = max(2, self._settle_timeout_ms // 500)
        for _ in range(sample_count):
            try:
                current = page.locator("body").inner_text(timeout=2_000)
            except playwright_error:
                current = ""
            if current and current == previous:
                stable_samples += 1
                if stable_samples >= 2:
                    return current
            else:
                stable_samples = 0
                previous = current
            page.wait_for_timeout(500)
        return previous

    @staticmethod
    def _capture_screenshot(
        page: Any,
        *,
        playwright_error: type[Exception],
    ) -> bytes | None:
        try:
            return page.screenshot(
                type="png",
                full_page=True,
                animations="disabled",
            )
        except playwright_error:
            try:
                return page.screenshot(
                    type="png",
                    full_page=False,
                    animations="disabled",
                )
            except playwright_error:
                return None


class BrowserReceiptRenderer:
    """Validate a URL and turn any compatible webpage into bounded evidence."""

    def __init__(
        self,
        *,
        driver: _BrowserDriver | None = None,
        url_validator: ReceiptUrlValidator | None = None,
        max_text_chars: int = MAX_RENDERED_TEXT_CHARS,
        max_screenshot_bytes: int = MAX_SCREENSHOT_BYTES,
    ) -> None:
        self._driver = driver or PlaywrightBrowserDriver()
        self._url_validator = url_validator or ReceiptUrlValidator()
        self._max_text_chars = max_text_chars
        self._max_screenshot_bytes = max_screenshot_bytes

    def render(self, url: str) -> RenderedReceiptEvidence:
        normalized_url, hostname = self._url_validator.validate(url)
        snapshot = self._driver.capture(
            normalized_url,
            allowed_hostname=hostname,
        )
        final_url, final_hostname = self._url_validator.validate(snapshot.final_url)
        if final_hostname != hostname:
            raise HostedReceiptError(
                "browser navigation ended on a different hostname"
            )

        visible_text = snapshot.visible_text.strip()[: self._max_text_chars]
        screenshot_data_url = self._encode_screenshot(snapshot.screenshot_png)
        if not visible_text and screenshot_data_url is None:
            raise HostedReceiptError(
                "browser rendered the page but found no visible text or screenshot"
            )

        return RenderedReceiptEvidence(
            requested_url=normalized_url,
            final_url=final_url,
            page_title=snapshot.page_title.strip()[:1_000],
            visible_text=visible_text,
            screenshot_data_url=screenshot_data_url,
        )

    def _encode_screenshot(self, screenshot_png: bytes | None) -> str | None:
        if (
            screenshot_png is None
            or not screenshot_png
            or len(screenshot_png) > self._max_screenshot_bytes
        ):
            return None
        encoded = base64.b64encode(screenshot_png).decode("ascii")
        return f"data:image/png;base64,{encoded}"


class RenderedEvidenceReceiptExtractor:
    """Extract and reconcile a receipt from browser-rendered evidence."""

    def __init__(self, client: _OpenAIClient) -> None:
        self._client = client

    def extract(self, evidence: RenderedReceiptEvidence) -> ReceiptDocument:
        response = self._request_inspection(evidence)
        inspection = ReceiptInspectionVerifier.parse(
            response.output_parsed,
            evidence_kind="rendered",
        )
        ReceiptInspectionVerifier.ensure_verified(
            inspection,
            source="Rendered evidence extraction",
        )
        try:
            return validate_and_reconcile(inspection.receipt)
        except SemanticValidationError as exc:
            raise HostedReceiptError(
                "the rendered receipt failed local reconciliation"
            ) from exc

    def _request_inspection(self, evidence: RenderedReceiptEvidence) -> Any:
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

        try:
            return self._client.responses.parse(
                model=MODEL,
                reasoning={"effort": "low"},
                store=False,
                instructions=RENDERED_EXTRACTION_PROMPT,
                input=[{"role": "user", "content": content}],
                text_format=HostedReceiptInspection,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
        except ValidationError as exc:
            raise HostedReceiptError(
                "OpenAI returned an invalid rendered receipt inspection"
            ) from exc
        except OpenAIError as exc:
            raise HostedReceiptError(
                "the OpenAI rendered receipt request failed"
            ) from exc


__all__ = [
    "BrowserReceiptRenderer",
    "PlaywrightBrowserDriver",
    "PublicNetworkPolicy",
    "RenderedEvidenceReceiptExtractor",
    "RenderedPageSnapshot",
    "RenderedReceiptEvidence",
]
