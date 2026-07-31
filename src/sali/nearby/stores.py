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
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from sali.cart_comparison.catalog import SupermarketsCatalog, default_catalog
from sali.cart_comparison.configuration import geocoding_base_url
from sali.cart_comparison.matching import similarity
from sali.nearby.geo import distance_meters, is_valid_coordinate

logger = logging.getLogger("sali.nearby.stores")

#: How long an assembled directory stays usable. Branch locations are close to
#: static, and the alternative is 58 upstream calls on every map open.
DIRECTORY_TTL_SECONDS = 6 * 60 * 60

#: How long an incomplete pricing index is trusted before being rebuilt. Short,
#: because the branches missing from it are disproportionately the ones that
#: carry prices, and the full TTL would hide that for most of a day.
PARTIAL_INDEX_TTL_SECONDS = 5 * 60

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
    #: True when the position is the centre of the branch's city rather than the
    #: branch itself. Good enough to answer "is this near me"; not good enough
    #: to quote a distance, so callers must say so.
    approximate_location: bool = False

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


#: Splits a directory city name into the forms a shop name might use.
#: `תל אביב - יפו` is one city that gets written three different ways.
_CITY_SEPARATORS = re.compile(r"\s*[-–,/()]\s*")

#: Shorter than this a "city" is too generic to match on safely.
_MIN_CITY_ALIAS = 3


def _city_aliases(centroids: dict[str, tuple[float, float]]) -> dict[str, str]:
    """Alias -> canonical city, for every unambiguous way to write a name.

    An alias that two different cities share is dropped rather than guessed:
    placing a shop in the wrong city is worse than not placing it at all.
    """
    claims: dict[str, set[str]] = {}
    for city in centroids:
        forms = {city, *(_CITY_SEPARATORS.split(city))}
        for form in forms:
            text = form.strip()
            if len(text) >= _MIN_CITY_ALIAS:
                claims.setdefault(text, set()).add(city)
    return {
        alias: next(iter(owners))
        for alias, owners in claims.items()
        if len(owners) == 1
    }


