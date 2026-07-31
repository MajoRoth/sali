"""Simulated prices: off by default, honest when on, stable while you look at it.

The whole risk this module carries is that invented numbers get mistaken for
real ones, so every test here is really the same test asked a different way.
"""

from sali.nearby import fallback
from sali.nearby.stores import NearbyRecord, StoreRecord
from tests.cart_comparison.test_service import document


def branch(store_id: str, chain: str = "שופרסל", name: str = "רמת גן") -> NearbyRecord:
    return NearbyRecord(
        StoreRecord(
            store_id=store_id,
            chain_id="7290027600007",
            chain_name=chain,
            store_name=name,
            city="רמת גן",
            address="ביאליק 1",
            lat=32.07,
            lng=34.82,
            priceable=False,
        ),
        distance_m=420.0,
    )


CART = [
    ("חלב תנובה 3%", "7290000000001", "2", "12.90"),
    ("לחם אחיד", "7290000000002", "1", "7.50"),
    ("קוטג' 5%", "7290000000003", "3", "19.80"),
]


def test_simulation_is_off_unless_asked_for(monkeypatch) -> None:
    """A deployment that does nothing must never quietly invent prices."""
    monkeypatch.delenv("SALI_FALLBACK_PRICES", raising=False)
    assert fallback.enabled() is False

    monkeypatch.setenv("SALI_FALLBACK_PRICES", "1")
    assert fallback.enabled() is True

    # Anything that is not an affirmative is off — including "0" and "false",
    # which a careless deploy script is far more likely to set than to unset.
    for value in ("0", "false", "no", "", "off"):
        monkeypatch.setenv("SALI_FALLBACK_PRICES", value)
        assert fallback.enabled() is False, value


def test_every_simulated_store_is_flagged_as_simulated() -> None:
    """The flag is what lets the UI label the screen; without it this is a lie."""
    stores = fallback.simulated_stores(document(CART), [branch("1"), branch("2")], limit=10)

    assert stores
    assert all(store.simulated for store in stores)


def test_simulated_prices_do_not_move_between_renders() -> None:
    """A comparison whose numbers change when you look away is worse than none."""
    doc = document(CART)
    branches = [branch("1"), branch("2"), branch("3")]

    first = fallback.simulated_stores(doc, branches, limit=10)
    second = fallback.simulated_stores(doc, branches, limit=10)

    assert [store.same_cart.total for store in first] == [
        store.same_cart.total for store in second
    ]


def test_simulated_stores_differ_from_each_other() -> None:
    """Otherwise the comparison screen has nothing to compare."""
    stores = fallback.simulated_stores(
        document(CART), [branch(str(index)) for index in range(6)], limit=10
    )

    assert len({store.same_cart.total for store in stores}) > 1


def test_simulated_totals_stay_near_what_was_actually_paid() -> None:
    """Grounded in the receipt so the screens look real; not so loose they lie."""
    doc = document(CART)
    paid = float(doc.receipt.totals.total)

    stores = fallback.simulated_stores(
        doc, [branch(str(index)) for index in range(8)], limit=10
    )

    for store in stores:
        # Only the available lines are totalled, so a store missing a line is
        # legitimately cheaper — the bound is a sanity check, not arithmetic.
        assert 0 < store.same_cart.total <= paid * 1.3


def test_simulation_never_recommends_a_substitution() -> None:
    """Telling someone to buy a different product on invented prices is the one
    thing this module must not do."""
    stores = fallback.simulated_stores(
        document(CART), [branch(str(index)) for index in range(5)], limit=10
    )

    assert all(store.optimal_cart.swaps == [] for store in stores)
    assert all(store.optimal_cart.savings_vs_same_cart == 0.0 for store in stores)


def test_simulation_needs_real_branches_to_stand_on() -> None:
    """The branches are real even when the money is not; with none, there is
    nothing honest left to show."""
    assert fallback.simulated_stores(document(CART), [], limit=10) == []


def test_the_branch_details_are_the_real_ones() -> None:
    stores = fallback.simulated_stores(document(CART), [branch("7")], limit=10)

    assert stores[0].chain == "שופרסל"
    assert stores[0].branch == "רמת גן"
    assert stores[0].city == "רמת גן"
    assert stores[0].distance_m == 420.0
