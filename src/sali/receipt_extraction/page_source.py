"""Reduce a receipt page's HTML to the structure a model needs to read it.

Receipt pages are single-page apps: most of their bytes are inline styles,
bundled scripts, and framework attributes. The purchase itself is a small island
of tables and text. This module keeps that island and throws the rest away,
typically shrinking a page by 85-95%.

It deliberately keeps markup that a browser does not paint. Real receipts hide
their line items behind a collapsed "details" control, and that content is
present in the DOM before anything is clicked, so dropping invisible nodes would
discard the very rows the extraction needs.
"""

from __future__ import annotations

import re
from contextlib import suppress
from html.parser import HTMLParser

if __package__:
    from .configuration import MAX_PAGE_HTML_CHARS
else:
    from configuration import MAX_PAGE_HTML_CHARS

#: Elements whose entire subtree carries no receipt evidence.
DISCARDED_SUBTREES = frozenset(
    {
        "head",
        "noscript",
        "script",
        "style",
        "svg",
        "template",
    }
)

#: Elements kept because their nesting conveys row, column, or grouping meaning.
STRUCTURAL_ELEMENTS = frozenset(
    {
        "article",
        "b",
        "caption",
        "dd",
        "div",
        "dl",
        "dt",
        "em",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "i",
        "li",
        "main",
        "ol",
        "p",
        "section",
        "small",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)

#: Void elements that never receive a closing tag.
VOID_ELEMENTS = frozenset({"br", "hr"})

#: Attributes kept because they carry text a reader would otherwise lose.
PRESERVED_ATTRIBUTES = ("alt", "title")

_COLLAPSIBLE_WHITESPACE = re.compile(r"\s+")
_BLANK_LINES = re.compile(r"\n{2,}")


class _ReceiptMarkupReducer(HTMLParser):
    """Collect a minimal, well-nested rendering of a page's meaningful markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._open_elements: list[str] = []
        self._suppression_depth = 0
        self._suppressing_tag: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if self._suppressing_tag is not None:
            if tag == self._suppressing_tag:
                self._suppression_depth += 1
            return
        if tag in DISCARDED_SUBTREES:
            self._suppressing_tag = tag
            self._suppression_depth = 1
            return
        if tag in VOID_ELEMENTS:
            self._parts.append("\n")
            return
        if tag == "img":
            self._append_attribute_text(attrs)
            return
        if tag not in STRUCTURAL_ELEMENTS:
            return

        self._append_attribute_text(attrs)
        self._parts.append(f"<{tag}>")
        self._open_elements.append(tag)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if self._suppressing_tag is None and tag == "img":
            self._append_attribute_text(attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._suppressing_tag is not None:
            if tag == self._suppressing_tag:
                self._suppression_depth -= 1
                if self._suppression_depth <= 0:
                    self._suppressing_tag = None
            return
        if tag not in STRUCTURAL_ELEMENTS or tag not in self._open_elements:
            return
        # Close any element the page left dangling so the output stays nested.
        while self._open_elements:
            open_tag = self._open_elements.pop()
            self._parts.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data: str) -> None:
        if self._suppressing_tag is not None:
            return
        text = _COLLAPSIBLE_WHITESPACE.sub(" ", data).strip()
        if text:
            self._parts.append(text)

    def _append_attribute_text(self, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for name in PRESERVED_ATTRIBUTES:
            value = values.get(name)
            if value:
                cleaned = _COLLAPSIBLE_WHITESPACE.sub(" ", value).strip()
                if cleaned:
                    self._parts.append(cleaned)

    def result(self) -> str:
        parts = list(self._parts)
        for open_tag in reversed(self._open_elements):
            parts.append(f"</{open_tag}>")
        return "".join(parts)


def reduce_receipt_markup(
    html: str,
    *,
    max_chars: int = MAX_PAGE_HTML_CHARS,
) -> str:
    """Return `html` stripped to the structure and text a reader needs.

    The result keeps element nesting so table rows stay legible, and is
    truncated to `max_chars` so one hostile page cannot dominate a request.
    """
    reducer = _ReceiptMarkupReducer()
    # Malformed merchant markup must degrade to whatever parsed, never raise.
    with suppress(Exception):
        reducer.feed(html)
        reducer.close()

    markup = _drop_empty_containers(reducer.result())
    markup = markup.replace("><", ">\n<")
    markup = _BLANK_LINES.sub("\n", markup).strip()
    return markup[:max_chars]


def _drop_empty_containers(markup: str) -> str:
    """Collapse `<div></div>` chains left behind once styling was removed."""
    pattern = re.compile(
        r"<(" + "|".join(sorted(STRUCTURAL_ELEMENTS)) + r")>\s*</\1>",
        re.IGNORECASE,
    )
    for _ in range(12):
        reduced = pattern.sub("", markup)
        if reduced == markup:
            break
        markup = reduced
    return markup


__all__ = [
    "DISCARDED_SUBTREES",
    "STRUCTURAL_ELEMENTS",
    "reduce_receipt_markup",
]