@dataclass(frozen=True)
class _PricingEntry:
    """How the pricing instance identifies a branch, and what it says about it."""

    chain_id: str
    store_id: str
    chain_name: str
    store_name: str = ""
    city: str | None = None
    address: str | None = None

    @property
    def text(self) -> str:
        """Everything this instance wrote about where the branch is."""
        return " ".join(part for part in (self.store_name, self.address) if part)


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
        self._catalog = catalog or default_catalog()
        # No auth header: the open instance does not want one, and sending the
        # production token to a different host would leak it.
        self._geocoder = geocoder or SupermarketsCatalog(
            geocoding_base_url(), headers={}
        )
        self._ttl = ttl_seconds
        # Re-entrant: building the pricing index derives city centroids, which
        # needs the map directory, which takes this same lock.
        self._lock = threading.RLock()
        self._pricing: dict[tuple[str, str], _PricingEntry] | None = None
        self._chain_names: dict[str, str] = {}
        self._loaded_at = 0.0
        self._geo: dict[tuple[str, str], dict[str, Any]] | None = None
        self._geo_at = 0.0
        self._reverse: dict[tuple[str, str], tuple[str, str]] = {}
        self._centroids: dict[str, tuple[float, float]] = {}
        self._aliases: dict[str, str] = {}

    # -- the map directory ---------------------------------------------------

    def _geo_stores(self) -> dict[tuple[str, str], dict[str, Any]]:
        """Every branch the map instance knows, keyed by `(chainCode, storeNumber)`.

        Assembled chain by chain rather than read from `/stores/nearby`, because
        that endpoint caps at 100 rows and — measured — does not return the
        *nearest* hundred but an arbitrary hundred. With price data covering
        only a handful of branches nationwide, an arbitrary cap is very likely
        to drop exactly the priced branch the shopper needed. This host answers
        each chain in milliseconds, so completeness is nearly free.
        """
        with self._lock:
            fresh = (
                self._geo is not None
                and (time.monotonic() - self._geo_at) < self._ttl
            )
            if fresh and self._geo is not None:
                return self._geo

        try:
            chains = self._geocoder.chains()
        except Exception:  # noqa: BLE001 - handled as "no map today"
            chains = []
        codes = [code for chain in chains if (code := _text(chain, "id"))]

        def fetch(code: str) -> list[dict[str, Any]]:
            try:
                return self._geocoder.stores(chain_id=code)
            except Exception:  # noqa: BLE001 - one bad chain must not empty the map
                logger.warning("map store fetch failed for chain %s", code)
                return []

        found: dict[tuple[str, str], dict[str, Any]] = {}
        if codes:
            with ThreadPoolExecutor(max_workers=CHAIN_FETCH_WORKERS) as pool:
                for batch in pool.map(fetch, codes):
                    for store in batch:
                        code = _text(store, "chainId")
                        number = _text(store, "storeNumber") or _text(store, "id")
                        if code and number:
                            found.setdefault((code, number), store)

        with self._lock:
            # Keep a stale directory rather than none.
            if not found and self._geo:
                logger.warning("map directory refresh returned nothing; keeping stale")
                return self._geo
            self._geo = found
            self._geo_at = time.monotonic()
        logger.info("map directory loaded: %d branches", len(found))
        return found

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

        # Warm the map directory first: deriving city centroids needs it, and
        # doing that here keeps every network call out of the locked section.
        geo = self._geo_stores()

        with self._lock:
            names = self._load_chain_names()
            pricing, complete = self._load_pricing_index()
            # Keep a stale index rather than none: an upstream hiccup should not
            # un-price a map that was priced a moment ago.
            if not pricing and self._pricing:
                logger.warning("pricing index refresh returned nothing; keeping stale")
                return self._pricing, self._chain_names

            self._pricing = pricing
            self._chain_names = names or self._chain_names
            self._reverse = {
                (entry.chain_id, entry.store_id): key
                for key, entry in pricing.items()
            }
            self._centroids = self._city_centroids(pricing, geo)
            self._aliases = _city_aliases(self._centroids)
            # A partial index is worth using now and worth replacing soon.
            self._loaded_at = time.monotonic()
            if not complete:
                self._loaded_at -= self._ttl - PARTIAL_INDEX_TTL_SECONDS
                logger.warning(
                    "pricing index is incomplete; retrying in %ds",
                    int(PARTIAL_INDEX_TTL_SECONDS),
                )
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

    def _load_pricing_index(self) -> tuple[dict[tuple[str, str], _PricingEntry], bool]:
        """The index, and whether it is complete.

        Completeness matters more than it looks. The index is cached for hours,
        so one built while the pricing instance was half-down would keep the
        branches it missed unpriceable for the rest of the day — and those are
        exactly the branches that carry price data. An incomplete index is
        therefore kept but marked, so it is retried in minutes rather than
        hours.
        """
        try:
            chains = self._catalog.chains()
        except Exception:  # noqa: BLE001 - no prices today; the map still works
            logger.warning("price instance chain list unavailable; map will be unpriced")
            return {}, False

        wanted = [
            (identifier, _text(chain, "chainCode"), _text(chain, "chainName"))
            for chain in chains
            if (identifier := _text(chain, "id"))
        ]
        if not wanted:
            return {}, False

        failures: list[str] = []

        def fetch(entry: tuple[str, str | None, str | None]) -> list[dict[str, Any]]:
            try:
                found = self._catalog.stores(chain_id=entry[0])
            except Exception:  # noqa: BLE001 - one bad chain must not empty the map
                logger.warning("store fetch failed for chain %s", entry[0])
                failures.append(entry[0])
                return []
            # The client turns a tolerated failure into an empty list, which is
            # indistinguishable here from a chain that genuinely has no stores.
            # Every real chain has at least one, so empty means it failed.
            if not found:
                failures.append(entry[0])
            return found

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
                postal = store.get("address")
                postal = postal if isinstance(postal, dict) else {}
                index.setdefault(
                    (chain_code, number),
                    _PricingEntry(
                        chain_id=chain_id,
                        store_id=store_id,
                        chain_name=chain_name or chain_code,
                        store_name=_text(store, "storeName") or "",
                        city=_place_name(_text(postal, "city")),
                        address=_place_name(_text(postal, "storeAddress")),
                    ),
                )

        complete = not failures
        logger.info(
            "pricing index built: %d branches across %d chains (%d chains failed)",
            len(index),
            len(wanted),
            len(failures),
        )
        return index, complete

    def _city_centroids(
        self,
        pricing: dict[tuple[str, str], _PricingEntry],
        geo: dict[tuple[str, str], dict[str, Any]],
    ) -> dict[str, tuple[float, float]]:
        """Where each city is, averaged over the branches we can place there.

        Neither instance publishes city coordinates, but between them they
        publish enough to derive them: the pricing instance names the city a
        branch is in, the map instance says where that branch is, and hundreds
        of branches appear in both. Averaging those gives a usable centre for
        every city either instance mentions.

        This exists so a priced branch the map instance has never heard of can
        still be placed — roughly, and flagged as rough, but placed. Otherwise
        the chains that actually carry price data are invisible, since they are
        precisely the ones missing from the map instance.
        """
        points: dict[str, list[tuple[float, float]]] = {}
        for key, entry in pricing.items():
            if not entry.city:
                continue
            raw = geo.get(key)
            if raw is None:
                continue
            coordinates = raw.get("coordinates")
            coordinates = coordinates if isinstance(coordinates, dict) else {}
            lat, lng = coordinates.get("lat"), coordinates.get("lng")
            if not is_valid_coordinate(lat, lng):
                continue
            points.setdefault(entry.city, []).append((float(lat), float(lng)))

        return {
            city: (
                sum(lat for lat, _ in found) / len(found),
                sum(lng for _, lng in found) / len(found),
            )
            for city, found in points.items()
        }

    def _city_of(self, entry: _PricingEntry) -> str | None:
        """The city a branch is in, named or inferred.

        The branches that carry price data tend to leave the city column empty
        and write it into the shop name instead — `סיטי מרקט טאוור בע"מ, משה
        דיין 2 תל אביב`. So the name is scanned for a city we know.

        Matched through aliases rather than the canonical name, because the two
        instances disagree on what a city is called: the directory says
        `תל אביב - יפו` and the shop name says `תל אביב`, and testing whether
        the long form appears in the short one finds nothing. Longest alias
        wins, so a city is never mistaken for a shorter one nested inside it.
        """
        if entry.city and entry.city in self._centroids:
            return entry.city
        text = entry.text
        if not text:
            return None
        for alias in sorted(self._aliases, key=len, reverse=True):
            if alias in text:
                return self._aliases[alias]
        return None

    # -- queries -------------------------------------------------------------

    def nearby(
        self,
        location: tuple[float, float],
        radius_m: float,
        *,
        limit: int | None = None,
    ) -> list[NearbyRecord]:
        """Located branches within `radius_m` of a point, nearest first."""
        pricing, chain_names = self._index()

        found: list[NearbyRecord] = []
        for entry in self._geo_stores().values():
            store = _located_store(entry, chain_names, pricing)
            if store is None or not store.located:
                continue
            if store.lat is None or store.lng is None:
                continue
            distance = distance_meters(location, (store.lat, store.lng))
            if distance <= radius_m:
                found.append(NearbyRecord(store, distance))

        found.sort(key=lambda record: record.distance_m)
        return found[:limit] if limit else found

    def locate(self, chain_id: str, store_id: str) -> NearbyRecord | None:
        """Place a branch the price database quoted, by its production ids.

        Needed because pricing and geography arrive in opposite directions: a
        priced store is named by the pricing instance's own ids, and only the
        map instance knows where it is. Looking it up directly means a branch
        that *has* prices is never dropped for having missed a listing query.
        """
        pricing, chain_names = self._index()
        with self._lock:
            key = self._reverse.get((chain_id, store_id))
        if key is None:
            return None

        raw = self._geo_stores().get(key)
        if raw is not None:
            store = _located_store(raw, chain_names, pricing)
            if (
                store is not None
                and store.located
                and store.lat is not None
                and store.lng is not None
            ):
                return NearbyRecord(store, 0.0)

        # The map instance has never heard of this branch. Fall back to the
        # centre of the city the pricing instance puts it in — flagged, because
        # a city centre is an answer to "roughly where", not "how far".
        entry = pricing.get(key)
        if entry is None:
            return None
        city = self._city_of(entry)
        if city is None:
            return None
        lat, lng = self._centroids[city]
        return NearbyRecord(
            StoreRecord(
                store_id=entry.store_id,
                chain_id=entry.chain_id,
                chain_name=entry.chain_name,
                store_name=entry.store_name,
                city=city,
                address=entry.address,
                lat=lat,
                lng=lng,
                priceable=True,
                approximate_location=True,
            ),
            0.0,
        )

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
