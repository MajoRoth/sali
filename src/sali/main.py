import asyncio
import os
import sys

# Ensure UTF-8 output on Windows - this is added so the agent can handle the Hebrew output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from open_supermarkets_api_client import AuthenticatedClient, Client
from open_supermarkets_api_client.api.chains import list_chains
from open_supermarkets_api_client.models.get_chains_response import GetChainsResponse

BASE_URL = "https://data.openisraelisupermarkets.co.il/"


async def async_main() -> None:
    token = os.getenv("SUPERMARKET_API_KEY")
    
    if token:
        client = AuthenticatedClient(base_url=BASE_URL, token=token)
    else:
        client = Client(base_url=BASE_URL)

    print(f"Fetching available chains asynchronously from {BASE_URL}...")
    
    async with client as c:
        response: GetChainsResponse | None = await list_chains.asyncio(client=c)

    if response and response.chains:
        print(f"\nFound {len(response.chains)} chains:")
        for chain_resp in response.chains:
            chain = chain_resp.chain
            print(f"- [{chain.id}] {chain.chain_name} (Code: {chain.chain_code}, Stores: {chain.store_count})")
    else:
        print("No chains found or request failed.")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
