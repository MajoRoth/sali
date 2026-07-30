from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.product import ItemModel
from schemas.product import Product


def _map_item_to_product(item: ItemModel) -> Product:
    barcode = int(item.item_code) if item.item_code and item.item_code.isdigit() else 0
    qty = 0
    if item.unit_qty:
        try:
            qty = int(float(item.unit_qty))
        except ValueError:
            pass

    return Product(
        id=item.item_code,
        productBarcode=barcode,
        internalBarcode=barcode,
        productName=item.item_name or "",
        manufacturerOrImporterName=item.manufacturer_name or "",
        countryOfOrigin=item.manufacture_country or "",
        productDescription="",
        productQuantityMeasure=item.unit_of_measure or "",
        productQuantity=qty,
        unitOfMeasure=item.unit_of_measure or "",
        itemsPerPackage=1,
        isWeighted=1 if item.is_weighted else 0,
        itemType=1,
        lastUpdated=datetime.now(UTC),
    )


async def get_product_by_barcode(db: AsyncSession, barcode: int) -> Product | None:
    stmt = select(ItemModel).filter(ItemModel.item_code == str(barcode))
    result = await db.execute(stmt)
    row = result.scalars().first()
    if row:
        return _map_item_to_product(row)
    return None


async def search_products(
    db: AsyncSession, *, query: str, limit: int = 10, offset: int = 0
) -> list[Product]:
    words = query.strip().split()
    if not words:
        return []

    conditions = []
    for word in words:
        # Use .contains() instead of .ilike() for Hebrew characters
        # Postgres 'ilike' fails on non-ASCII chars if the DB collation is 'C'
        conditions.append(
            or_(
                ItemModel.item_name.contains(word),
                ItemModel.item_code.contains(word),
            )
        )

    stmt = select(ItemModel).filter(and_(*conditions)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_map_item_to_product(row) for row in rows]
