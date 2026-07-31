"""Fold a receipt's own unit wording onto the five the contract allows.

Receipts write the same unit a dozen ways and in two scripts — `kg`, `ק"ג`,
`קילו`, `Kg.` — and the UI multiplies by whatever it is given. Anything not
recognised becomes `unit`, which is what an unlabelled line on a receipt means.
"""

from __future__ import annotations

from sali.nearby.models import MeasureUnit

_ALIASES: dict[str, MeasureUnit] = {
    "kg": "kg",
    "kgs": "kg",
    "kilo": "kg",
    "kilogram": "kg",
    'ק"ג': "kg",
    "קג": "kg",
    "קילו": "kg",
    "קילוגרם": "kg",
    "g": "g",
    "gr": "g",
    "gram": "g",
    "grams": "g",
    "גרם": "g",
    "ג": "g",
    "l": "l",
    "lt": "l",
    "ltr": "l",
    "liter": "l",
    "litre": "l",
    "ליטר": "l",
    "ל": "l",
    "ml": "ml",
    "mls": "ml",
    "milliliter": "ml",
    'מ"ל': "ml",
    "מל": "ml",
    "unit": "unit",
    "units": "unit",
    "item": "unit",
    "items": "unit",
    "each": "unit",
    "ea": "unit",
    "pc": "unit",
    "pcs": "unit",
    "piece": "unit",
    "יח": "unit",
    'יח"': "unit",
    "יחידה": "unit",
    "יחידות": "unit",
}


def normalize_unit(unit: str | None) -> MeasureUnit:
    """The contract unit a receipt's unit text denotes; `unit` when unclear."""
    if not unit:
        return "unit"
    folded = unit.strip().casefold().rstrip(".").replace("׳", "").replace(" ", "")
    return _ALIASES.get(folded, "unit")


__all__ = ["normalize_unit"]
