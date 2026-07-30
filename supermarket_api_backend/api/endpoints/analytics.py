from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api import deps
from schemas.analytics import (
    ChainPriceData,
    CrossChainPriceComparisonResponse,
    OverallStatistics,
    ProductPromotionsResponse,
    PromotionResponse,
)

router = APIRouter()


@router.get(
    "/price-comparison/cross-chain/{product_barcode}",
    response_model=CrossChainPriceComparisonResponse,
)
async def get_cross_chain_price_comparison(
    product_barcode: int = Path(...),
    current_only: bool = Query(True),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    # Get product info
    prod_q = text(
        "SELECT item_name, manufacturer_name FROM items WHERE item_code = :barcode"
    )
    prod_res = await db.execute(prod_q, {"barcode": str(product_barcode)})
    prod_row = prod_res.fetchone()
    prod_name = prod_row.item_name if prod_row else f"Product {product_barcode}"
    manufacturer = prod_row.manufacturer_name if prod_row else None

    # Get chain comparison data
    chain_q = text("""
        SELECT 
            t.chain_id,
            MAX(t.chain_name) as chain_name,
            COUNT(t.store_id) as store_count,
            MIN(t.item_price) as min_price,
            MAX(t.item_price) as max_price,
            AVG(t.item_price) as avg_price
        FROM (
            SELECT DISTINCT ON (sp.chain_id, sp.store_id)
                s.chain_id,
                s.chain_name,
                sp.store_id,
                sp.item_price
            FROM store_prices sp
            JOIN stores s ON sp.chain_id = s.chain_id AND sp.store_id = s.store_id
            WHERE sp.item_code = :barcode
            ORDER BY sp.chain_id, sp.store_id, sp.price_updated_at DESC
        ) t
        GROUP BY t.chain_id
    """)
    chain_res = await db.execute(chain_q, {"barcode": str(product_barcode)})
    chain_rows = chain_res.fetchall()

    comparisons = []
    overall_min = float("inf")
    overall_max = float("-inf")
    total_avg_sum = 0.0
    total_stores = 0
    total_chains = len(chain_rows)

    for row in chain_rows:
        min_p = float(row.min_price or 0)
        max_p = float(row.max_price or 0)
        avg_p = float(row.avg_price or 0)
        stores_c = row.store_count or 0

        overall_min = min(overall_min, min_p)
        overall_max = max(overall_max, max_p)
        total_avg_sum += avg_p * stores_c
        total_stores += stores_c

        comparisons.append(
            ChainPriceData(
                chainId=str(row.chain_id),
                chainName=row.chain_name or "",
                storeCount=stores_c,
                minPrice=min_p,
                maxPrice=max_p,
                avgPrice=avg_p,
                priceRange=max_p - min_p,
                storePrices=[],  # Empty for now as it would require too much data
            )
        )

    overall_avg = (total_avg_sum / total_stores) if total_stores > 0 else 0
    if overall_min == float("inf"):
        overall_min = 0
        overall_max = 0

    stats = OverallStatistics(
        minPrice=overall_min,
        maxPrice=overall_max,
        avgPrice=overall_avg,
        totalPriceRange=overall_max - overall_min,
        totalStores=total_stores,
        totalChains=total_chains,
    )

    return CrossChainPriceComparisonResponse(
        productBarcode=product_barcode,
        productName=prod_name,
        manufacturer=manufacturer,
        currentOnly=current_only,
        overallStatistics=stats,
        chainComparison=comparisons,
    )


@router.get(
    "/promotions/product/{product_barcode}", response_model=ProductPromotionsResponse
)
async def get_product_promotions(
    product_barcode: int = Path(...),
    store_id: str | None = Query(None),
    chain_id: str | None = Query(None),
    current_only: bool = Query(True),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    prod_q = text("SELECT item_name FROM items WHERE item_code = :barcode")
    prod_res = await db.execute(prod_q, {"barcode": str(product_barcode)})
    prod_row = prod_res.fetchone()
    prod_name = prod_row.item_name if prod_row else f"Product {product_barcode}"

    promo_q = text("""
        SELECT p.*
        FROM promotions p
        JOIN promotion_items pi ON p.promotion_id = pi.promotion_id
        WHERE pi.item_code = :barcode
    """)
    promo_res = await db.execute(promo_q, {"barcode": str(product_barcode)})
    promo_rows = promo_res.fetchall()

    promotions = []
    for row in promo_rows:
        now = datetime.now(UTC)
        # Mocking complex PromotionResponse fields
        promotions.append(
            PromotionResponse(
                promotion_id=row.promotion_id,
                promotion_description=row.description or "",
                promotion_start_datetime=row.start_date or now,
                promotion_end_datetime=row.end_date or now,
                promotion_update_datetime=now,
                target_population="",
                minimum_quantity_for_promo=int(row.min_qty or 0),
                maximum_quantity_for_promo=0,
                discount_rate=float(row.discount_rate or 0),
                minimum_purchase_amount=0,
                maximum_purchase_amount=0,
                additional_promo_restrictions="",
                additional_promo_text="",
                reward_type=row.reward_type or 0,
                discount_type=0,
                promotion_items="",
                clubs="",
                weight_unit="",
                is_weighted_promo=1 if row.is_weighted_promo else 0,
                item_type=0,
                gifts_items="",
                promotion_groups=[],
            )
        )

    return ProductPromotionsResponse(
        product_barcode=product_barcode,
        product_name=prod_name,
        promotions=promotions,
        total_promotions=len(promotions),
    )


@router.get("/promotions/offer-logic/{product_barcode}")
async def get_promotion_offer_logic(
    product_barcode: int = Path(...),
    store_id: str | None = Query(None),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    return {"logic": f"Buy item {product_barcode} to get a discount!"}
