from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Address")


@_attrs_define
class Address:
    """Address information matching Prisma model

    Attributes:
        store_address (str):
        website (str):
        city (str):
        postal_code (int):
    """

    store_address: str
    website: str
    city: str
    postal_code: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        store_address = self.store_address

        website = self.website

        city = self.city

        postal_code = self.postal_code

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "storeAddress": store_address,
                "website": website,
                "city": city,
                "postalCode": postal_code,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        store_address = d.pop("storeAddress")

        website = d.pop("website")

        city = d.pop("city")

        postal_code = d.pop("postalCode")

        address = cls(
            store_address=store_address,
            website=website,
            city=city,
            postal_code=postal_code,
        )

        address.additional_properties = d
        return address

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
