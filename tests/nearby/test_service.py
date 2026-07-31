"""Pricing a receipt's cart at the branches around the shopper.

These tests stub the matcher and the price database outright, because what they
check is the assembly: which product a store's cart line shows, what a swap is
measured against, and what the warnings admit to.
"""

from sali.cart_comparison.matching import LineMatch
from sali.cart_comparison.models import AlternateProduct, CatalogProduct
from sali.nearby.models import GeoPoint
from sali.nearby.service import NearbyService
from sali.nearby.stores import NearbyRecord, StoreRecord
from tests.cart_comparison.test_ranking import chain, comparison
from tests.cart_comparison.test_service import FakeCatalog, document

HERE = GeoPoint(lat=32.0, lng=34.78)


def catalogue(product_id: str, barcode: int, name: str) -> CatalogProduct:
    return CatalogProduct(
        product_id=product_id, barcode=barcode, name=name, manufacturer=None
    )


class FakeMatcher:
    """Hands back exactly the matches a test declares, one per receipt line."""

    def __init__(self, matches: list[LineMatch]) -> None:
        self._matches = matches

    def match_all(self, items: list) -> list[LineMatch]:
        assert len(items) == len(self._matches)
        return self._matches


class FakeDirectory:
    """A map with exactly the branches a test placed on it."""

    def __init__(self, records: list[NearbyRecord]) -> None:
        self._records = records

    def nearby(self, location, radius_m, *, limit=None):
        return self._records

    def locate(self, chain_id: str, store_id: str):
        return None

    def resolve_origin(self, merchant_name, branch_name, location):
        return None


def branch(chain_id: str, store_id: str, chain_name: str) -> NearbyRecord:
    return NearbyRecord(
        StoreRecord(
            store_id=store_id,
            chain_id=chain_id,
            chain_name=chain_name,
            store_name="סניף",
            city=None,
            address=None,
            lat=32.0,
            lng=34.78,
            priceable=True,
        ),
        distance_m=120.0,
    )


def test_a_store_pricing_only_the_alternate_still_supplies_the_line() -> None:
    doc = document([("עגבניה", "18", "1", "3.10")])
    matcher = FakeMatcher(
        [
            LineMatch(
                catalogue("935", 935, "עגבניה"),
                "name",
                1.0,
                None,
                (AlternateProduct(product=catalogue("777", 777, "עגבניה"), confidence=1.0),),
            )
        ]
    )
    catalog = FakeCatalog(
        comparisons=[
            comparison(777, [chain("c1", "ויקטורי", [{"storeId": "1", "price": 4.2}])])
        ]
    )
    service = NearbyService(
        catalog=catalog,
        matcher=matcher,
        directory=FakeDirectory([branch("c1", "1", "ויקטורי")]),
    )

    response = service.price(doc, location=HERE, radius_m=5000)

    assert len(response.stores) == 1
    store = response.stores[0]
    assert store.same_cart.coverage == 1.0
    line = store.same_cart.items[0]
    # The cart shows what the store actually sells: the alternate, under its
    # own code and confidence, not the primary product this store never quoted.
    assert line.available
    assert line.barcode == "777"
    assert line.match_confidence == 1.0
    assert store.same_cart.total == 4.2
    # Every chain with a branch here quoted something, so nothing to disclose.
    assert not any("published no price" in warning for warning in response.warnings)


def test_a_fixed_deposit_is_available_and_included_in_every_store_total() -> None:
    doc = document(
        [
            ("\u05d7\u05dc\u05d1", "7290000000001", "1", "6.90"),
            ("דמי פקדון 0.30 שח", "1000", "1", "0.30"),
        ]
    )
    matcher = FakeMatcher(
        [
            LineMatch(
                catalogue("7290000000001", 7290000000001, "\u05d7\u05dc\u05d1"),
                "barcode",
                1.0,
                None,
            ),
            LineMatch(
                catalogue("fixed-charge:2", 1000, doc.receipt.items[1].name),
                "fixed_charge",
                1.0,
                None,
            ),
        ]
    )
    catalog = FakeCatalog(
        comparisons=[
            comparison(
                7290000000001,
                [
                    chain(
                        "c1",
                        "\u05e1\u05d8\u05d5\u05e4\u05de\u05e8\u05e7\u05d8",
                        [{"storeId": "1", "price": 5.0}],
                    )
                ],
            )
        ]
    )
    service = NearbyService(
        catalog=catalog,
        matcher=matcher,
        directory=FakeDirectory(
            [branch("c1", "1", "\u05e1\u05d8\u05d5\u05e4\u05de\u05e8\u05e7\u05d8")]
        ),
    )

    response = service.price(doc, location=HERE, radius_m=5000)

    store = response.stores[0]
    assert store.same_cart.coverage == 1.0
    assert store.same_cart.unavailable_count == 0
    assert store.same_cart.total == 5.3
    assert store.same_cart.items[1].available
    assert store.same_cart.items[1].line_total == 0.3


