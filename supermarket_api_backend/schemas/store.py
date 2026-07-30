from datetime import datetime

from pydantic import BaseModel


class Address(BaseModel):
    storeAddress: str
    website: str
    city: str
    postalCode: int


class Coordinates(BaseModel):
    lat: float
    lng: float


class StoreBase(BaseModel):
    id: str
    storeNumber: int
    storeName: str
    address: Address
    coordinates: Coordinates | None = None
    lastObservedAt: datetime
    chainId: str


class Store(StoreBase):
    class Config:
        from_attributes = True


class GetStoresResponse(BaseModel):
    stores: list[Store]
