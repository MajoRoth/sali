from sqlalchemy import BigInteger, Column, Integer, String
from sqlalchemy.types import UserDefinedType

from db.base import Base


class Geometry(UserDefinedType):
    def get_col_spec(self, **kw):
        return "GEOMETRY"


class StoreModel(Base):
    __tablename__ = "stores"

    store_id = Column(Integer, primary_key=True)
    chain_id = Column(BigInteger, primary_key=True)
    sub_chain_id = Column(Integer)
    bikoret_no = Column(Integer)
    store_type = Column(Integer)
    location = Column(Geometry)
    address = Column(String)
    city = Column(String)
    zip_code = Column(String)
    chain_name = Column(String)
    sub_chain_name = Column(String)
    store_name = Column(String)
