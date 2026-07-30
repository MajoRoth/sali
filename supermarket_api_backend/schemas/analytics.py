from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OverallStatistics(BaseModel):
    minPrice: float
    maxPrice: float
    avgPrice: float
    totalPriceRange: float
    totalStores: int
    totalChains: int


class ChainPriceData(BaseModel):
    chainId: str
    chainName: str
    chainCode: str | None = None
    storeCount: int
    minPrice: float
    maxPrice: float
    avgPrice: float
    priceRange: float
    storePrices: list[dict[str, Any]]


class CrossChainPriceComparisonResponse(BaseModel):
    productBarcode: int
    productName: str
    manufacturer: str | None = None
    currentOnly: bool
    overallStatistics: OverallStatistics
    chainComparison: list[ChainPriceData]


class ComparePricesResponse(BaseModel):
    comparisons: list[CrossChainPriceComparisonResponse]
    notFoundProductIds: list[str] = []
    productIdsWithNoListings: list[str] = []


class PromotionItemResponse(BaseModel):
    item_code: str
    product_barcode: int
    reward_type: int
    min_quantity: int
    max_quantity: int
    discount_rate: float
    discounted_price: float
    original_price: float
    item_name: str
    item_description: str
    item_type: int


class PromotionGroupResponse(BaseModel):
    group_id: str
    group_name: str
    min_purchase_amount: float
    discount_type: int
    promotion_items: list[PromotionItemResponse]


class PromotionResponse(BaseModel):
    promotion_id: int
    promotion_description: str
    promotion_start_datetime: datetime
    promotion_end_datetime: datetime
    promotion_update_datetime: datetime
    target_population: str
    minimum_quantity_for_promo: int
    maximum_quantity_for_promo: int
    discount_rate: float
    minimum_purchase_amount: float
    maximum_purchase_amount: float
    additional_promo_restrictions: str
    additional_promo_text: str
    reward_type: int
    discount_type: int
    promotion_items: str
    clubs: str
    weight_unit: str
    is_weighted_promo: int
    item_type: int
    gifts_items: str
    promotion_groups: list[PromotionGroupResponse]


class ProductPromotionsResponse(BaseModel):
    product_barcode: int
    product_name: str
    promotions: list[PromotionResponse]
    total_promotions: int
