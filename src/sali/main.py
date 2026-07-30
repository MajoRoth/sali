import asyncio
import os
import sys

# Ensure UTF-8 output on Windows - this is added so the agent can handle the Hebrew output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from open_supermarkets_api_client import AuthenticatedClient, Client
from open_supermarkets_api_client.api.products import get_product_by_barcode, compare_product_prices

BASE_URL = "https://data.openisraelisupermarkets.co.il/"

async def get_list_price_per_store(client: AuthenticatedClient | Client, product_ids: list[str]) -> dict[str, float]:
    """
    Given a list of product IDs, returns a mapping from store name to the total price
    of all products in the list, but ONLY for stores that carry ALL the requested products.
    """
    response = await compare_product_prices.asyncio_detailed(client=client, product_ids=product_ids)
    if response.status_code != 200 or not response.parsed or not hasattr(response.parsed, 'comparisons') or not response.parsed.comparisons:
        return {}
        
    store_totals = {}
    store_product_counts = {}
    store_info = {}
    
    num_products = len(response.parsed.comparisons)
    
    for comp in response.parsed.comparisons:
        for chain_data in comp.chain_comparison:
            chain_name = chain_data.chain_name
            for store_price in chain_data.store_prices:
                props = store_price.additional_properties
                store_id = props.get('storeId')
                store_name = props.get('storeName', 'Unknown Store')
                price = props.get('unitPrice', 0.0) # unitPrice is the price for one unit
                
                if not store_id:
                    continue
                    
                city = props.get('city')
                city_suffix = f" ({city})" if isinstance(city, str) and city and city != "0.0" else ""
                display_name = f"{chain_name} - {store_name}{city_suffix}"
                store_info[store_id] = display_name
                
                store_totals[store_id] = store_totals.get(store_id, 0.0) + price
                store_product_counts[store_id] = store_product_counts.get(store_id, 0) + 1
            
    # Filter only stores that have all products
    valid_store_prices = {
        store_info[store_id]: round(price, 2)
        for store_id, price in store_totals.items() 
        if store_product_counts[store_id] == num_products
    }
    
    return valid_store_prices

async def async_main(product_numbers: list[str]) -> None:
    token = os.getenv("SUPERMARKET_API_KEY", "001d35a9-09fb-4805-8fe2-c86f69bc03ce")
    
    if token:
        client = AuthenticatedClient(base_url=BASE_URL, token=token, timeout=30.0)
    else:
        client = Client(base_url=BASE_URL, timeout=30.0)

    product_ids = []
    
    async with client as c:
        # Step 1: Resolve barcodes to product IDs
        for num in product_numbers:
            if num.isdigit():
                print(f"Looking up barcode {num}...")
                resp = await get_product_by_barcode.asyncio_detailed(client=c, barcode=int(num))
                if resp.status_code == 200 and resp.parsed:
                    pid = resp.parsed.product.id
                    print(f"Found product ID for {num}: {pid} ({resp.parsed.product.product_name})")
                    product_ids.append(pid)
                else:
                    print(f"Could not find barcode {num}. Status: {resp.status_code}")
            else:
                # Assume it's already a product ID
                product_ids.append(num)
                
        if not product_ids:
            print("No valid product IDs to compare.")
            return

        # Step 2: Compare prices using the new function
        print(f"\nCalculating total price per store for the list of {len(product_ids)} products...")
        store_totals = await get_list_price_per_store(client=c, product_ids=product_ids)
        
        if store_totals:
            print("\n=== Total List Price Per Store ===")
            # Sort stores by total price ascending
            sorted_stores = sorted(store_totals.items(), key=lambda x: x[1])
            for store_name, total_price in sorted_stores:
                print(f"  - {store_name}: {total_price}")
        else:
            print("\nNo stores found that carry all the requested products, or failed to fetch prices.")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: uv run python src/sali/main.py <product_number_1> <product_number_2> ...")
        # Fallback to some common defaults for demonstration
        args = ["7290000041283", "5000159028158"]
        print(f"No product numbers provided. Using defaults: {args}\n")
        
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
