from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from api import deps
from schemas.chain import ChainResponse, ChainStatistics, GetChainsResponse

router = APIRouter()


@router.get("/", response_model=GetChainsResponse)
async def list_chains(
    db: AsyncSession = Depends(deps.get_db),
    includeStores: bool | None = Query(False, description="Include store information"),
    includeStats: bool | None = Query(False, description="Include chain statistics"),
) -> Any:
    """
    Get all chains with optional store information and statistics.
    """
    chains = await crud.crud_chain.get_chains(db)

    response_chains = []
    for chain in chains:
        stores: list[Any] | None = [] if includeStores else None
        stats = (
            ChainStatistics(storeCount=chain.storeCount, currentProductListings=0)
            if includeStats
            else None
        )

        response_chains.append(
            ChainResponse(chain=chain, stores=stores, statistics=stats)
        )

    return GetChainsResponse(chains=response_chains)


@router.get("/{chain_id}", response_model=ChainResponse)
async def get_chain(
    chain_id: str,
    db: AsyncSession = Depends(deps.get_db),
    includeStores: bool | None = Query(False, description="Include store information"),
    includeStats: bool | None = Query(False, description="Include chain statistics"),
) -> Any:
    chains = await crud.crud_chain.get_chains(db)
    target = None
    for c in chains:
        if c.id == chain_id:
            target = c
            break

    if not target:
        raise HTTPException(status_code=404, detail="Chain not found")

    stores: list[Any] | None = [] if includeStores else None
    stats = (
        ChainStatistics(storeCount=target.storeCount, currentProductListings=0)
        if includeStats
        else None
    )

    return ChainResponse(chain=target, stores=stores, statistics=stats)
