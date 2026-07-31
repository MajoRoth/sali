from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.chain_response import ChainResponse


T = TypeVar("T", bound="GetChainsResponse")


@_attrs_define
class GetChainsResponse:
    """
    Attributes:
        chains (list[ChainResponse]):
    """

    chains: list[ChainResponse]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chains = []
        for chains_item_data in self.chains:
            chains_item = chains_item_data.to_dict()
            chains.append(chains_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chains": chains,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chain_response import ChainResponse

        d = dict(src_dict)
        chains = []
        _chains = d.pop("chains")
        for chains_item_data in _chains:
            chains_item = ChainResponse.from_dict(chains_item_data)

            chains.append(chains_item)

        get_chains_response = cls(
            chains=chains,
        )

        get_chains_response.additional_properties = d
        return get_chains_response

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
