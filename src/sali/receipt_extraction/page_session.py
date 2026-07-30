"""A live receipt page the model can interrogate while it extracts.

The previous design took one snapshot and closed the browser, which meant a
receipt whose line items sit behind a control was unreadable no matter how the
model was prompted. Keeping the page open instead lets the model ask for more
when what it was handed is not enough.

Navigation stays inside the same public host under the existing network policy;
the tools only read and click, so the model can widen its own view of a page it
was already allowed to open, and nothing more.
"""

from __future__ import annotations

import base64
from contextlib import suppress
from types import TracebackType
from typing import Any, Self

if __package__:
    from .configuration import (
        BROWSER_NAVIGATION_TIMEOUT_MS,
        BROWSER_SETTLE_TIMEOUT_MS,
        MAX_PAGE_HTML_CHARS,
        MAX_RENDERED_TEXT_CHARS,
        MAX_SCREENSHOT_BYTES,
    )
    from .errors import HostedReceiptError
    from .page_source import reduce_receipt_markup
    from .rendered_evidence import PublicNetworkPolicy, RenderedReceiptEvidence
    from .url_validation import ReceiptUrlValidator
else:
    from configuration import (
        BROWSER_NAVIGATION_TIMEOUT_MS,
        BROWSER_SETTLE_TIMEOUT_MS,
        MAX_PAGE_HTML_CHARS,
        MAX_RENDERED_TEXT_CHARS,
        MAX_SCREENSHOT_BYTES,
    )
    from errors import HostedReceiptError
    from page_source import reduce_receipt_markup
    from rendered_evidence import PublicNetworkPolicy, RenderedReceiptEvidence
    from url_validation import ReceiptUrlValidator


