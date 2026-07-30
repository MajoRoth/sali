from sqlalchemy import Column, DateTime, Integer, String

from db.base import Base


class Chain(Base):
    __tablename__ = "chains"

    id = Column(String, primary_key=True, index=True)
    chainCode = Column(Integer, index=True, nullable=False)
    chainName = Column(String, nullable=False)
    subChainCode = Column(Integer, nullable=False)
    subChainName = Column(String, nullable=False)
    observedAt = Column(DateTime, nullable=False)
    storeCount = Column(Integer, default=0, nullable=False)

    # Example relationship
    # stores = relationship("Store", back_populates="chain")
