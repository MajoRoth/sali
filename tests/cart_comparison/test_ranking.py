"""Reading prices out of the comparison payload and ranking store carts.

The live price database currently returns no listings, so these tests state the
payload shape outright. That is the point: the ranking has to be provably right
before there is data to run it on, and it has to keep working when the payload
names its fields slightly differently.
"""

from decimal import Decimal

from sali.cart_comparison.models import AlternateProduct, CatalogProduct, MatchedLine
from sali.cart_comparison.pricing import read_store_prices
from sali.cart_comparison.ranking import rank_carts, store_directory


def comparison(barcode: int, chains: list[dict]) -> dict:
    return {
        "productBarcode": barcode,
        "productName": f"product {barcode}",
        "currentOnly": True,
        "overallStatistics": {
            "minPrice": 0.0,
            "maxPrice": 0.0,
            "avgPrice": 0.0,
            "totalPriceRange": 0.0,
            "totalStores": 0,
            "totalChains": 0,
        },
        "chainComparison": chains,
    }


def chain(
    chain_id: str,
    name: str,
    store_prices: list[dict],
    *,
    min_price: float = 0.0,
) -> dict:
    return {
        "chainId": chain_id,
        "chainName": name,
        "storeCount": len(store_prices),
        "minPrice": min_price,
        "maxPrice": min_price,
        "avgPrice": min_price,
        "priceRange": 0.0,
        "storePrices": store_prices,
    }


def matched(barcode: int, name: str, quantity: str = "1") -> MatchedLine:
    return MatchedLine(
        position=barcode % 100,
        receipt_name=name,
        receipt_code=str(barcode),
        quantity=quantity,
        paid="10.00",
        product=CatalogProduct(
            product_id=str(barcode),
            barcode=barcode,
            name=name,
            manufacturer=None,
        ),
        matched_by="barcode",
        confidence=1.0,
    )


MILK, BREAD = 7290000000001, 7290000000002


def test_store_prices_are_read_per_store_per_product() -> None:
    prices = read_store_prices(
        [
            comparison(
                MILK,
                [
                    chain(
                        "c1",
                        "שופרסל",
                        [
                            {"storeId": "s1", "storeName": "נס ציונה", "price": 6.9},
                            {"storeId": "s2", "storeName": "חולון", "price": 7.4},
                        ],
                    )
                ],
            )
        ]
    )

    assert {(price.store_id, price.price) for price in prices} == {
        ("s1", Decimal("6.9")),
        ("s2", Decimal("7.4")),
    }
    assert all(not price.chain_level for price in prices)


def test_a_chain_without_a_store_breakdown_still_competes_on_its_own_price() -> None:
    prices = read_store_prices(
        [comparison(MILK, [chain("c9", "טיב טעם", [], min_price=6.2)])]
    )

    assert len(prices) == 1
    assert prices[0].chain_level
    assert prices[0].price == Decimal("6.2")
    assert prices[0].store_id is None


def test_chain_minimum_is_retained_when_branch_prices_are_sparse() -> None:
    prices = read_store_prices(
        [
            comparison(
                MILK,
                [
                    chain(
                        "c1",
                        "x",
                        [{"storeId": "a", "price": 5.0}],
                        min_price=5.0,
                    )
                ],
            ),
            comparison(
                BREAD,
                [
                    chain(
                        "c1",
                        "x",
                        [{"storeId": "b", "price": 8.0}],
                        min_price=8.0,
                    )
                ],
            ),
        ]
    )

    complete, partial = rank_carts(
        [matched(MILK, "\u05d7\u05dc\u05d1"), matched(BREAD, "\u05dc\u05d7\u05dd")],
        prices,
    )

    assert partial == []
    physical = [cart for cart in complete if cart.store_id is not None]
    assert {cart.store_id for cart in physical} == {"a", "b"}
    assert all(cart.total == "13.00" for cart in physical)
    assert all(cart.chain_level_estimate for cart in physical)


def test_prices_survive_alternative_field_names() -> None:
    prices = read_store_prices(
        [
            comparison(
                MILK,
                [
                    chain(
                        "c1",
                        "שופרסל",
                        [
                            {
                                "store_id": "s1",
                                "name": "נס ציונה",
                                "currentPrice": "6.90",
                                "address": {"city": "נס ציונה"},
                            }
                        ],
                    )
                ],
            )
        ]
    )

    assert prices[0].store_id == "s1"
    assert prices[0].price == Decimal("6.90")
    assert prices[0].city == "נס ציונה"


def test_a_store_missing_an_item_ranks_below_every_complete_cart() -> None:
    cart = [matched(MILK, "חלב"), matched(BREAD, "לחם")]
    prices = read_store_prices(
        [
            comparison(
                MILK,
                [
                    chain(
                        "c1",
                        "שופרסל",
                        [
                            {"storeId": "cheap", "price": 5.0},
                            {"storeId": "dear", "price": 6.0},
                        ],
                    )
                ],
            ),
            comparison(
                BREAD,
                [chain("c1", "שופרסל", [{"storeId": "dear", "price": 8.0}])],
            ),
        ]
    )

    complete, partial = rank_carts(cart, prices)

    # `cheap` is cheaper on the only item it stocks, and is still the wrong shop.
    assert [store.store_id for store in complete] == ["dear"]
    assert complete[0].total == "14.00"
    assert [store.store_id for store in partial] == ["cheap"]
    assert [item.barcode for item in partial[0].missing] == [BREAD]


