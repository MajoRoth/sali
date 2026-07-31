from datetime import datetime

from pydantic import BaseModel


class ChainStore(BaseModel):
    id: str
    storeNumber: int
    storeName: str
    # address: Address
    lastObservedAt: datetime
    chainId: str

    class Config:
        from_attributes = True


class ChainBase(BaseModel):
    id: str
    chainCode: int
    chainName: str
    subChainCode: int
    subChainName: str
    observedAt: datetime
    storeCount: int


class Chain(ChainBase):
    stores: list[ChainStore] | None = None

    class Config:
        from_attributes = True


class ChainStatistics(BaseModel):
    storeCount: int
    currentProductListings: int


class ChainResponse(BaseModel):
    chain: Chain
    stores: list[ChainStore] | None = None
    statistics: ChainStatistics | None = None


class GetChainsResponse(BaseModel):
    chains: list[ChainResponse]