def test_same_chain_minimum_fills_a_sparse_branch_price() -> None:
    doc = document(
        [
            ("\u05d7\u05dc\u05d1", "7290000000001", "1", "6.90"),
            ("\u05dc\u05d7\u05dd", "7290000000002", "1", "8.50"),
        ]
    )
    matcher = FakeMatcher(
        [
            LineMatch(
                catalogue("7290000000001", 7290000000001, "\u05d7\u05dc\u05d1"),
                "barcode",
                1.0,
                None,
            ),
            LineMatch(
                catalogue("7290000000002", 7290000000002, "\u05dc\u05d7\u05dd"),
                "barcode",
                1.0,
                None,
            ),
        ]
    )
    catalog = FakeCatalog(
        comparisons=[
            comparison(
                7290000000001,
                [chain("c1", "x", [{"storeId": "1", "price": 5.0}], min_price=5.0)],
            ),
            comparison(
                7290000000002,
                [chain("c1", "x", [{"storeId": "2", "price": 8.0}], min_price=8.0)],
            ),
        ]
    )
    service = NearbyService(
        catalog=catalog,
        matcher=matcher,
        directory=FakeDirectory([branch("c1", "1", "x")]),
    )

    response = service.price(doc, location=HERE, radius_m=5000)

    store = next(store for store in response.stores if store.store_id == "1")
    assert store.same_cart.coverage == 1.0
    assert store.same_cart.unavailable_count == 0
    assert store.same_cart.total == 13.0
    assert store.chain_level_estimate


def test_a_swap_is_measured_against_the_price_the_cart_shows() -> None:
    # The store sells the line as the 4.0 alternate. A 6.0 lookalike is not a
    # saving against that, even though it undercuts the 10.0 primary — applying
    # it would make the "optimal" cart cost more than the same cart.
    doc = document([("קוטג תנובה", "18", "1", "5.90")])
    matcher = FakeMatcher(
        [
            LineMatch(
                catalogue("100", 100, "קוטג תנובה"),
                "name",
                1.0,
                None,
                (AlternateProduct(product=catalogue("200", 200, "קוטג תנובה"), confidence=1.0),),
            )
        ]
    )
    catalog = FakeCatalog(
        by_query={"קוטג תנובה": [{"id": "300", "productBarcode": 300, "productName": "קוטג תנובה", "manufacturerOrImporterName": ""}]},
        comparisons=[
            comparison(100, [chain("c1", "ויקטורי", [{"storeId": "1", "price": 10.0}])]),
            comparison(200, [chain("c1", "ויקטורי", [{"storeId": "1", "price": 4.0}])]),
            comparison(300, [chain("c1", "ויקטורי", [{"storeId": "1", "price": 6.0}])]),
        ],
    )
    service = NearbyService(
        catalog=catalog,
        matcher=matcher,
        directory=FakeDirectory([branch("c1", "1", "ויקטורי")]),
    )

    response = service.price(doc, location=HERE, radius_m=5000)

    store = response.stores[0]
    assert store.same_cart.total == 4.0
    assert store.optimal_cart.swaps == []
    assert store.optimal_cart.total == store.same_cart.total


