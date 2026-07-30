from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.store import StoreModel
from schemas.store import Address, Coordinates, Store


async def get_stores(
    db: AsyncSession,
    *,
    chain_id: str | None = None,
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius: float | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Store]:

    query = select(
        StoreModel,
        func.ST_X(StoreModel.location).label("lng"),
        func.ST_Y(StoreModel.location).label("lat"),
    )

    if chain_id and chain_id.isdigit():
        query = query.filter(StoreModel.chain_id == int(chain_id))
    if city:
        query = query.filter(StoreModel.city == city)
    if lat is not None and lng is not None and radius is not None:
        query = query.filter(
            text(
                "ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius)"
            ).bindparams(lng=lng, lat=lat, radius=radius)
        )

    result = await db.execute(query.offset(skip).limit(limit))
    rows = result.all()

    stores = []
    for row in rows:
        store_model = row[0]
        lng = row.lng
        lat = row.lat

        postal = 0
        if store_model.zip_code and store_model.zip_code.isdigit():
            postal = int(store_model.zip_code)

        coords = None
        if lng is not None and lat is not None:
            coords = Coordinates(lat=lat, lng=lng)

        stores.append(
            Store(
                id=str(store_model.store_id),
                storeNumber=store_model.store_id,
                storeName=store_model.store_name or "",
                address=Address(
                    storeAddress=store_model.address or "",
                    website="",
                    city=store_model.city or "",
                    postalCode=postal,
                ),
                coordinates=coords,
                lastObservedAt=datetime.now(UTC),
                chainId=str(store_model.chain_id),
            )
        )
    return stores
