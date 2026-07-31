from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from api import deps
from schemas.analytics import (
    ChainPriceData,
    ComparePricesResponse,
    CrossChainPriceComparisonResponse,
    OverallStatistics,
)
from schemas.product import Product, ProductBarcodeResponse, ProductSearchPage

router = APIRouter()


@router.get("/search", response_model=ProductSearchPage)
async def search_products(
    query: str = Query(..., description="Search query for product name"),
    store_id: str | None = Query(None, description="Filter by store ID"),
    chain_id: str | None = Query(None, description="Filter by chain ID"),
    active: bool = Query(
        False, description="Show only products that have active listing"
    ),
    limit: int = Query(10, ge=1, le=100, description="Max items (max 100)"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    products = await crud.search_products(db, query=query, limit=limit, offset=offset)

    return ProductSearchPage(
        items=products,
        limit=limit,
        offset=offset,
        has_more=len(products) == limit,
        next_offset=offset + limit if len(products) == limit else None,
    )


@router.get("/similar", response_model=list[Product])
async def get_similar_products(
    item_code: str = Query(
        ..., description="The item code to find similar products for"
    ),
    limit: int = Query(5, ge=1, le=50, description="Max items to return (max 50)"),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    return await crud.get_similar_products(db, item_code=item_code, limit=limit)


@router.get("/ocr-match", response_model=list[Product])
async def ocr_match_products(
    item_code: str = Query(..., description="The OCR read item code"),
    item_name: str = Query(..., description="The OCR read item name"),
    price: float = Query(..., description="The OCR read item price"),
    limit: int = Query(5, ge=1, le=50, description="Max items to return (max 50)"),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    return await crud.ocr_match_products(
        db, item_code=item_code, item_name=item_name, item_price=price, limit=limit
    )


@router.get("/barcode/{barcode}", response_model=ProductBarcodeResponse)
async def get_product_by_barcode(
    barcode: int = Path(...), db: AsyncSession = Depends(deps.get_db)
) -> Any:
    product = await crud.get_product_by_barcode(db, barcode)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductBarcodeResponse(product=product)


@router.get("/compare-prices", response_model=ComparePricesResponse)
async def compare_product_prices(
    product_ids: list[str] = Query(..., min_length=1, max_length=20),
    current_only: bool = Query(True),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    comparisons = []

    # 1. Check if product exists in items table
    prod_q = text(
        "SELECT item_code, item_name, manufacturer_name FROM items WHERE item_code = ANY(:barcodes)"
    )
    prod_res = await db.execute(prod_q, {"barcodes": product_ids})
    prod_rows = prod_res.fetchall()

    found_products = {str(row.item_code): row for row in prod_rows}
    not_found = [pid for pid in product_ids if pid not in found_products]

    # 2. Get chain and store prices for all found products
    prices_by_item: dict[str, list[Any]] = {}
    if found_products:
        prices_q = text("""
            SELECT DISTINCT ON (sp.item_code, sp.chain_id, sp.store_id)
                sp.item_code,
                s.chain_id,
                s.chain_name,
                sp.store_id,
                sp.item_price
            FROM store_prices sp
            JOIN stores s ON sp.chain_id = s.chain_id AND sp.store_id = s.store_id
            WHERE sp.item_code = ANY(:barcodes)
            ORDER BY sp.item_code, sp.chain_id, sp.store_id, sp.price_updated_at DESC
        """)
        prices_res = await db.execute(
            prices_q, {"barcodes": list(found_products.keys())}
        )
        prices_rows = prices_res.fetchall()

        for r in prices_rows:
            icode = str(r.item_code)
            if icode not in prices_by_item:
                prices_by_item[icode] = []
            prices_by_item[icode].append(r)

    no_listings = []

    for pid in product_ids:
        if pid in not_found:
            continue

        if pid not in prices_by_item:
            no_listings.append(pid)
            continue

        prod_row = found_products[pid]
        prod_name = prod_row.item_name or f"Product {pid}"
        manufacturer = prod_row.manufacturer_name

        # Group by chain_id
        chain_groups: dict[str, dict[str, Any]] = {}
        overall_min = float("inf")
        overall_max = float("-inf")
        total_sum = 0.0
        total_stores = 0

        for r in prices_by_item[pid]:
            cid = str(r.chain_id)
            if cid not in chain_groups:
                chain_groups[cid] = {
                    "chain_name": r.chain_name or "",
                    "store_prices": [],
                }

            price = float(r.item_price or 0)
            chain_groups[cid]["store_prices"].append(
                {"store_id": r.store_id, "price": price}
            )

            overall_min = min(overall_min, price)
            overall_max = max(overall_max, price)
            total_sum += price
            total_stores += 1

        chain_comps = []
        for cid, data in chain_groups.items():
            prices = [p["price"] for p in data["store_prices"]]
            c_min = min(prices)
            c_max = max(prices)
            c_avg = sum(prices) / len(prices)

            chain_comps.append(
                ChainPriceData(
                    chainId=cid,
                    chainName=data["chain_name"],
                    chainCode=cid,
                    storeCount=len(prices),
                    minPrice=c_min,
                    maxPrice=c_max,
                    avgPrice=c_avg,
                    priceRange=c_max - c_min,
                    storePrices=data["store_prices"],
                )
            )

        stats = OverallStatistics(
            minPrice=overall_min,
            maxPrice=overall_max,
            avgPrice=total_sum / total_stores if total_stores > 0 else 0,
            totalPriceRange=overall_max - overall_min,
            totalStores=total_stores,
            totalChains=len(chain_groups),
        )

        comparisons.append(
            CrossChainPriceComparisonResponse(
                productBarcode=int(pid) if pid.isdigit() else 0,
                productName=prod_name,
                manufacturer=manufacturer,
                currentOnly=current_only,
                overallStatistics=stats,
                chainComparison=chain_comps,
            )
        )

    return ComparePricesResponse(
        comparisons=comparisons,
        notFoundProductIds=not_found,
        productIdsWithNoListings=no_listings,
    )