def test_branches_of_chains_that_quoted_nothing_are_disclosed() -> None:
    doc = document([("עגבניה", "18", "1", "3.10")])
    matcher = FakeMatcher([LineMatch(catalogue("935", 935, "עגבניה"), "name", 1.0, None)])
    catalog = FakeCatalog(
        comparisons=[
            comparison(935, [chain("c1", "ויקטורי", [{"storeId": "1", "price": 3.0}])])
        ]
    )
    service = NearbyService(
        catalog=catalog,
        matcher=matcher,
        directory=FakeDirectory(
            [branch("c1", "1", "ויקטורי"), branch("shufersal", "9", "שופרסל")]
        ),
    )

    response = service.price(doc, location=HERE, radius_m=5000)

    assert any(
        "1 of 2 branches within your radius belong to chains that published no "
        "price" in warning
        for warning in response.warnings
    )


def test_cart_preserves_an_unmatched_line_as_unavailable_and_counts_it() -> None:
    """Global catalogue misses remain visible and reduce full-cart coverage."""
    doc = document(
        [
            ("עגבניה", "18", "1", "3.10"),
            ("מרשמלו", None, "1", "7.90"),
            ("שוקולד חלב", "21", "1", "5.90"),
        ]
    )
    matcher = FakeMatcher(
        [
            LineMatch(catalogue("935", 935, "עגבניה"), "barcode", 1.0, None),
            # The middle line resolves to nothing and drops out of every cart.
            LineMatch(None, None, 0.0, "no catalogue match"),
            LineMatch(catalogue("880", 880, "שוקולד חלב"), "barcode", 1.0, None),
        ]
    )
    catalog = FakeCatalog(
        comparisons=[
            comparison(935, [chain("c1", "ויקטורי", [{"storeId": "1", "price": 3.0}])]),
            comparison(880, [chain("c1", "ויקטורי", [{"storeId": "1", "price": 8.9}])]),
        ]
    )
    service = NearbyService(
        catalog=catalog,
        matcher=matcher,
        directory=FakeDirectory([branch("c1", "1", "ויקטורי")]),
    )

    response = service.price(doc, location=HERE, radius_m=5000)

    store = response.stores[0]
    assert [line.position for line in store.same_cart.items] == [1, 2, 3]
    assert [line.position for line in store.optimal_cart.items] == [1, 2, 3]
    missing = store.same_cart.items[1]
    assert not missing.available
    assert missing.line_total is None
    assert store.same_cart.unavailable_count == 1
    assert store.same_cart.coverage == 0.6667

    chocolate = store.same_cart.items[2]
    assert chocolate.name == "שוקולד חלב"
    assert chocolate.unit_price == 8.9

    # The origin basket carries every receipt line, positions included, so the
    # UI can join against it too.
    assert response.origin is not None
    assert [line.position for line in response.origin.same_cart.items] == [1, 2, 3]


def test_no_swap_cart_sums_the_same_rounded_line_amounts_in_both_totals() -> None:
    """Two half-unit lines cannot create a phantom one-cent price difference."""
    doc = document(
        [
            ("Weighted one", "7290000000001", "0.5", "1.67"),
            ("Weighted two", "7290000000002", "0.5", "1.67"),
        ]
    )
    matcher = FakeMatcher(
        [
            LineMatch(
                catalogue("7290000000001", 7290000000001, "Weighted one"),
                "barcode",
                1.0,
                None,
            ),
            LineMatch(
                catalogue("7290000000002", 7290000000002, "Weighted two"),
                "barcode",
                1.0,
                None,
            ),
        ]
    )
    catalog = FakeCatalog(
        comparisons=[
            comparison(
                7290000000001,
                [chain("c1", "x", [{"storeId": "1", "price": 3.33}])],
            ),
            comparison(
                7290000000002,
                [chain("c1", "x", [{"storeId": "1", "price": 3.33}])],
            ),
        ]
    )
    service = NearbyService(
        catalog=catalog,
        matcher=matcher,
        directory=FakeDirectory([branch("c1", "1", "x")]),
    )

    store = service.price(doc, location=HERE, radius_m=5000).stores[0]

    assert [line.line_total for line in store.same_cart.items] == [1.67, 1.67]
    assert store.same_cart.total == 3.34
    assert store.optimal_cart.total == 3.34
    assert store.optimal_cart.savings_vs_same_cart == 0.0
    assert store.optimal_cart.swaps == []
