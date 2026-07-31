from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="OverallStatistics")


@_attrs_define
class OverallStatistics:
    """
    Attributes:
        min_price (float):
        max_price (float):
        avg_price (float):
        total_price_range (float):
        total_stores (int):
        total_chains (int):
    """

    min_price: float
    max_price: float
    avg_price: float
    total_price_range: float
    total_stores: int
    total_chains: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        min_price = self.min_price

        max_price = self.max_price

        avg_price = self.avg_price

        total_price_range = self.total_price_range

        total_stores = self.total_stores

        total_chains = self.total_chains

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "minPrice": min_price,
                "maxPrice": max_price,
                "avgPrice": avg_price,
                "totalPriceRange": total_price_range,
                "totalStores": total_stores,
                "totalChains": total_chains,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        min_price = d.pop("minPrice")

        max_price = d.pop("maxPrice")

        avg_price = d.pop("avgPrice")

        total_price_range = d.pop("totalPriceRange")

        total_stores = d.pop("totalStores")

        total_chains = d.pop("totalChains")

        overall_statistics = cls(
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            total_price_range=total_price_range,
            total_stores=total_stores,
            total_chains=total_chains,
        )

        overall_statistics.additional_properties = d
        return overall_statistics

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
