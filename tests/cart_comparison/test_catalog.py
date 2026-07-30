"""The Open Supermarkets client's own obligations: batching, 404s, failures."""

import httpx
import pytest

from sali.cart_comparison.catalog import CatalogUnavailableError, SupermarketsCatalog


def catalog_against(handler) -> tuple[SupermarketsCatalog, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(record))
    return SupermarketsCatalog("http://prices.test", client=client), seen


def test_a_cart_is_compared_in_batches_the_endpoint_accepts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        ids = request.url.params.get_list("product_ids")
        return httpx.Response(
            200,
            json={
                "comparisons": [
                    {"productBarcode": int(identifier)} for identifier in ids
                ]
            },
        )

    catalog, requests = catalog_against(handler)
    product_ids = [str(7290000000000 + index) for index in range(45)]

    comparisons = catalog.compare_prices(product_ids)

    # `/products/compare-prices` rejects more than 20 ids in one call, so a
    # 45-line cart has to become three requests rather than one 422.
    assert [
        len(request.url.params.get_list("product_ids")) for request in requests
    ] == [
        20,
        20,
        5,
    ]
    assert len(comparisons) == 45


def test_an_unknown_barcode_is_absence_rather_than_an_error() -> None:
    catalog, _ = catalog_against(
        lambda _request: httpx.Response(404, json={"detail": "Product not found"})
    )

    assert catalog.product_by_barcode("7290000000001") is None


def test_an_unreachable_price_database_is_reported_as_unavailable() -> None:
    def refuse(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    catalog, _ = catalog_against(refuse)

    with pytest.raises(CatalogUnavailableError):
        catalog.search_products("חלב")


def test_a_server_error_is_not_silently_read_as_no_results() -> None:
    catalog, _ = catalog_against(lambda _request: httpx.Response(500, text="boom"))

    with pytest.raises(CatalogUnavailableError):
        catalog.search_products("חלב")


def test_a_blank_search_never_reaches_the_network() -> None:
    catalog, requests = catalog_against(
        lambda _request: httpx.Response(200, json={"items": []})
    )

    assert catalog.search_products("   ") == []
    assert requests == []


def test_stores_are_narrowed_by_city_because_the_unfiltered_list_is_capped() -> None:
    catalog, requests = catalog_against(
        lambda _request: httpx.Response(200, json={"stores": [{"id": "1"}]})
    )

    catalog.stores(city="תל אביב")

    assert requests[0].url.params.get("city") == "תל אביב"
