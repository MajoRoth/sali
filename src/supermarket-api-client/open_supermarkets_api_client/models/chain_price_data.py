from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.chain_price_data_store_prices_item import ChainPriceDataStorePricesItem


T = TypeVar("T", bound="ChainPriceData")


@_attrs_define
class ChainPriceData:
    """Chain price data for comparison

    Attributes:
        chain_id (str):
        chain_name (str):
        chain_code (None | str):
        store_count (int):
        min_price (float):
        max_price (float):
        avg_price (float):
        price_range (float):
        store_prices (list[ChainPriceDataStorePricesItem]):
    """

    chain_id: str
    chain_name: str
    chain_code: None | str
    store_count: int
    min_price: float
    max_price: float
    avg_price: float
    price_range: float
    store_prices: list[ChainPriceDataStorePricesItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chain_id = self.chain_id

        chain_name = self.chain_name

        chain_code: None | str
        chain_code = self.chain_code

        store_count = self.store_count

        min_price = self.min_price

        max_price = self.max_price

        avg_price = self.avg_price

        price_range = self.price_range

        store_prices = []
        for store_prices_item_data in self.store_prices:
            store_prices_item = store_prices_item_data.to_dict()
            store_prices.append(store_prices_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chainId": chain_id,
                "chainName": chain_name,
                "chainCode": chain_code,
                "storeCount": store_count,
                "minPrice": min_price,
                "maxPrice": max_price,
                "avgPrice": avg_price,
                "priceRange": price_range,
                "storePrices": store_prices,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chain_price_data_store_prices_item import ChainPriceDataStorePricesItem

        d = dict(src_dict)
        chain_id = d.pop("chainId")

        chain_name = d.pop("chainName")

        def _parse_chain_code(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        chain_code = _parse_chain_code(d.pop("chainCode"))

        store_count = d.pop("storeCount")

        min_price = d.pop("minPrice")

        max_price = d.pop("maxPrice")

        avg_price = d.pop("avgPrice")

        price_range = d.pop("priceRange")

        store_prices = []
        _store_prices = d.pop("storePrices")
        for store_prices_item_data in _store_prices:
            store_prices_item = ChainPriceDataStorePricesItem.from_dict(store_prices_item_data)

            store_prices.append(store_prices_item)

        chain_price_data = cls(
            chain_id=chain_id,
            chain_name=chain_name,
            chain_code=chain_code,
            store_count=store_count,
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            price_range=price_range,
            store_prices=store_prices,
        )

        chain_price_data.additional_properties = d
        return chain_price_data

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
