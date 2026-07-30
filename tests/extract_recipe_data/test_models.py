"""Tests for normalized receipt models and reconciliation."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from sali.receipt_extraction.models import (
    NormalizedReceipt,
    SemanticValidationError,
    validate_and_reconcile,
)


def valid_receipt_data() -> dict[str, object]:
    return {
        "merchant": {
            "name": "שוק הדוגמה",
            "branch_name": None,
            "branch_number": None,
        },
        "transaction": {
            "receipt_id": None,
            "purchased_at": "2026-07-30T18:42:00+03:00",
            "transaction_number": "42",
            "type": "purchase",
            "currency": "ILS",
        },
        "totals": {
            "subtotal": "32.00",
            "discounts": "-2.00",
            "total": "30.00",
        },
        "items": [
            {
                "position": 1,
                "code": "000123",
                "name": "קפה לדוגמה",
                "categories": [],
                "quantity": "2",
                "unit": "item",
                "unit_price": "10.00",
                "gross_total": "20.00",
                "adjustments": [],
                "final_total": "20.00",
            },
            {
                "position": 2,
                "code": None,
                "name": "עגבניות לדוגמה",
                "categories": ["produce"],
                "quantity": "1.500",
                "unit": "kg",
                "unit_price": "8.00",
                "gross_total": "12.00",
                "adjustments": [
                    {
                        "description": "מבצע",
                        "amount": "-2.00",
                    }
                ],
                "final_total": "10.00",
            },
        ],
    }


def valid_receipt() -> NormalizedReceipt:
    return NormalizedReceipt.model_validate(valid_receipt_data())


def test_receipt_document_preserves_api_shape_and_unicode() -> None:
    document = validate_and_reconcile(valid_receipt())
    payload = document.model_dump(mode="json")

    assert list(payload) == ["schema_version", "receipt", "warnings"]
    assert payload["schema_version"] == "1.0"
    assert payload["receipt"]["merchant"]["branch_name"] is None
    assert payload["receipt"]["items"][0]["code"] == "000123"
    assert "שוק הדוגמה" in json.dumps(payload, ensure_ascii=False)
    assert "source_url" not in payload
    assert "model" not in payload
    assert "transcript" not in payload


@pytest.mark.parametrize(
    "invalid_value",
    [5.5, 5, "1e2", "1,200", "₪5.50", "", "NaN", "Infinity", "+5"],
)
def test_decimal_fields_reject_non_decimal_strings(invalid_value: object) -> None:
    payload = valid_receipt_data()
    payload["totals"]["total"] = invalid_value  # type: ignore[index]

    with pytest.raises(ValidationError):
        NormalizedReceipt.model_validate(payload)


def test_model_facing_schema_requires_nullable_fields_and_forbids_extras() -> None:
    payload = valid_receipt_data()
    del payload["merchant"]["branch_name"]  # type: ignore[index]

    with pytest.raises(ValidationError):
        NormalizedReceipt.model_validate(payload)

    payload = valid_receipt_data()
    payload["merchant"]["unexpected"] = "value"  # type: ignore[index]

    with pytest.raises(ValidationError):
        NormalizedReceipt.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "merchant_name",
        "transaction_type",
        "item_code",
        "item_name",
        "item_category",
        "item_unit",
        "adjustment_description",
    ],
)
def test_non_empty_text_fields_reject_blank_or_whitespace(field: str) -> None:
    payload = valid_receipt_data()
    if field == "merchant_name":
        payload["merchant"]["name"] = "   "  # type: ignore[index]
    elif field == "transaction_type":
        payload["transaction"]["type"] = "\t"  # type: ignore[index]
    elif field == "item_code":
        payload["items"][0]["code"] = "\n"  # type: ignore[index]
    elif field == "item_name":
        payload["items"][0]["name"] = ""  # type: ignore[index]
    elif field == "item_category":
        payload["items"][1]["categories"] = ["produce", "  "]  # type: ignore[index]
    elif field == "item_unit":
        payload["items"][0]["unit"] = "  "  # type: ignore[index]
    else:
        payload["items"][1]["adjustments"][0]["description"] = "  "  # type: ignore[index]

    with pytest.raises(ValidationError, match="text must not be blank"):
        NormalizedReceipt.model_validate(payload)


def test_non_empty_text_local_validator_does_not_emit_min_length() -> None:
    schema = json.dumps(NormalizedReceipt.model_json_schema())

    assert "minLength" not in schema


def test_json_does_not_escape_formula_looking_product_text() -> None:
    receipt = valid_receipt()
    receipt.items[0].name = "=1+1"

    document = validate_and_reconcile(receipt)

    assert document.receipt.items[0].name == "=1+1"


def test_reconciliation_accepts_inclusive_two_cent_tolerance() -> None:
    receipt = valid_receipt()
    receipt.totals.total = "30.02"

    assert validate_and_reconcile(receipt).receipt.totals.total == "30.02"


def test_reconciliation_rejects_more_than_two_cents_difference() -> None:
    receipt = valid_receipt()
    receipt.totals.total = "30.0201"

    with pytest.raises(SemanticValidationError, match="final_total"):
        validate_and_reconcile(receipt)


def test_reconciliation_rejects_line_adjustment_mismatch() -> None:
    receipt = valid_receipt()
    receipt.items[1].final_total = "11.00"
    receipt.totals.total = "31.00"
    receipt.totals.discounts = "-1.00"

    with pytest.raises(SemanticValidationError, match="plus adjustments"):
        validate_and_reconcile(receipt)


def test_reconciliation_rejects_empty_items_and_bad_positions() -> None:
    empty = valid_receipt()
    empty.items = []
    empty.totals.subtotal = "0"
    empty.totals.discounts = "0"
    empty.totals.total = "0"

    with pytest.raises(SemanticValidationError, match="at least one"):
        validate_and_reconcile(empty)

    bad_position = valid_receipt()
    bad_position.items[1].position = 3

    with pytest.raises(SemanticValidationError, match="array order"):
        validate_and_reconcile(bad_position)

    blank_name = valid_receipt()
    blank_name.items[0].name = "   "

    with pytest.raises(SemanticValidationError, match="name must not be blank"):
        validate_and_reconcile(blank_name)


def test_missing_gross_and_exact_unit_price_are_derived_with_stable_warnings() -> None:
    receipt = valid_receipt()
    receipt.items[0].gross_total = None
    receipt.items[0].unit_price = None

    document = validate_and_reconcile(receipt)

    assert document.receipt.items[0].gross_total == "20.00"
    assert document.receipt.items[0].unit_price == "10"
    assert document.warnings == [
        "derived: receipt.items[1].gross_total from final_total and adjustments",
        "derived: receipt.items[1].unit_price from gross_total and quantity",
    ]


def test_nonterminating_derivation_remains_null_and_warns() -> None:
    receipt = valid_receipt()
    receipt.items[0].quantity = "3"
    receipt.items[0].unit_price = None

    document = validate_and_reconcile(receipt)

    assert document.receipt.items[0].unit_price is None
    assert document.warnings == ["missing: receipt.items[1].unit_price"]


def test_incorrect_discount_is_corrected_from_item_adjustments() -> None:
    receipt = valid_receipt()
    receipt.totals.discounts = "-1.00"

    document = validate_and_reconcile(receipt)

    assert document.receipt.totals.discounts == "-2.00"
    assert document.warnings == [
        "corrected: receipt.totals.discounts from item signed adjustments"
    ]


def test_top_level_components_are_corrected_from_valid_item_arithmetic() -> None:
    receipt = valid_receipt()
    receipt.totals.subtotal = "33.00"
    receipt.totals.discounts = "-3.00"

    document = validate_and_reconcile(receipt)

    assert document.receipt.totals.subtotal == "32.00"
    assert document.receipt.totals.discounts == "-2.00"
    assert document.warnings == [
        "corrected: receipt.totals.subtotal from item gross_total values",
        "corrected: receipt.totals.discounts from item signed adjustments",
    ]


def test_missing_top_level_components_are_derived_from_items() -> None:
    receipt = valid_receipt()
    receipt.totals.subtotal = None
    receipt.totals.discounts = None

    document = validate_and_reconcile(receipt)

    assert document.receipt.totals.subtotal == "32.00"
    assert document.receipt.totals.discounts == "-2.00"
    assert document.warnings == [
        "derived: receipt.totals.subtotal from item gross_total values",
        "derived: receipt.totals.discounts from item signed adjustments",
    ]
