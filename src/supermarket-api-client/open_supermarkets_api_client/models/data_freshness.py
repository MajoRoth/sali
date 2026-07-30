from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DataFreshness")


@_attrs_define
class DataFreshness:
    """
    Attributes:
        chain_id (str):
        chain_name (None | str):
        last_update (datetime.datetime | None):
        has_data (bool):
    """

    chain_id: str
    chain_name: None | str
    last_update: datetime.datetime | None
    has_data: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chain_id = self.chain_id

        chain_name: None | str
        chain_name = self.chain_name

        last_update: None | str
        if isinstance(self.last_update, datetime.datetime):
            last_update = self.last_update.isoformat()
        else:
            last_update = self.last_update

        has_data = self.has_data

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chainId": chain_id,
                "chainName": chain_name,
                "lastUpdate": last_update,
                "hasData": has_data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        chain_id = d.pop("chainId")

        def _parse_chain_name(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        chain_name = _parse_chain_name(d.pop("chainName"))

        def _parse_last_update(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_update_type_0 = datetime.datetime.fromisoformat(data)

                return last_update_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        last_update = _parse_last_update(d.pop("lastUpdate"))

        has_data = d.pop("hasData")

        data_freshness = cls(
            chain_id=chain_id,
            chain_name=chain_name,
            last_update=last_update,
            has_data=has_data,
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