class ReceiptPageSession:
    """An open, policy-restricted browser page scoped to one receipt URL."""

    def __init__(
        self,
        url: str,
        *,
        url_validator: ReceiptUrlValidator | None = None,
        navigation_timeout_ms: int = BROWSER_NAVIGATION_TIMEOUT_MS,
        settle_timeout_ms: int = BROWSER_SETTLE_TIMEOUT_MS,
    ) -> None:
        validator = url_validator or ReceiptUrlValidator()
        self._requested_url, self._hostname = validator.validate(url)
        self._url_validator = validator
        self._navigation_timeout_ms = navigation_timeout_ms
        self._settle_timeout_ms = settle_timeout_ms
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._errors: Any = None

    def __enter__(self) -> Self:
        try:
            import playwright.sync_api as playwright_api
        except ImportError as exc:
            raise HostedReceiptError(
                "browser extraction is unavailable because Playwright is not installed"
            ) from exc

        self._errors = playwright_api
        network_policy = PublicNetworkPolicy()
        try:
            self._playwright = playwright_api.sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                accept_downloads=False,
                java_script_enabled=True,
                service_workers="block",
                ignore_https_errors=False,
                viewport={"width": 1440, "height": 1200},
            )
            self._context.route_web_socket("**/*", lambda socket: socket.close())
            page = self._context.new_page()
            page.on("dialog", lambda dialog: dialog.dismiss())
            page.on("download", lambda download: download.cancel())
            page.on("popup", lambda popup: popup.close())
            page.route(
                "**/*",
                lambda route: self._route_request(route, page, network_policy),
            )
            self._page = page

            page.goto(
                self._requested_url,
                wait_until="domcontentloaded",
                timeout=self._navigation_timeout_ms,
            )
            self._settle()
        except playwright_api.TimeoutError as exc:
            self.close()
            raise HostedReceiptError(
                "browser navigation timed out after "
                f"{self._navigation_timeout_ms // 1000} seconds: {exc}"
            ) from exc
        except playwright_api.Error as exc:
            self.close()
            raise HostedReceiptError(
                f"browser could not open the receipt: {exc}"
            ) from exc
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        for resource, method in (
            (self._context, "close"),
            (self._browser, "close"),
            (self._playwright, "stop"),
        ):
            if resource is None:
                continue
            # Teardown runs on the failure path too and must not mask the cause.
            with suppress(Exception):
                getattr(resource, method)()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    # -- evidence ---------------------------------------------------------

    def evidence(self) -> RenderedReceiptEvidence:
        """Capture everything the model needs for a first read of the page."""
        final_url, final_hostname = self._url_validator.validate(self._page.url)
        if final_hostname != self._hostname:
            raise HostedReceiptError("browser navigation ended on a different hostname")

        page_html = self.reduced_html()
        visible_text = self._visible_text()
        screenshot_data_url = self._screenshot_data_url()
        if not page_html and not visible_text and screenshot_data_url is None:
            raise HostedReceiptError(
                "browser opened the page but found no markup, text, or screenshot"
            )

        return RenderedReceiptEvidence(
            requested_url=self._requested_url,
            final_url=final_url,
            page_title=self._page_title(),
            page_html=page_html,
            visible_text=visible_text,
            screenshot_data_url=screenshot_data_url,
        )

    def reduced_html(self) -> str:
        """The page's markup stripped to receipt-bearing structure."""
        return reduce_receipt_markup(self._content())

    def raw_html(self) -> str:
        """The page's markup as served, for when reduction dropped something."""
        return self._content()[:MAX_PAGE_HTML_CHARS]

    # -- interaction ------------------------------------------------------

    def click_text(self, text: str) -> str:
        """Click the first element showing `text`; return the resulting markup.

        A click that leaves the receipt's own host is undone, so exploring the
        page can never carry the session somewhere it was not allowed to go.
        """
        query = (text or "").strip()
        if not query:
            raise ValueError("click target text must not be blank")

        before_url = self._page.url
        locator = self._page.get_by_text(query, exact=False).first
        try:
            locator.click(timeout=5_000)
        except self._errors.Error as exc:
            raise LookupError(f"could not click {query!r}: {exc}") from exc

        self._settle()
        if self._page.url != before_url:
            _, hostname = self._url_validator.validate(self._page.url)
            if hostname != self._hostname:
                self._page.go_back(timeout=self._navigation_timeout_ms)
                self._settle()
                raise LookupError(
                    f"clicking {query!r} left the receipt host; the click was undone"
                )
        return self.reduced_html()

    # -- internals --------------------------------------------------------

    def _route_request(
        self,
        route: Any,
        page: Any,
        network_policy: PublicNetworkPolicy,
    ) -> None:
        from urllib.parse import urlsplit

        request = route.request
        request_hostname = (urlsplit(request.url).hostname or "").rstrip(".").casefold()
        is_main_navigation = (
            request.is_navigation_request() and request.frame == page.main_frame
        )
        if is_main_navigation and request_hostname != self._hostname:
            route.abort("blockedbyclient")
        elif network_policy.permits(request.url):
            route.continue_()
        else:
            route.abort("blockedbyclient")

    def _settle(self) -> None:
        try:
            self._page.wait_for_load_state(
                "networkidle",
                timeout=self._settle_timeout_ms,
            )
        except self._errors.TimeoutError:
            pass

    def _content(self) -> str:
        try:
            return self._page.content()
        except self._errors.Error:
            return ""

    def _visible_text(self) -> str:
        try:
            text = self._page.locator("body").inner_text(timeout=5_000)
        except self._errors.Error:
            return ""
        return text.strip()[:MAX_RENDERED_TEXT_CHARS]

    def _page_title(self) -> str:
        try:
            return self._page.title().strip()[:1_000]
        except self._errors.Error:
            return ""

    def _screenshot_data_url(self) -> str | None:
        screenshot: bytes | None = None
        for full_page in (True, False):
            try:
                screenshot = self._page.screenshot(
                    type="png",
                    full_page=full_page,
                    animations="disabled",
                )
                break
            except self._errors.Error:
                continue
        if not screenshot or len(screenshot) > MAX_SCREENSHOT_BYTES:
            return None
        return "data:image/png;base64," + base64.b64encode(screenshot).decode("ascii")


__all__ = ["ReceiptPageSession"]
