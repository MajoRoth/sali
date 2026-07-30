from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.address import Address


T = TypeVar("T", bound="Store")


@_attrs_define
class Store:
    """Store information matching Prisma model

    Attributes:
        id (str):
        store_number (int):
        store_name (str):
        address (Address): Address information matching Prisma model
        last_observed_at (datetime.datetime):
        chain_id (str):
    """

    id: str
    store_number: int
    store_name: str
    address: Address
    last_observed_at: datetime.datetime
    chain_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        store_number = self.store_number

        store_name = self.store_name

        address = self.address.to_dict()

        last_observed_at = self.last_observed_at.isoformat()

        chain_id = self.chain_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "storeNumber": store_number,
                "storeName": store_name,
                "address": address,
                "lastObservedAt": last_observed_at,
                "chainId": chain_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.address import Address

        d = dict(src_dict)
        id = d.pop("id")

        store_number = d.pop("storeNumber")

        store_name = d.pop("storeName")

        address = Address.from_dict(d.pop("address"))

        last_observed_at = datetime.datetime.fromisoformat(d.pop("lastObservedAt"))

        chain_id = d.pop("chainId")

        store = cls(
            id=id,
            store_number=store_number,
            store_name=store_name,
            address=address,
            last_observed_at=last_observed_at,
            chain_id=chain_id,
        )

        store.additional_properties = d
        return store

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
