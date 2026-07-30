from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.store import Store


T = TypeVar("T", bound="Chain")


@_attrs_define
class Chain:
    """Chain information matching Prisma model

    Attributes:
        id (str):
        chain_code (int):
        chain_name (str):
        sub_chain_code (int):
        sub_chain_name (str):
        observed_at (datetime.datetime):
        store_count (int):
        stores (list[Store] | None | Unset):
    """

    id: str
    chain_code: int
    chain_name: str
    sub_chain_code: int
    sub_chain_name: str
    observed_at: datetime.datetime
    store_count: int
    stores: list[Store] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        chain_code = self.chain_code

        chain_name = self.chain_name

        sub_chain_code = self.sub_chain_code

        sub_chain_name = self.sub_chain_name

        observed_at = self.observed_at.isoformat()

        store_count = self.store_count

        stores: list[dict[str, Any]] | None | Unset
        if isinstance(self.stores, Unset):
            stores = UNSET
        elif isinstance(self.stores, list):
            stores = []
            for stores_type_0_item_data in self.stores:
                stores_type_0_item = stores_type_0_item_data.to_dict()
                stores.append(stores_type_0_item)

        else:
            stores = self.stores

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "chainCode": chain_code,
                "chainName": chain_name,
                "subChainCode": sub_chain_code,
                "subChainName": sub_chain_name,
                "observedAt": observed_at,
                "storeCount": store_count,
            }
        )
        if stores is not UNSET:
            field_dict["stores"] = stores

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.store import Store

        d = dict(src_dict)
        id = d.pop("id")

        chain_code = d.pop("chainCode")

        chain_name = d.pop("chainName")

        sub_chain_code = d.pop("subChainCode")

        sub_chain_name = d.pop("subChainName")

        observed_at = datetime.datetime.fromisoformat(d.pop("observedAt"))

        store_count = d.pop("storeCount")

        def _parse_stores(data: object) -> list[Store] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                stores_type_0 = []
                _stores_type_0 = data
                for stores_type_0_item_data in _stores_type_0:
                    stores_type_0_item = Store.from_dict(stores_type_0_item_data)

                    stores_type_0.append(stores_type_0_item)

                return stores_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[Store] | None | Unset, data)

        stores = _parse_stores(d.pop("stores", UNSET))

        chain = cls(
            id=id,
            chain_code=chain_code,
            chain_name=chain_name,
            sub_chain_code=sub_chain_code,
            sub_chain_name=sub_chain_name,
            observed_at=observed_at,
            store_count=store_count,
            stores=stores,
        )

        chain.additional_properties = d
        return chain

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
