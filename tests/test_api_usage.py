import os
import sys

import pytest

# Ensure Hebrew characters can be printed on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from open_supermarkets_api_client import AuthenticatedClient, Client
from open_supermarkets_api_client.api.products import (
    compare_product_prices,
    get_product_by_barcode,
    search_products,
)
from open_supermarkets_api_client.api.stores import list_stores

BASE_URL = "https://data.openisraelisupermarkets.co.il/"

@pytest.fixture
def api_client(request):
    """Fixture that provides an authenticated client if a key is available, else an anonymous client."""
    token = request.config.getoption("--api-key") or os.getenv("SUPERMARKET_API_KEY")
    if token:
        return AuthenticatedClient(base_url=BASE_URL, token=token, timeout=30.0)
    return Client(base_url=BASE_URL, timeout=30.0)


@pytest.mark.asyncio
async def test_search_products(api_client):
    """Usage example for searching products."""
    query = "milk"
    
    async with api_client as c:
        response = await search_products.asyncio_detailed(client=c, query=query, limit=5)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error content: {response.content}")
        
    assert response.status_code == 200
    parsed = response.parsed
    assert hasattr(parsed, 'items')
    print(f"\nFound {len(parsed.items)} products for query '{query}'")
    for item in parsed.items:
        print(f"Product: {item.product_name} - Barcode: {item.product_barcode}")


@pytest.mark.asyncio
async def test_get_product_by_barcode(api_client):
    """Usage example for retrieving a specific product by its barcode."""
    barcode = 7290000041283
    
    async with api_client as c:
        response = await get_product_by_barcode.asyncio_detailed(client=c, barcode=barcode)
    
    if response.status_code == 200:
        parsed = response.parsed
        print(f"\nProduct details for {barcode}: {parsed.product.item_name}")
        assert str(parsed.product.item_code) == str(barcode)
    else:
        print(f"\nBarcode {barcode} not found in this environment. Status code: {response.status_code}")


@pytest.mark.asyncio
async def test_compare_product_prices(api_client):
    """Usage example for comparing a product's price across different stores/chains."""
    async with api_client as c:
        search_resp = await search_products.asyncio(client=c, query="milk", limit=1)
        if not search_resp or not search_resp.items:
            print("No product found to compare prices.")
            return

        product_id = search_resp.items[0].id
        response = await compare_product_prices.asyncio_detailed(client=c, product_ids=[product_id])
    
    if response.status_code == 200:
        parsed = response.parsed
        print(f"\nPrice comparison for product {product_id}:")
        assert hasattr(parsed, 'comparisons')
        if parsed.comparisons:
            comp = parsed.comparisons[0]
            print(f"Overall lowest price is {comp.overall_statistics.min_price}")
            for chain_data in comp.chain_comparison:
                print(f"Chain {chain_data.chain_name}: Min {chain_data.min_price}, Avg {chain_data.avg_price}")
    else:
        print(f"\nCould not find prices for {product_id}. Status code: {response.status_code}")


@pytest.mark.asyncio
async def test_list_stores(api_client):
    """Usage example for listing all stores."""
    async with api_client as c:
        response = await list_stores.asyncio_detailed(client=c)
        
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error content: {response.content}")
        
    assert response.status_code == 200
    parsed = response.parsed
    assert hasattr(parsed, 'stores')
    print(f"\nFetched {len(parsed.stores)} stores.")
    # Print the first 10
    for store in parsed.stores[:10]:
        print(f"Store: {store.store_name} (ID: {store.id}) in {store.address.city}")