def test_a_fixed_deposit_charge_does_not_make_a_store_incomplete() -> None:
    deposit = matched(1000, "\u05d3\u05de\u05d9 \u05e4\u05e7\u05d3\u05d5\u05df").model_copy(
        update={"matched_by": "fixed_charge", "paid": "0.30"}
    )
    prices = read_store_prices(
        [comparison(MILK, [chain("c1", "x", [{"storeId": "a", "price": 5.0}])])]
    )

    complete, partial = rank_carts([matched(MILK, "\u05d7\u05dc\u05d1"), deposit], prices)

    assert partial == []
    assert complete[0].complete
    assert complete[0].priced_items == 2
    assert complete[0].total_items == 2
    assert complete[0].total == "5.30"


def test_complete_carts_are_ordered_by_what_the_whole_cart_costs() -> None:
    cart = [matched(MILK, "חלב"), matched(BREAD, "לחם")]
    prices = read_store_prices(
        [
            comparison(
                MILK,
                [
                    chain(
                        "c1",
                        "שופרסל",
                        [
                            {"storeId": "a", "price": 5.0},
                            {"storeId": "b", "price": 7.0},
                        ],
                    )
                ],
            ),
            comparison(
                BREAD,
                [
                    chain(
                        "c1",
                        "שופרסל",
                        [
                            {"storeId": "a", "price": 12.0},
                            {"storeId": "b", "price": 8.0},
                        ],
                    )
                ],
            ),
        ]
    )

    complete, _ = rank_carts(cart, prices)

    # `a` wins on milk but loses the cart: 17.00 against 15.00.
    assert [store.store_id for store in complete] == ["b", "a"]
    assert [store.total for store in complete] == ["15.00", "17.00"]


def test_quantity_multiplies_the_line_into_the_cart_total() -> None:
    cart = [matched(MILK, "חלב", quantity="3"), matched(BREAD, "עגבניות", "0.565")]
    prices = read_store_prices(
        [
            comparison(MILK, [chain("c1", "x", [{"storeId": "a", "price": 6.0}])]),
            comparison(BREAD, [chain("c1", "x", [{"storeId": "a", "price": 10.0}])]),
        ]
    )

    complete, _ = rank_carts(cart, prices)

    assert complete[0].total == "23.65"


def test_a_partial_cart_covering_more_of_the_shop_outranks_a_cheaper_one() -> None:
    cart = [matched(MILK, "חלב"), matched(BREAD, "לחם"), matched(3, "ביצים")]
    prices = read_store_prices(
        [
            comparison(
                MILK,
                [
                    chain(
                        "c1",
                        "x",
                        [
                            {"storeId": "broad", "price": 5.0},
                            {"storeId": "narrow", "price": 1.0},
                        ],
                    )
                ],
            ),
            comparison(BREAD, [chain("c1", "x", [{"storeId": "broad", "price": 5.0}])]),
        ]
    )

    _, partial = rank_carts(cart, prices)

    assert [store.store_id for store in partial] == ["broad", "narrow"]


def test_a_city_filter_drops_stores_elsewhere() -> None:
    cart = [matched(MILK, "חלב")]
    prices = read_store_prices(
        [
            comparison(
                MILK,
                [
                    chain(
                        "c1",
                        "x",
                        [
                            {"storeId": "tlv", "price": 5.0},
                            {"storeId": "haifa", "price": 4.0},
                        ],
                    )
                ],
            )
        ]
    )
    directory = store_directory(
        [
            {"id": "tlv", "storeName": "דיזנגוף", "address": {"city": "תל אביב"}},
            {"id": "haifa", "storeName": "חורב", "address": {"city": "חיפה"}},
        ]
    )

    complete, _ = rank_carts(cart, prices, stores=directory, city="תל אביב")

    assert [store.store_id for store in complete] == ["tlv"]
    assert complete[0].store_name == "דיזנגוף"


def test_no_listings_yields_no_carts_rather_than_an_empty_free_shop() -> None:
    complete, partial = rank_carts([matched(MILK, "חלב")], [])

    assert complete == []
    assert partial == []


def test_a_store_keying_a_line_under_its_own_code_still_supplies_it() -> None:
    # Chains key identical produce on their own internal codes. The alternate
    # is what lets a ויקטורי quote its own tomato against a receipt matched to
    # another chain's code — without it this cart would rank as incomplete.
    tomato = matched(935, "עגבניה").model_copy(
        update={
            "alternates": [
                AlternateProduct(
                    product=CatalogProduct(
                        product_id="777",
                        barcode=777,
                        name="עגבניה",
                        manufacturer=None,
                    ),
                    confidence=1.0,
                )
            ]
        }
    )
    prices = read_store_prices(
        [comparison(777, [chain("c2", "ויקטורי", [{"storeId": "s9", "price": 4.2}])])]
    )

    complete, partial = rank_carts([tomato], prices)

    assert partial == []
    assert len(complete) == 1
    assert complete[0].complete
    assert complete[0].total == "4.20"
