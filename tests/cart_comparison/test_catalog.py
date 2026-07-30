"""The Open Supermarkets client's own obligations: batching, 404s, failures."""

import httpx
import pytest

from sali.cart_comparison.catalog import CatalogUnavailableError, SupermarketsCatalog
from sali.cart_comparison.configuration import (
    CATALOG_RETRY_ATTEMPTS,
    CIRCUIT_BREAKER_THRESHOLD,
)


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
    # 45-line cart has to become three requests rather than one 422. Sorted
    # because the batches are issued concurrently: sizes are the contract,
    # arrival order is not.
    assert sorted(
        len(request.url.params.get_list("product_ids")) for request in requests
    ) == [5, 20, 20]
    # Every id is asked about exactly once — batching must not drop or repeat.
    asked = [
        identifier
        for request in requests
        for identifier in request.url.params.get_list("product_ids")
    ]
    assert sorted(asked) == sorted(product_ids)
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
        catalog.compare_prices(["7290000000001"])


def test_a_server_error_is_not_silently_read_as_no_prices() -> None:
    """The pricing call is the answer, so its failure has to be reported.

    Returning an empty comparison would render as "nothing you bought is sold
    anywhere nearby", which is a far worse lie than an error.
    """
    catalog, _ = catalog_against(lambda _request: httpx.Response(500, text="boom"))

    with pytest.raises(CatalogUnavailableError):
        catalog.compare_prices(["7290000000001"])


def test_a_failing_search_is_retried_then_tolerated() -> None:
    """A search improves an answer; it does not make one.

    The hosted catalogue's search occasionally 504s under load, and one slow
    lookup must not fail a fifty-line cart whose other forty-nine resolved. So
    it is retried, and if it still fails the line goes unmatched instead.
    """
    catalog, requests = catalog_against(lambda _request: httpx.Response(504))

    assert catalog.search_products("חלב") == []
    assert len(requests) == 2


def test_a_bad_request_is_not_retried() -> None:
    """4xx is a bad request, not bad luck — repeating it just costs a second."""
    catalog, requests = catalog_against(lambda _request: httpx.Response(422))

    assert catalog.search_products("חלב") == []
    assert len(requests) == 1


def test_a_transient_failure_is_recovered_by_the_retry() -> None:
    attempts: list[int] = []

    def flaky(_request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(504)
        return httpx.Response(200, json={"items": [{"id": "abc"}]})

    catalog, _ = catalog_against(flaky)

    assert catalog.search_products("חלב") == [{"id": "abc"}]


def test_a_barcode_is_looked_up_once_and_remembered() -> None:
    """The hosted catalogue takes seconds per barcode and the answer is stable."""
    catalog, requests = catalog_against(
        lambda _request: httpx.Response(200, json={"product": {"id": "abc"}})
    )

    first = catalog.product_by_barcode("7290000000001")
    second = catalog.product_by_barcode("7290000000001")

    assert first == second == {"id": "abc"}
    assert len(requests) == 1


def test_an_absent_barcode_is_remembered_too() -> None:
    """Otherwise every repeat of a product the database lacks pays full price."""
    catalog, requests = catalog_against(lambda _request: httpx.Response(404))

    assert catalog.product_by_barcode("7290000000001") is None
    assert catalog.product_by_barcode("7290000000001") is None
    assert len(requests) == 1


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


def test_a_tolerated_failure_is_not_remembered_as_absence() -> None:
    """An outage must not mark a product missing for the rest of the process.

    "The host said 404" and "the host said nothing" look the same to a caller
    but mean opposite things, and caching the second as the first would keep a
    product unpriceable long after the service came back.
    """
    calls: list[int] = []

    def flaky(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) <= 2:  # both attempts of the first lookup fail
            return httpx.Response(503)
        return httpx.Response(200, json={"product": {"id": "abc"}})

    catalog, _ = catalog_against(flaky)

    assert catalog.product_by_barcode("7290000000001") is None
    assert catalog.product_by_barcode("7290000000001") == {"id": "abc"}


def test_a_host_that_is_plainly_down_stops_being_called() -> None:
    """Fifty lookups against a dead service should not cost fifty timeouts."""
    catalog, requests = catalog_against(lambda _request: httpx.Response(503))

    for index in range(40):
        catalog.product_by_barcode(f"729000000{index:04d}")

    # Two attempts per lookup until the breaker trips, then nothing.
    assert len(requests) <= CIRCUIT_BREAKER_THRESHOLD * CATALOG_RETRY_ATTEMPTS
    assert len(requests) < 40
