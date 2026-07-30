from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.store import StoreModel
from schemas.chain import Chain


async def get_chains(db: AsyncSession, *, skip: int = 0, limit: int = 100):
    stmt = (
        select(
            StoreModel.chain_id,
            StoreModel.chain_name,
            StoreModel.sub_chain_id,
            StoreModel.sub_chain_name,
            func.count(StoreModel.store_id).label("storeCount"),
        )
        .group_by(
            StoreModel.chain_id,
            StoreModel.chain_name,
            StoreModel.sub_chain_id,
            StoreModel.sub_chain_name,
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    chains = []
    for row in rows:
        chains.append(
            Chain(
                id=str(row.chain_id),
                chainCode=row.chain_id,
                chainName=row.chain_name or "",
                subChainCode=row.sub_chain_id or 0,
                subChainName=row.sub_chain_name or "",
                observedAt=datetime.now(UTC),
                storeCount=row.storeCount,
                stores=None,
            )
        )
    return chains
