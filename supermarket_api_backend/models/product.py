from sqlalchemy import Boolean, Column, String

from db.base import Base


class ItemModel(Base):
    __tablename__ = "items"

    item_code = Column(String, primary_key=True)
    is_weighted = Column(Boolean)
    manufacturer_name = Column(String)
    manufacture_country = Column(String)
    unit_of_measure = Column(String)
    unit_qty = Column(String)
    item_name = Column(String)
