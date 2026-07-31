"""Markup reduction over the real receipt pages this feature was built for."""

from __future__ import annotations

from pathlib import Path

import pytest

from sali.receipt_extraction.page_source import reduce_receipt_markup

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "receipt_pages"


def _page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "max_ratio"),
    [("stopmarket", 0.25), ("weezmo-1", 0.15), ("weezmo-2", 0.15)],
)
def test_reduction_discards_the_bulk_of_a_receipt_page(
    name: str,
    max_ratio: float,
) -> None:
    raw = _page(name)
    reduced = reduce_receipt_markup(raw)

    assert reduced, "reduction must not empty a real receipt page"
    assert len(reduced) < len(raw) * max_ratio


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("stopmarket", ["אפרסק", "נקטרינה", "573.06", "32.90"]),
        ("weezmo-1", ["POLYSKIN", "39.80", "18.9"]),
        ("weezmo-2", ["ביצים אורגני", "נוטלה", "173.50", "8.86"]),
    ],
)
def test_reduction_keeps_every_receipt_fact(name: str, expected: list[str]) -> None:
    reduced = reduce_receipt_markup(_page(name))

    for needle in expected:
        assert needle in reduced, f"{name} lost {needle!r}"


def test_reduction_keeps_content_the_browser_does_not_paint() -> None:
    """The weezmo-2 line items sit in a collapsed section.

    They are the reason reduction works on markup rather than visible text: a
    visible-text capture of this page yields a total and nothing else.
    """
    reduced = reduce_receipt_markup(_page("weezmo-2"))

    assert "ביצים אורגני" in reduced
    assert "<table>" in reduced
    assert "שם פריט" in reduced


@pytest.mark.parametrize("name", ["stopmarket", "weezmo-1", "weezmo-2"])
def test_reduction_drops_scripts_and_styling(name: str) -> None:
    reduced = reduce_receipt_markup(_page(name))

    assert "<script" not in reduced.lower()
    assert "<style" not in reduced.lower()
    assert "class=" not in reduced.lower()


def test_reduction_is_bounded() -> None:
    reduced = reduce_receipt_markup(_page("stopmarket"), max_chars=500)

    assert len(reduced) <= 500


@pytest.mark.parametrize(
    "markup",
    [
        "",
        "<div><p>unclosed",
        "<table><tr><td>3.50</td></table>",
        "<div><<>>malformed<script>x</div>",
        "<p>plain text</p>",
    ],
)
def test_reduction_never_raises_on_broken_markup(markup: str) -> None:
    reduce_receipt_markup(markup)


def test_reduction_preserves_table_structure() -> None:
    reduced = reduce_receipt_markup(
        "<html><body><table><tr><td>Milk</td><td>5.90</td></tr></table></body></html>"
    )

    assert "<table>" in reduced
    assert "<td>" in reduced
    assert "Milk" in reduced
    assert "5.90" in reduced
