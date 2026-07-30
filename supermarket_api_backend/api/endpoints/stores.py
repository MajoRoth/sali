from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from api import deps
from schemas.store import GetStoresResponse

router = APIRouter()


@router.get("/", response_model=GetStoresResponse)
async def list_stores(
    db: AsyncSession = Depends(deps.get_db),
    chain_id: str | None = Query(None, description="Filter by chainId or chainCode"),
    product_id: str | None = Query(None, description="Filter by productId"),
    city: str | None = Query(None, description="Filter by city"),
) -> Any:
    """
    Get all stores with optional filtering.
    """
    stores = await crud.get_stores(db, chain_id=chain_id, city=city)
    return GetStoresResponse(stores=stores)


@router.get("/nearby", response_model=GetStoresResponse)
async def get_stores_nearby(
    lat: float = Query(..., description="Latitude of the center point"),
    lng: float = Query(..., description="Longitude of the center point"),
    radius: float = Query(..., description="Radius in meters to search within"),
    db: AsyncSession = Depends(deps.get_db),
    chain_id: str | None = Query(None, description="Filter by chainId or chainCode"),
) -> Any:
    """
    Get all stores within a given radius (in meters) of a location.
    """
    stores = await crud.get_stores(
        db, chain_id=chain_id, lat=lat, lng=lng, radius=radius
    )
    return GetStoresResponse(stores=stores)
