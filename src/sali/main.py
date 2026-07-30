import asyncio
import os
import sys

# Ensure UTF-8 output on Windows - this is added so the agent can handle the Hebrew output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from open_supermarkets_api_client import AuthenticatedClient, Client
from open_supermarkets_api_client.api.products import (
    compare_product_prices,
    get_product_by_barcode,
)

BASE_URL = "https://data.openisraelisupermarkets.co.il/"

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

        # Step 2: Compare prices
        print(f"\nComparing prices for {len(product_ids)} products...")
        response = await compare_product_prices.asyncio_detailed(client=c, product_ids=product_ids)
        
        if response.status_code == 200 and response.parsed:
            parsed = response.parsed
            if hasattr(parsed, 'comparisons') and parsed.comparisons:
                for comp in parsed.comparisons:
                    print(f"\n=== Price comparison for: {comp.product_name} (Barcode: {comp.product_barcode}) ===")
                    print(f"Overall lowest price across all chains: {comp.overall_statistics.min_price}")
                    for chain_data in comp.chain_comparison:
                        print(f"  - {chain_data.chain_name}: Min {chain_data.min_price}, Avg {chain_data.avg_price}")
            else:
                print("No comparisons found in the response.")
        else:
            print(f"Failed to compare prices. Status code: {response.status_code}")
            print(f"Error: {response.content}")


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
