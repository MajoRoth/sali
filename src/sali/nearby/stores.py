"""The store directory: the branches around a shopper, and how to price them.

This is where the two deployments are stitched together, because neither can
answer the question alone (see `sali.cart_comparison.configuration`):

* **Where the shops are** comes from the open instance's `/stores/nearby`,
  which takes a lat/lng and a radius and answers in milliseconds. It is the
  only store query that accepts coordinates — `/stores/` unfiltered caps at 100
  rows nationwide, and its `city=` filter needs a municipality name that a
  phone reporting GPS does not have.
* **Which of those shops can be priced** comes from the production instance,
  whose `compare-prices` reports totals against its own opaque store ids.

The join is `(chainCode, storeNumber)` — the chain's GLN plus the branch number
the chain itself assigns. Both deployments publish those, and together they
identify a branch independently of either one's internal ids.

The pricing index costs one request per chain, so it is cached for the process
and built lazily. When it cannot be built the map still works: branches are
shown with their real names and locations, and nothing is priced. That degrades
in the right direction — an unpriced map is useful, an empty one is not.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from sali.cart_comparison.catalog import SupermarketsCatalog
from sali.cart_comparison.configuration import geocoding_base_url
from sali.cart_comparison.matching import similarity
from sali.nearby.geo import distance_meters, is_valid_coordinate

logger = logging.getLogger("sali.nearby.stores")

#: How long an assembled directory stays usable. Branch locations are close to
#: static, and the alternative is 58 upstream calls on every map open.
DIRECTORY_TTL_SECONDS = 6 * 60 * 60

#: Chains are fetched concurrently. Kept modest deliberately: this is somebody
#: else's unauthenticated service and a map open should not look like a flood.
CHAIN_FETCH_WORKERS = 8

#: A branch this far from the receipt's merchant name is not that merchant.
#: Origin resolution prefers a wrong answer of "we don't know" over naming the
#: shopper's receipt after a shop they have never been to.
MIN_ORIGIN_NAME_SCORE = 0.4

#: The chain has to stand on its own before a branch name is allowed to help.
#: Without this, `סופר-פארם` matches `גוד פארם` on the shared word `פארם` and a
#: Super-Pharm receipt is filed under a competitor — the branch score should
#: only ever choose *between* branches of a chain the receipt already named.
MIN_ORIGIN_CHAIN_SCORE = 0.5

#: How far from the shopper the origin branch may sit and still be identified
#: by proximity. A receipt is usually from somewhere they actually go.
ORIGIN_SEARCH_RADIUS_M = 25_000


@dataclass(frozen=True)
class StoreRecord:
    """One branch, as the app needs it: identified, named, and placed.

    `chain_id` and `store_id` are the *production* ids when this branch could be
    matched to the pricing instance, because those are what a priced cart comes
    back keyed on. When it could not, they fall back to the open instance's own
    ids: the branch is still a real shop worth drawing on the map, it just has
    no prices attached.
    """

    store_id: str
    chain_id: str
    chain_name: str
    store_name: str
    city: str | None
    address: str | None
    lat: float | None
    lng: float | None
    #: True when `chain_id`/`store_id` are production ids a cart can be priced
    #: against. False means map-only.
    priceable: bool = False

    @property
    def located(self) -> bool:
        return is_valid_coordinate(self.lat, self.lng)


@dataclass(frozen=True)
class NearbyRecord:
    """A branch inside the search radius, with how far away it is."""

    store: StoreRecord
    distance_m: float


def _text(source: dict[str, Any], key: str) -> str | None:
    value = source.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return None


#: Values the upstream `city` column uses for "no city", none of which are one.
#: They arrive as text, so only reading them tells them apart from a place name.
_NON_CITIES = frozenset({"nan", "none", "null", "n/a", "-", "0"})


def _place_name(value: str | None) -> str | None:
    """A city name, or None when the column holds a postcode or a null marker.

    Roughly a third of branches carry `nan`, a bare postal code, or a float in
    their city field. Shown as-is that reads as a real place — "טיב טעם, 5000.0"
    — so anything that is not word-like is dropped rather than displayed.
    """
    if value is None:
        return None
    text = value.strip()
    if not text or text.casefold() in _NON_CITIES:
        return None
    # A city name contains letters; a postcode, a float, and a store number
    # do not.
    return text if any(character.isalpha() for character in text) else None


@dataclass(frozen=True)
class _PricingEntry:
    """How the pricing instance identifies a branch the map instance found."""

    chain_id: str
    store_id: str
    chain_name: str


def _located_store(
    raw: dict[str, Any],
    chain_names: dict[str, str],
    pricing: dict[tuple[str, str], _PricingEntry],
) -> StoreRecord | None:
    """Read one branch from the map instance, priced if we can price it."""
    chain_code = _text(raw, "chainId")
    store_number = _text(raw, "storeNumber") or _text(raw, "id")
    if not chain_code or not store_number:
        return None

    address = raw.get("address")
    address = address if isinstance(address, dict) else {}
    coordinates = raw.get("coordinates")
    coordinates = coordinates if isinstance(coordinates, dict) else {}
    lat = coordinates.get("lat")
    lng = coordinates.get("lng")

    entry = pricing.get((chain_code, store_number))
    return StoreRecord(
        store_id=entry.store_id if entry else store_number,
        chain_id=entry.chain_id if entry else chain_code,
        chain_name=(entry.chain_name if entry else None)
        or chain_names.get(chain_code)
        or chain_code,
        store_name=_text(raw, "storeName") or "",
        city=_place_name(_text(address, "city")),
        address=_place_name(_text(address, "storeAddress")),
        lat=float(lat) if isinstance(lat, int | float) else None,
        lng=float(lng) if isinstance(lng, int | float) else None,
        priceable=entry is not None,
    )


class StoreDirectory:
    """The branches around a shopper, located and — where possible — priceable."""

    def __init__(
        self,
        catalog: SupermarketsCatalog | None = None,
        *,
        geocoder: SupermarketsCatalog | None = None,
        ttl_seconds: float = DIRECTORY_TTL_SECONDS,
    ) -> None:
        self._catalog = catalog or SupermarketsCatalog()
        # No auth header: the open instance does not want one, and sending the
        # production token to a different host would leak it.
        self._geocoder = geocoder or SupermarketsCatalog(
            geocoding_base_url(), headers={}
        )
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._pricing: dict[tuple[str, str], _PricingEntry] | None = None
        self._chain_names: dict[str, str] = {}
        self._loaded_at = 0.0

    # -- the pricing index ---------------------------------------------------

    def _index(self) -> tuple[dict[tuple[str, str], _PricingEntry], dict[str, str]]:
        """`(chainCode, storeNumber)` -> the pricing instance's own ids.

        Built once and reused: it is one request per chain against a service
        that is slow on a good day. An empty index is a normal outcome, not an
        error — it means today's map is unpriced.
        """
        with self._lock:
            fresh = (
                self._pricing is not None
                and (time.monotonic() - self._loaded_at) < self._ttl
            )
            if fresh and self._pricing is not None:
                return self._pricing, self._chain_names

            names = self._load_chain_names()
            pricing = self._load_pricing_index()
            # Keep a stale index rather than none: an upstream hiccup should not
            # un-price a map that was priced a moment ago.
            if not pricing and self._pricing:
                logger.warning("pricing index refresh returned nothing; keeping stale")
                return self._pricing, self._chain_names

            self._pricing = pricing
            self._chain_names = names or self._chain_names
            self._loaded_at = time.monotonic()
            return pricing, self._chain_names

    def _load_chain_names(self) -> dict[str, str]:
        """Chain names keyed by chain code, from whichever instance answers.

        The map instance is asked because it is the one that is reliably up, and
        it keys chains on the same code its stores carry.
        """
        names: dict[str, str] = {}
        try:
            chains = self._geocoder.chains()
        except Exception:  # noqa: BLE001 - a nameless chain still draws on a map
            logger.warning("chain list unavailable; branches will show their code")
            return names
        for chain in chains:
            code = _text(chain, "chainCode") or _text(chain, "id")
            name = _text(chain, "chainName")
            if code and name and code not in names:
                names[code] = name
        return names

    def _load_pricing_index(self) -> dict[tuple[str, str], _PricingEntry]:
        try:
            chains = self._catalog.chains()
        except Exception:  # noqa: BLE001 - no prices today; the map still works
            logger.warning("price instance chain list unavailable; map will be unpriced")
            return {}

        wanted = [
            (identifier, _text(chain, "chainCode"), _text(chain, "chainName"))
            for chain in chains
            if (identifier := _text(chain, "id"))
        ]
        if not wanted:
            return {}

        def fetch(entry: tuple[str, str | None, str | None]) -> list[dict[str, Any]]:
            try:
                return self._catalog.stores(chain_id=entry[0])
            except Exception:  # noqa: BLE001 - one bad chain must not empty the map
                logger.warning("store fetch failed for chain %s", entry[0])
                return []

        with ThreadPoolExecutor(max_workers=CHAIN_FETCH_WORKERS) as pool:
            batches = list(pool.map(fetch, wanted))

        index: dict[tuple[str, str], _PricingEntry] = {}
        for (chain_id, chain_code, chain_name), stores in zip(
            wanted, batches, strict=True
        ):
            if not chain_code:
                continue
            for store in stores:
                number = _text(store, "storeNumber")
                store_id = _text(store, "id")
                if not number or not store_id:
                    continue
                index.setdefault(
                    (chain_code, number),
                    _PricingEntry(chain_id, store_id, chain_name or chain_code),
                )

        logger.info("pricing index built: %d branches", len(index))
        return index

    # -- queries -------------------------------------------------------------

    def nearby(
        self,
        location: tuple[float, float],
        radius_m: float,
        *,
        limit: int | None = None,
    ) -> list[NearbyRecord]:
        """Located branches within `radius_m` of a point, nearest first."""
        raw = self._geocoder.stores_nearby(location[0], location[1], radius_m)
        if not raw:
            return []

        pricing, chain_names = self._index()

        seen: set[tuple[str, str]] = set()
        found: list[NearbyRecord] = []
        for entry in raw:
            store = _located_store(entry, chain_names, pricing)
            if store is None or not store.located:
                continue
            if store.lat is None or store.lng is None:
                continue
            # A store id is only unique within its chain.
            key = (store.chain_id, store.store_id)
            if key in seen:
                continue
            seen.add(key)
            distance = distance_meters(location, (store.lat, store.lng))
            # The endpoint filters the radius itself, but it is not this app's
            # rounding, so the boundary is enforced here too.
            if distance <= radius_m:
                found.append(NearbyRecord(store, distance))

        found.sort(key=lambda record: record.distance_m)
        return found[:limit] if limit else found

    def resolve_origin(
        self,
        merchant_name: str | None,
        branch_name: str | None,
        location: tuple[float, float] | None,
    ) -> NearbyRecord | None:
        """Find the branch a receipt was bought at.

        Scored on the merchant name against the chain, and the branch text
        against the store name, because a receipt names its shop the way a
        cashier would and the directory names it the way a database would.
        Proximity breaks ties but never creates a match on its own: the nearest
        supermarket to the shopper is not evidence about where they shopped.
        """
        if not merchant_name and not branch_name:
            return None
        if location is None:
            # Every branch we can name is one we found by looking near a point.
            return None

        nearby = self.nearby(location, ORIGIN_SEARCH_RADIUS_M)
        candidates = [record.store for record in nearby]
        if not candidates:
            return None

        best: StoreRecord | None = None
        best_score = 0.0
        for store in candidates:
            chain_score = (
                similarity(merchant_name, store.chain_name) if merchant_name else 0.0
            )
            # A receipt that names no merchant can still be placed by its branch
            # text alone; one that names a *different* merchant cannot.
            if merchant_name and chain_score < MIN_ORIGIN_CHAIN_SCORE:
                continue

            branch_score = max(
                similarity(branch_name, store.store_name) if branch_name else 0.0,
                similarity(branch_name, store.city or "") if branch_name else 0.0,
            )
            # The chain has to be right for the branch to mean anything, so it
            # carries the weight; the branch only distinguishes between shops of
            # a chain the receipt already named.
            score = chain_score * 0.7 + branch_score * 0.3 if merchant_name else branch_score
            if score > best_score:
                best, best_score = store, score

        if best is None or best_score < MIN_ORIGIN_NAME_SCORE:
            return None

        distance = (
            distance_meters(location, (best.lat, best.lng))
            if location is not None and best.located
            and best.lat is not None and best.lng is not None
            else float("nan")
        )
        return NearbyRecord(best, distance)


def default_directory() -> StoreDirectory:
    """The process-wide directory, so the 58-call assembly happens once."""
    global _DIRECTORY
    if _DIRECTORY is None:
        ttl = os.environ.get("SALI_STORE_DIRECTORY_TTL_SECONDS")
        _DIRECTORY = StoreDirectory(
            ttl_seconds=float(ttl) if ttl and ttl.strip() else DIRECTORY_TTL_SECONDS
        )
    return _DIRECTORY


_DIRECTORY: StoreDirectory | None = None


__all__ = [
    "DIRECTORY_TTL_SECONDS",
    "MIN_ORIGIN_NAME_SCORE",
    "NearbyRecord",
    "StoreDirectory",
    "StoreRecord",
    "default_directory",
]
