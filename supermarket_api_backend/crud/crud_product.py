from datetime import UTC, datetime

from sqlalchemy import and_, or_, select, text
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


async def get_similar_products(
    db: AsyncSession, item_code: str, limit: int = 5
) -> list[Product]:
    # Ensure the target item has an embedding
    check_stmt = text(
        "SELECT 1 FROM items WHERE item_code = :item_code AND embedding IS NOT NULL"
    )
    res = await db.execute(check_stmt, {"item_code": item_code})
    if not res.scalar():
        return []

    stmt = (
        select(ItemModel)
        .where(ItemModel.item_code != item_code, text("embedding IS NOT NULL"))
        .order_by(
            text(
                "embedding <-> (SELECT embedding FROM items WHERE item_code = :item_code)"
            )
        )
        .limit(limit)
    )
    result = await db.execute(stmt, {"item_code": item_code})
    rows = result.scalars().all()
    return [_map_item_to_product(row) for row in rows]


async def ocr_match_products(
    db: AsyncSession, item_code: str, item_name: str, item_price: float, limit: int = 5
) -> list[Product]:
    query = text("""
        SELECT i.item_code, i.is_weighted, i.manufacturer_name, i.manufacture_country,
               i.unit_of_measure, i.unit_qty, i.item_name,
               MIN(
                   SQRT(
                       POWER(CAST(levenshtein(SUBSTRING(COALESCE(i.item_code, '') FROM 1 FOR 255), SUBSTRING(:code FROM 1 FOR 255)) AS FLOAT), 2) + 
                       POWER(CAST(levenshtein(SUBSTRING(COALESCE(i.item_name, '') FROM 1 FOR 255), SUBSTRING(:name FROM 1 FOR 255)) AS FLOAT), 2) + 
                       POWER(CAST(COALESCE(sp.item_price, 0) AS FLOAT) - :price, 2)
                   )
               ) as distance
        FROM items i
        LEFT JOIN store_prices sp ON i.item_code = sp.item_code
        GROUP BY i.item_code, i.is_weighted, i.manufacturer_name, i.manufacture_country,
                 i.unit_of_measure, i.unit_qty, i.item_name
        ORDER BY distance ASC
        LIMIT :limit
    """)

    result = await db.execute(
        query,
        {"code": item_code, "name": item_name, "price": item_price, "limit": limit},
    )
    rows = result.fetchall()

    products = []
    for row in rows:
        item = ItemModel(
            item_code=row.item_code,
            is_weighted=row.is_weighted,
            manufacturer_name=row.manufacturer_name,
            manufacture_country=row.manufacture_country,
            unit_of_measure=row.unit_of_measure,
            unit_qty=row.unit_qty,
            item_name=row.item_name,
        )
        products.append(_map_item_to_product(item))
    return products
