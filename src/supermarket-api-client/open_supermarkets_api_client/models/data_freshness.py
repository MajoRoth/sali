from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DataFreshness")


@_attrs_define
class DataFreshness:
    """
    Attributes:
        chain_id (str):
        has_data (bool):
        chain_name (None | str | Unset):
        last_update (datetime.datetime | None | Unset):
    """

    chain_id: str
    has_data: bool
    chain_name: None | str | Unset = UNSET
    last_update: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chain_id = self.chain_id

        has_data = self.has_data

        chain_name: None | str | Unset
        if isinstance(self.chain_name, Unset):
            chain_name = UNSET
        else:
            chain_name = self.chain_name

        last_update: None | str | Unset
        if isinstance(self.last_update, Unset):
            last_update = UNSET
        elif isinstance(self.last_update, datetime.datetime):
            last_update = self.last_update.isoformat()
        else:
            last_update = self.last_update

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chainId": chain_id,
                "hasData": has_data,
            }
        )
        if chain_name is not UNSET:
            field_dict["chainName"] = chain_name
        if last_update is not UNSET:
            field_dict["lastUpdate"] = last_update

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        chain_id = d.pop("chainId")

        has_data = d.pop("hasData")

        def _parse_chain_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        chain_name = _parse_chain_name(d.pop("chainName", UNSET))

        def _parse_last_update(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_update_type_0 = datetime.datetime.fromisoformat(data)

                return last_update_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        last_update = _parse_last_update(d.pop("lastUpdate", UNSET))

        data_freshness = cls(
            chain_id=chain_id,
            has_data=has_data,
            chain_name=chain_name,
            last_update=last_update,
        )

        data_freshness.additional_properties = d
        return data_freshness

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
