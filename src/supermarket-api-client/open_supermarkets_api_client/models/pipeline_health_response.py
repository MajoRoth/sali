from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.chain_data_status import ChainDataStatus
    from ..models.pipeline_health_response_datasourcestats import PipelineHealthResponseDatasourcestats


T = TypeVar("T", bound="PipelineHealthResponse")


@_attrs_define
class PipelineHealthResponse:
    """
    Attributes:
        status (str):
        last_overall_update (datetime.datetime | None):
        hours_since_last_update (float | None):
        total_chains (int):
        chains_with_recent_data (int):
        chains_with_stale_data (int):
        chain_statuses (list[ChainDataStatus]):
        data_source_stats (PipelineHealthResponseDatasourcestats):
    """

    status: str
    last_overall_update: datetime.datetime | None
    hours_since_last_update: float | None
    total_chains: int
    chains_with_recent_data: int
    chains_with_stale_data: int
    chain_statuses: list[ChainDataStatus]
    data_source_stats: PipelineHealthResponseDatasourcestats
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        last_overall_update: None | str
        if isinstance(self.last_overall_update, datetime.datetime):
            last_overall_update = self.last_overall_update.isoformat()
        else:
            last_overall_update = self.last_overall_update

        hours_since_last_update: float | None
        hours_since_last_update = self.hours_since_last_update

        total_chains = self.total_chains

        chains_with_recent_data = self.chains_with_recent_data

        chains_with_stale_data = self.chains_with_stale_data

        chain_statuses = []
        for chain_statuses_item_data in self.chain_statuses:
            chain_statuses_item = chain_statuses_item_data.to_dict()
            chain_statuses.append(chain_statuses_item)

        data_source_stats = self.data_source_stats.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "lastOverallUpdate": last_overall_update,
                "hoursSinceLastUpdate": hours_since_last_update,
                "totalChains": total_chains,
                "chainsWithRecentData": chains_with_recent_data,
                "chainsWithStaleData": chains_with_stale_data,
                "chainStatuses": chain_statuses,
                "dataSourceStats": data_source_stats,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chain_data_status import ChainDataStatus
        from ..models.pipeline_health_response_datasourcestats import PipelineHealthResponseDatasourcestats

        d = dict(src_dict)
        status = d.pop("status")

        def _parse_last_overall_update(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_overall_update_type_0 = datetime.datetime.fromisoformat(data)

                return last_overall_update_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        last_overall_update = _parse_last_overall_update(d.pop("lastOverallUpdate"))

        def _parse_hours_since_last_update(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        hours_since_last_update = _parse_hours_since_last_update(d.pop("hoursSinceLastUpdate"))

        total_chains = d.pop("totalChains")

        chains_with_recent_data = d.pop("chainsWithRecentData")

        chains_with_stale_data = d.pop("chainsWithStaleData")

        chain_statuses = []
        _chain_statuses = d.pop("chainStatuses")
        for chain_statuses_item_data in _chain_statuses:
            chain_statuses_item = ChainDataStatus.from_dict(chain_statuses_item_data)

            chain_statuses.append(chain_statuses_item)

        data_source_stats = PipelineHealthResponseDatasourcestats.from_dict(d.pop("dataSourceStats"))

        pipeline_health_response = cls(
            status=status,
            last_overall_update=last_overall_update,
            hours_since_last_update=hours_since_last_update,
            total_chains=total_chains,
            chains_with_recent_data=chains_with_recent_data,
            chains_with_stale_data=chains_with_stale_data,
            chain_statuses=chain_statuses,
            data_source_stats=data_source_stats,
        )

        pipeline_health_response.additional_properties = d
        return pipeline_health_response

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
