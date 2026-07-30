from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

RECONCILIATION_TOLERANCE = Decimal("0.02")
DECIMAL_STRING_PATTERN = r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$"


def _reject_blank_text(value: str) -> str:
    if not value:
        raise ValueError("text must not be blank")
    return value


type DecimalString = Annotated[
    str,
    StringConstraints(pattern=DECIMAL_STRING_PATTERN),
]
type NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    AfterValidator(_reject_blank_text),
]
type CurrencyCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]{3}$"),
]
type ItemPosition = Annotated[int, Field(ge=1)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Merchant(_StrictModel):
    name: NonEmptyText | None
    branch_name: NonEmptyText | None
    branch_number: NonEmptyText | None


class Transaction(_StrictModel):
    receipt_id: NonEmptyText | None
    purchased_at: NonEmptyText | None
    transaction_number: NonEmptyText | None
    type: NonEmptyText | None
    currency: CurrencyCode | None


class Totals(_StrictModel):
    subtotal: DecimalString | None
    discounts: Annotated[
        DecimalString | None,
        Field(
            description=(
                "Signed aggregate discount amount; discounts are negative and "
                "surcharges are positive."
            )
        ),
    ]
    total: DecimalString


class Adjustment(_StrictModel):
    description: NonEmptyText | None
    amount: Annotated[
        DecimalString,
        Field(
            description=(
                "Signed contribution to the item total; discounts are negative "
                "and surcharges are positive."
            )
        ),
    ]


class Item(_StrictModel):
    position: ItemPosition
    code: NonEmptyText | None
    name: NonEmptyText
    categories: list[NonEmptyText]
    quantity: DecimalString | None
    unit: NonEmptyText | None
    unit_price: DecimalString | None
    gross_total: Annotated[
        DecimalString | None,
        Field(description="Line total before signed adjustments."),
    ]
    adjustments: list[Adjustment]
    final_total: Annotated[
        DecimalString,
        Field(description="Line total after all signed adjustments."),
    ]


class NormalizedReceipt(_StrictModel):
    merchant: Merchant
    transaction: Transaction
    totals: Totals
    items: list[Item]


class ReceiptDocument(_StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    receipt: NormalizedReceipt
    warnings: list[str]


class ReceiptImageTotalDocument(_StrictModel):
    """A verified Receipt Image Total without an extractable complete cart."""

    total: DecimalString
    currency: CurrencyCode | None
    warnings: list[str]


class SemanticValidationError(ValueError):
    """A structurally valid model extraction that fails local receipt checks."""

    def __init__(self, errors: list[str]) -> None:
        if not errors:
            raise ValueError("SemanticValidationError requires at least one error")
        self.errors = tuple(errors)
        super().__init__("receipt validation failed: " + "; ".join(self.errors))


def validate_and_reconcile(receipt: NormalizedReceipt) -> ReceiptDocument:
    """Derive safe values and reconcile a model extraction using Decimal math."""
    errors: list[str] = []
    warnings: list[str] = []
    reconciled_items: list[Item] = []

    _warn_if_missing(
        warnings,
        receipt.merchant.name,
        "receipt.merchant.name",
    )
    _warn_if_missing(
        warnings,
        receipt.transaction.purchased_at,
        "receipt.transaction.purchased_at",
    )
    _warn_if_missing(
        warnings,
        receipt.transaction.currency,
        "receipt.transaction.currency",
    )

    if not receipt.items:
        errors.append("receipt.items must contain at least one purchased item")

    for expected_position, item in enumerate(receipt.items, start=1):
        path = f"receipt.items[{expected_position}]"
        if not item.name.strip():
            errors.append(f"{path}.name must not be blank")
        if item.position != expected_position:
            errors.append(
                f"{path}.position must be {expected_position} to match array order"
            )

        adjustment_total = sum(
            (Decimal(adjustment.amount) for adjustment in item.adjustments),
            start=Decimal(0),
        )
        final_total = Decimal(item.final_total)
        gross_total = (
            Decimal(item.gross_total)
            if item.gross_total is not None
            else final_total - adjustment_total
        )

        updates: dict[str, str] = {}
        if item.gross_total is None:
            updates["gross_total"] = _format_decimal(gross_total)
            warnings.append(
                f"derived: {path}.gross_total from final_total and adjustments"
            )

        if not _within_tolerance(
            gross_total + adjustment_total,
            final_total,
        ):
            errors.append(
                f"{path}.gross_total plus adjustments must match final_total "
                f"within {RECONCILIATION_TOLERANCE}"
            )

        quantity = Decimal(item.quantity) if item.quantity is not None else None
        unit_price = Decimal(item.unit_price) if item.unit_price is not None else None

        if quantity is None and unit_price not in (None, Decimal(0)):
            quantity = _exact_decimal_divide(gross_total, unit_price)
            if quantity is not None:
                updates["quantity"] = _format_decimal(quantity)
                warnings.append(
                    f"derived: {path}.quantity from gross_total and unit_price"
                )

        if unit_price is None and quantity not in (None, Decimal(0)):
            unit_price = _exact_decimal_divide(gross_total, quantity)
            if unit_price is not None:
                updates["unit_price"] = _format_decimal(unit_price)
                warnings.append(
                    f"derived: {path}.unit_price from gross_total and quantity"
                )

        if quantity is None:
            warnings.append(f"missing: {path}.quantity")
        if unit_price is None:
            warnings.append(f"missing: {path}.unit_price")

        if (
            quantity is not None
            and unit_price is not None
            and not _within_tolerance(
                quantity * unit_price,
                gross_total,
            )
        ):
            errors.append(
                f"{path}.quantity times unit_price must match gross_total "
                f"within {RECONCILIATION_TOLERANCE}"
            )

        reconciled_items.append(item.model_copy(update=updates) if updates else item)

    stated_total = Decimal(receipt.totals.total)
    item_total = sum(
        (Decimal(item.final_total) for item in receipt.items),
        start=Decimal(0),
    )
    item_gross_total = sum(
        (Decimal(item.gross_total) for item in reconciled_items),
        start=Decimal(0),
    )
    item_adjustment_total = sum(
        (
            Decimal(adjustment.amount)
            for item in reconciled_items
            for adjustment in item.adjustments
        ),
        start=Decimal(0),
    )
    if not _within_tolerance(item_total, stated_total):
        errors.append(
            "sum of receipt.items final_total values must match "
            f"receipt.totals.total within {RECONCILIATION_TOLERANCE}"
        )

    totals_updates: dict[str, str] = {}
    canonical_subtotal = _format_decimal(item_gross_total)
    if receipt.totals.subtotal is None:
        totals_updates["subtotal"] = canonical_subtotal
        warnings.append("derived: receipt.totals.subtotal from item gross_total values")
    elif not _within_tolerance(
        item_gross_total,
        Decimal(receipt.totals.subtotal),
    ):
        totals_updates["subtotal"] = canonical_subtotal
        warnings.append(
            "corrected: receipt.totals.subtotal from item gross_total values"
        )

    canonical_discounts = _format_decimal(item_adjustment_total)
    if receipt.totals.discounts is None:
        totals_updates["discounts"] = canonical_discounts
        warnings.append(
            "derived: receipt.totals.discounts from item signed adjustments"
        )
    elif not _within_tolerance(
        item_adjustment_total,
        Decimal(receipt.totals.discounts),
    ):
        totals_updates["discounts"] = canonical_discounts
        warnings.append(
            "corrected: receipt.totals.discounts from item signed adjustments"
        )

    if not _within_tolerance(
        item_gross_total + item_adjustment_total,
        stated_total,
    ):
        errors.append(
            "receipt.totals.subtotal plus signed discounts must match "
            f"receipt.totals.total within {RECONCILIATION_TOLERANCE}"
        )

    if errors:
        raise SemanticValidationError(errors)

    reconciled_totals = (
        receipt.totals.model_copy(update=totals_updates)
        if totals_updates
        else receipt.totals
    )
    reconciled_receipt = receipt.model_copy(
        update={
            "items": reconciled_items,
            "totals": reconciled_totals,
        },
    )
    return ReceiptDocument(
        receipt=reconciled_receipt,
        warnings=_deduplicate(warnings),
    )


def _warn_if_missing(
    warnings: list[str],
    value: object | None,
    path: str,
) -> None:
    if value is None or (isinstance(value, str) and not value.strip()):
        warnings.append(f"missing: {path}")


def _within_tolerance(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) <= RECONCILIATION_TOLERANCE


def _format_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value, "f")


def _exact_decimal_divide(
    numerator: Decimal,
    denominator: Decimal,
) -> Decimal | None:
    """Return an exact finite base-10 quotient, or None when none exists."""
    if denominator == 0:
        return None

    quotient = Fraction(numerator) / Fraction(denominator)
    remaining_denominator = quotient.denominator
    powers_of_two = 0
    powers_of_five = 0

    while remaining_denominator % 2 == 0:
        powers_of_two += 1
        remaining_denominator //= 2
    while remaining_denominator % 5 == 0:
        powers_of_five += 1
        remaining_denominator //= 5

    if remaining_denominator != 1:
        return None

    scale = max(powers_of_two, powers_of_five)
    scaled_numerator = quotient.numerator
    scaled_numerator *= 2 ** (scale - powers_of_two)
    scaled_numerator *= 5 ** (scale - powers_of_five)
    return Decimal(scaled_numerator).scaleb(-scale)


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "DECIMAL_STRING_PATTERN",
    "RECONCILIATION_TOLERANCE",
    "Adjustment",
    "DecimalString",
    "Item",
    "Merchant",
    "NormalizedReceipt",
    "ReceiptDocument",
    "ReceiptImageTotalDocument",
    "SemanticValidationError",
    "Totals",
    "Transaction",
    "validate_and_reconcile",
]
