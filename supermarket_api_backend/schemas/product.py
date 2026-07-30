from datetime import datetime

from pydantic import BaseModel


class ProductBase(BaseModel):
    id: str
    productBarcode: int
    internalBarcode: int
    productName: str
    manufacturerOrImporterName: str
    countryOfOrigin: str
    productDescription: str
    productQuantityMeasure: str
    productQuantity: int
    unitOfMeasure: str
    itemsPerPackage: int
    isWeighted: int
    itemType: int
    lastUpdated: datetime | None = None


class Product(ProductBase):
    class Config:
        from_attributes = True


class ProductBarcodeResponse(BaseModel):
    product: Product


class ProductSearchPage(BaseModel):
    items: list[Product]
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None = None
