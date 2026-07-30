from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.chain import Chain
    from ..models.chain_statistics import ChainStatistics
    from ..models.store import Store


T = TypeVar("T", bound="ChainResponse")


@_attrs_define
class ChainResponse:
    """Response for GET /chains

    Attributes:
        chain (Chain): Chain information matching Prisma model
        stores (list[Store] | None | Unset):
        statistics (ChainStatistics | None | Unset):
    """

    chain: Chain
    stores: list[Store] | None | Unset = UNSET
    statistics: ChainStatistics | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.chain_statistics import ChainStatistics

        chain = self.chain.to_dict()

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

        statistics: dict[str, Any] | None | Unset
        if isinstance(self.statistics, Unset):
            statistics = UNSET
        elif isinstance(self.statistics, ChainStatistics):
            statistics = self.statistics.to_dict()
        else:
            statistics = self.statistics

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chain": chain,
            }
        )
        if stores is not UNSET:
            field_dict["stores"] = stores
        if statistics is not UNSET:
            field_dict["statistics"] = statistics

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chain import Chain
        from ..models.chain_statistics import ChainStatistics
        from ..models.store import Store

        d = dict(src_dict)
        chain = Chain.from_dict(d.pop("chain"))

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

        def _parse_statistics(data: object) -> ChainStatistics | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                statistics_type_0 = ChainStatistics.from_dict(data)

                return statistics_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ChainStatistics | None | Unset, data)

        statistics = _parse_statistics(d.pop("statistics", UNSET))

        chain_response = cls(
            chain=chain,
            stores=stores,
            statistics=statistics,
        )

        chain_response.additional_properties = d
        return chain_response

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
