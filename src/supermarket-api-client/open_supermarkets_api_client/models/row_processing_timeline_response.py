from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.site_row_processing_timeline import SiteRowProcessingTimeline


T = TypeVar("T", bound="RowProcessingTimelineResponse")


@_attrs_define
class RowProcessingTimelineResponse:
    """
    Attributes:
        start_time (datetime.datetime):
        end_time (datetime.datetime):
        bucket_minutes (int):
        timelines (list[SiteRowProcessingTimeline]):
    """

    start_time: datetime.datetime
    end_time: datetime.datetime
    bucket_minutes: int
    timelines: list[SiteRowProcessingTimeline]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        start_time = self.start_time.isoformat()

        end_time = self.end_time.isoformat()

        bucket_minutes = self.bucket_minutes

        timelines = []
        for timelines_item_data in self.timelines:
            timelines_item = timelines_item_data.to_dict()
            timelines.append(timelines_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "startTime": start_time,
                "endTime": end_time,
                "bucketMinutes": bucket_minutes,
                "timelines": timelines,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.site_row_processing_timeline import SiteRowProcessingTimeline

        d = dict(src_dict)
        start_time = datetime.datetime.fromisoformat(d.pop("startTime"))

        end_time = datetime.datetime.fromisoformat(d.pop("endTime"))

        bucket_minutes = d.pop("bucketMinutes")

        timelines = []
        _timelines = d.pop("timelines")
        for timelines_item_data in _timelines:
            timelines_item = SiteRowProcessingTimeline.from_dict(timelines_item_data)

            timelines.append(timelines_item)

        row_processing_timeline_response = cls(
            start_time=start_time,
            end_time=end_time,
            bucket_minutes=bucket_minutes,
            timelines=timelines,
        )

        row_processing_timeline_response.additional_properties = d
        return row_processing_timeline_response

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
