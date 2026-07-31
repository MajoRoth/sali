"""The wire contract for nearby-store pricing, per `docs/nearby-schema.md`.

These models are camelCase on the wire while the rest of this API is
snake_case. That is deliberate and confined to this one endpoint family: the
contract was written down before either side was built, its field names match
`ui/src/lib/types.ts` so the response feeds the screens without reshaping, and
a checked-in contract someone may already be coding against is worth more than
uniformity. Python-side names stay snake_case, so only the JSON differs.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from sali.receipt_extraction.models import ReceiptDocument

#: The units a cart line can be quantified in, as named by the contract.
type MeasureUnit = Literal["unit", "kg", "g", "l", "ml"]

#: Why a swap was proposed. Only `cheaper_similar` is produced today; the rest
#: are contract vocabulary for substitutions this service cannot yet justify.
type SwapReason = Literal[
    "cheaper_similar",
    "store_brand",
    "promotion",
    "larger_pack_unit_price",
]


class _Wire(BaseModel):
    """Strict, camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class GeoPoint(_Wire):
    lat: Annotated[float, Field(ge=-90.0, le=90.0)]
    lng: Annotated[float, Field(ge=-180.0, le=180.0)]


class NearbyRequest(_Wire):
    """Price an already-extracted receipt against the stores around a shopper."""

    document: ReceiptDocument
    location: GeoPoint
    #: How far a shopper is willing to travel. Beyond a few tens of km the
    #: answer stops being actionable, so the ceiling is a product decision
    #: rather than a technical one.
    radius_m: Annotated[int, Field(gt=0, le=50_000)] = 5_000
    limit: Annotated[int, Field(gt=0, le=200)] = 30
    include_online: bool = False
    allow_substitutions: bool = True


class NearbyUrlRequest(_Wire):
    """Extract a Digital Receipt and price it against nearby stores in one call."""

    url: str
    location: GeoPoint
    radius_m: Annotated[int, Field(gt=0, le=50_000)] = 5_000
    limit: Annotated[int, Field(gt=0, le=200)] = 30
    include_online: bool = False
    allow_substitutions: bool = True


class CartLine(_Wire):
    """One receipt line as one store would sell it.

    `position` is the join key back to the receipt, and it is not decoration.
    A store cart holds only the lines that could be matched, so a cart of 22
    lines can answer a receipt of 23. Anything pairing the two by list index
    silently shifts every line after the first unmatched one, and compares a
    shopper's chocolate against what they paid for dish soap.
    """

    #: The receipt line this answers, as printed on it (`Item.position`).
    position: int
    barcode: str
    name: str
    qty: float
    unit: MeasureUnit
    #: null when this store has no current price for the product.
    unit_price: float | None
    line_total: float | None
    available: bool
    #: Present only when the receipt line was resolved by name rather than by
    #: barcode, so the UI can mark a line that might be the wrong variant.
    match_confidence: float | None = None
    is_substitution: bool = False


class Cart(_Wire):
    """A priced basket at one store. `total` sums only the available lines."""

    items: list[CartLine]
    total: float
    unavailable_count: int
    #: available / requested, in 0..1. Compare stores on this before price: a
    #: cart is always cheapest when it is missing the expensive things.
    coverage: float


class Swap(_Wire):
    """A cheaper product this store stocks that stands in for a cart line."""

    from_: Annotated[dict[str, object], Field(alias="from")]
    to: dict[str, object]
    qty: float
    unit: MeasureUnit
    line_savings: float
    reason: SwapReason
    category: str | None = None
    similarity: float | None = None
    is_substitution: bool = False


class OptimalCart(Cart):
    """The same basket after swapping in cheaper equivalents."""

    swaps: list[Swap]
    savings_vs_same_cart: float


class NearbyStore(_Wire):
    """One store the shopper could buy this cart at."""

    store_id: str
    chain: str
    branch: str
    online: bool
    #: null for online-only stores, and for branches the price database has no
    #: usable coordinates for.
    location: GeoPoint | None
    distance_m: float | None
    delivery_fee: float
    city: str | None = None
    address: str | None = None
    #: True when the totals come from a chain-wide price because the price
    #: database returned no per-store breakdown for this branch.
    chain_level_estimate: bool = False

    #: True when these totals are simulated rather than read from the price
    #: database — see `sali.nearby.fallback`. The branch is real; the money is
    #: not. Clients must label it; they must never present it as a real price.
    simulated: bool = False

    #: True when `location` is the centre of the branch's city rather than the
    #: branch itself, because no coordinates are published for it. `distanceM`
    #: is null in that case: the city is known, the walk is not.
    approximate_location: bool = False

    same_cart: Cart
    optimal_cart: OptimalCart


class UnmatchedCartLine(_Wire):
    """A receipt line no catalogue product could be found for."""

    position: int
    name: str
    code: str | None
    paid: float
    reason: str


class NearbyResponse(_Wire):
    """The answer the three app screens render."""

    schema_version: Literal["1.0"] = "1.0"
    computed_at: str
    currency: str
    #: Where the receipt was bought, at the price actually paid. Resolved to a
    #: real branch when the merchant on the receipt can be found near enough to
    #: name one; otherwise it still carries the receipt's own merchant text.
    origin: NearbyStore | None
    #: Ranked cheapest-first on `optimalCart.total`, complete carts before
    #: partial ones.
    stores: list[NearbyStore]
    unmatched: list[UnmatchedCartLine]
    #: Anything a shopper should not have to infer. When the price database has
    #: no listings this is where that is said out loud, and `stores` is empty
    #: rather than invented.
    warnings: list[str]
    #: Real branches inside the radius, whether or not any price was found for
    #: them. The map still has something true to show when pricing comes back
    #: empty.
    stores_in_radius: int


__all__ = [
    "Cart",
    "CartLine",
    "GeoPoint",
    "NearbyRequest",
    "NearbyResponse",
    "NearbyStore",
    "NearbyUrlRequest",
    "OptimalCart",
    "Swap",
    "UnmatchedCartLine",
]
