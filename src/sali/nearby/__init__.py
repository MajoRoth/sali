"""Nearby supermarkets: what one shopper's cart costs at the stores around them.

Cart comparison answers "which stores are cheapest" for the whole country in
catalogue terms. This package answers the question the app actually asks: given
this receipt and where I am standing, which shops can I walk to, what would this
cart cost in each, and where was it bought. That means coordinates, distances,
and an origin store — none of which the price database attaches to a cart.

The wire contract is `docs/nearby-schema.md`, whose field names deliberately
match `ui/src/lib/types.ts` so the response feeds the screens with no reshaping.
"""

from sali.nearby.models import NearbyRequest, NearbyResponse, NearbyStore
from sali.nearby.service import NearbyService

__all__ = ["NearbyRequest", "NearbyResponse", "NearbyService", "NearbyStore"]
