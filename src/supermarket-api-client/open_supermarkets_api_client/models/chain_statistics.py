from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ChainStatistics")


@_attrs_define
class ChainStatistics:
    """Chain statistics

    Attributes:
        store_count (int):
        current_product_listings (int):
    """

    store_count: int
    current_product_listings: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        store_count = self.store_count

        current_product_listings = self.current_product_listings

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "storeCount": store_count,
                "currentProductListings": current_product_listings,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        store_count = d.pop("storeCount")

        current_product_listings = d.pop("currentProductListings")

        chain_statistics = cls(
            store_count=store_count,
            current_product_listings=current_product_listings,
        )

        chain_statistics.additional_properties = d
        return chain_statistics

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
