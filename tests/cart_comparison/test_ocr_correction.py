"""Correcting extracted receipts against the catalogue's ocr-match."""

from decimal import Decimal
from typing import Any

from sali.cart_comparison.catalog import ProductLookup
from sali.cart_comparison.ocr_correction import OcrReceiptCorrector
from sali.receipt_extraction.models import ReceiptDocument


class FakeCatalog:
    """A catalogue whose contents each test states outright."""

    def __init__(
        self,
        known: dict[str, dict[str, Any]] | None = None,
        nearest: list[dict[str, Any]] | None = None,
        *,
        answering: bool = True,
    ) -> None:
        self._known = known or {}
        self._nearest = nearest or []
        self._answering = answering
        self.lookups: list[str] = []
        self.readings: list[tuple[str, str, float]] = []

    def find_product(self, barcode: str) -> ProductLookup:
        self.lookups.append(barcode)
        if not self._answering:
            return ProductLookup(None, False)
        return ProductLookup(self._known.get(barcode), True)

    def ocr_match(
        self,
        item_code: str,
        item_name: str,
        price: float,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        self.readings.append((item_code, item_name, price))
        return list(self._nearest)


class BrokenCatalog(FakeCatalog):
    def ocr_match(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("catalogue exploded mid-request")


def product(barcode: int, name: str) -> dict[str, Any]:
    return {
        "id": str(barcode),
        "productBarcode": barcode,
        "productName": name,
        "manufacturerOrImporterName": "",
    }


def receipt_item(
    position: int,
    name: str,
    code: str | None,
    *,
    unit_price: str | None = "10.00",
    final_total: str = "10.00",
) -> dict[str, Any]:
    return {
        "position": position,
        "code": code,
        "name": name,
        "categories": [],
        "quantity": "1",
        "unit": "unit",
        "unit_price": unit_price,
        "gross_total": final_total,
        "adjustments": [],
        "final_total": final_total,
    }


def document(
    *items: dict[str, Any], warnings: list[str] | None = None
) -> ReceiptDocument:
    total = str(sum((Decimal(entry["final_total"]) for entry in items), Decimal(0)))
    return ReceiptDocument.model_validate(
        {
            "schema_version": "1.0",
            "receipt": {
                "merchant": {
                    "name": "מרכול",
                    "branch_name": None,
                    "branch_number": None,
                },
                "transaction": {
                    "receipt_id": None,
                    "purchased_at": None,
                    "transaction_number": None,
                    "type": None,
                    "currency": "ILS",
                },
                "totals": {"subtotal": total, "discounts": "0", "total": total},
                "items": list(items),
            },
            "warnings": list(warnings or []),
        }
    )


def test_a_code_the_catalogue_knows_is_left_alone() -> None:
    """A barcode hit means the extractor read it right; right beats a guess."""
    catalog = FakeCatalog(known={"7290000000001": product(7290000000001, "חלב")})
    given = document(receipt_item(1, "חלב", "7290000000001"))

    corrected = OcrReceiptCorrector(catalog).correct(given)

    assert corrected is given
    assert catalog.readings == []


def test_a_confident_name_match_rewrites_the_misread_code() -> None:
    catalog = FakeCatalog(nearest=[product(7290000000388, "חלב תנובה 3")])
    given = document(receipt_item(1, "חלב תנובה 3", "7290000000007", unit_price="6.90"))

    corrected = OcrReceiptCorrector(catalog).correct(given)

    item = corrected.receipt.items[0]
    assert item.code == "7290000000388"
    assert item.name == "חלב תנובה 3"
    assert corrected.warnings == [
        "corrected: receipt.items[1].code to its catalogue barcode"
    ]
    # The reading was sent as printed, priced per unit.
    assert catalog.readings == [("7290000000007", "חלב תנובה 3", 6.9)]


def test_a_nearly_identical_code_corroborates_a_middling_name() -> None:
    """A misread digit is the error this pass exists for.

    The name alone scores below the rewrite bar, but the printed code is one
    edit from the candidate's barcode — together they identify the product.
    """
    catalog = FakeCatalog(nearest=[product(7290000000001, "חלב תנובה 1 ליטר")])
    given = document(receipt_item(1, "חלב תנובה", "7290000000007"))

    corrected = OcrReceiptCorrector(catalog).correct(given)

    item = corrected.receipt.items[0]
    assert item.code == "7290000000001"
    assert item.name == "חלב תנובה 1 ליטר"
    assert corrected.warnings == [
        "corrected: receipt.items[1].code to its catalogue barcode",
        "corrected: receipt.items[1].name to its catalogue name",
    ]


def test_a_middling_name_with_a_far_code_is_left_alone() -> None:
    """Below the bar and uncorroborated is a lookalike, and it gets saved."""
    catalog = FakeCatalog(nearest=[product(7290004444444, "חלב תנובה 1 ליטר")])
    given = document(receipt_item(1, "חלב תנובה", "7290000000007"))

    assert OcrReceiptCorrector(catalog).correct(given) is given


def test_a_wrong_product_is_never_accepted_on_code_alone() -> None:
    """One edit of code distance means nothing under a name that disagrees."""
    catalog = FakeCatalog(nearest=[product(7290000000001, "מלפפון חממה")])
    given = document(receipt_item(1, "חלב תנובה", "7290000000007"))

    assert OcrReceiptCorrector(catalog).correct(given) is given


def test_the_best_scoring_candidate_wins_not_the_first() -> None:
    catalog = FakeCatalog(
        nearest=[
            product(7290000000111, "מלפפון חממה"),
            product(7290000000222, "חלב תנובה 3"),
        ]
    )
    given = document(receipt_item(1, "חלב תנובה 3", "7290000000007"))

    corrected = OcrReceiptCorrector(catalog).correct(given)

    assert corrected.receipt.items[0].code == "7290000000222"


def test_a_plu_line_is_matched_without_a_barcode_lookup() -> None:
    """Weighed goods print merchant PLUs the catalogue does not key on."""
    catalog = FakeCatalog(nearest=[product(7290000000333, "עגבניות שרי")])
    given = document(
        receipt_item(1, "עגבניות שרי", None, unit_price=None, final_total="23.90")
    )

    corrected = OcrReceiptCorrector(catalog).correct(given)

    assert corrected.receipt.items[0].code == "7290000000333"
    assert catalog.lookups == []
    # With no unit price, the line total is the only price there is to send.
    assert catalog.readings == [("", "עגבניות שרי", 23.9)]


def test_an_unanswered_catalogue_changes_nothing() -> None:
    """With the catalogue silent there is no ground for overruling print."""
    catalog = FakeCatalog(answering=False)
    given = document(receipt_item(1, "חלב תנובה", "7290000000007"))

    assert OcrReceiptCorrector(catalog).correct(given) is given
    assert catalog.readings == []


def test_catalogue_trouble_never_fails_the_document() -> None:
    """Correction improves a document; it must never cost the extraction."""
    given = document(receipt_item(1, "חלב תנובה", "7290000000007"))

    assert OcrReceiptCorrector(BrokenCatalog()).correct(given) is given


def test_corrections_extend_the_warnings_reconciliation_wrote() -> None:
    catalog = FakeCatalog(nearest=[product(7290000000388, "חלב תנובה 3")])
    given = document(
        receipt_item(1, "חלב תנובה 3", "7290000000007"),
        warnings=["missing: receipt.items[1].quantity"],
    )

    corrected = OcrReceiptCorrector(catalog).correct(given)

    assert corrected.warnings == [
        "missing: receipt.items[1].quantity",
        "corrected: receipt.items[1].code to its catalogue barcode",
    ]


def test_correction_touches_nothing_numeric() -> None:
    """The rewrite renames a line; the receipt's arithmetic is settled."""
    catalog = FakeCatalog(nearest=[product(7290000000388, "חלב תנובה 3")])
    given = document(receipt_item(1, "חלב תנובה 3", "7290000000007", unit_price="6.90"))

    corrected = OcrReceiptCorrector(catalog).correct(given)

    item = corrected.receipt.items[0]
    assert item.unit_price == "6.90"
    assert item.final_total == "10.00"
    assert item.quantity == "1"
    assert corrected.receipt.totals == given.receipt.totals
