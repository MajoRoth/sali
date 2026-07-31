"""The cart comparison a shopper gets back for one extracted receipt."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from sali.receipt_extraction.models import CurrencyCode, DecimalString, NonEmptyText


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


type MatchMethod = Literal["barcode", "name"]


class CatalogProduct(_StrictModel):
    """A product in the price database that a receipt line was matched to."""

    product_id: NonEmptyText
    barcode: int
    name: str
    manufacturer: str | None


class AlternateProduct(_StrictModel):
    """Another catalogue product that reads the same receipt line equally well.

    Produce is the reason this exists: every chain keys its bananas on its own
    internal code, so the single best match can only ever be priced inside one
    chain, and every other chain shows the line as unavailable. An alternate is
    admitted only when it is as good a reading of the receipt text as the
    primary, or confidently good on its own — never as a looser guess.
    """

    product: CatalogProduct
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    is_substitution: bool = False


class MatchedLine(_StrictModel):
    """A receipt line resolved to a catalogue product."""

    position: int
    receipt_name: NonEmptyText
    receipt_code: NonEmptyText | None
    quantity: DecimalString
    paid: DecimalString
    product: CatalogProduct
    matched_by: MatchMethod
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    #: Equally-valid catalogue readings of this line, used so a store that
    #: stocks the same thing under a different code can still price it.
    alternates: list[AlternateProduct] = []


class UnmatchedLine(_StrictModel):
    """A receipt line that could not be resolved to a catalogue product."""

    position: int
    receipt_name: NonEmptyText
    receipt_code: NonEmptyText | None
    paid: DecimalString
    reason: NonEmptyText


class MissingProduct(_StrictModel):
    """A matched product a store has no current price for."""

    barcode: int
    name: str


class StoreCart(_StrictModel):
    """What one store would charge for the matched part of the cart."""

    store_id: str | None
    store_name: str | None
    city: str | None
    address: str | None
    chain_id: NonEmptyText
    chain_name: str
    #: Priced against every matched product, so the cart can be paid in one shop.
    complete: bool
    priced_items: int
    total_items: int
    total: DecimalString
    missing: list[MissingProduct]
    #: True when the total is built from a chain-wide price rather than this
    #: store's own, because the price database gave no per-store breakdown.
    chain_level_estimate: bool


class CartComparison(_StrictModel):
    """The ranked answer: who stocks the whole cart, cheapest first."""

    schema_version: Literal["1.0"] = "1.0"
    currency: CurrencyCode | None
    receipt_total: DecimalString | None
    matched: list[MatchedLine]
    unmatched: list[UnmatchedLine]
    #: Stores carrying every matched product first, cheapest first; then the
    #: best partial carts, each naming what it could not price.
    complete_carts: list[StoreCart]
    partial_carts: list[StoreCart]
    warnings: list[str]


__all__ = [
    "AlternateProduct",
    "CartComparison",
    "CatalogProduct",
    "MatchedLine",
    "MissingProduct",
    "StoreCart",
    "UnmatchedLine",
]
