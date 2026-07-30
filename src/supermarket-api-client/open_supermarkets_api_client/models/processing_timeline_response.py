from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.site_processing_timeline import SiteProcessingTimeline


T = TypeVar("T", bound="ProcessingTimelineResponse")


@_attrs_define
class ProcessingTimelineResponse:
    """
    Attributes:
        start_time (datetime.datetime):
        end_time (datetime.datetime):
        bucket_minutes (int):
        use_extracted_date (bool):
        timelines (list[SiteProcessingTimeline]):
    """

    start_time: datetime.datetime
    end_time: datetime.datetime
    bucket_minutes: int
    use_extracted_date: bool
    timelines: list[SiteProcessingTimeline]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        start_time = self.start_time.isoformat()

        end_time = self.end_time.isoformat()

        bucket_minutes = self.bucket_minutes

        use_extracted_date = self.use_extracted_date

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
                "useExtractedDate": use_extracted_date,
                "timelines": timelines,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.site_processing_timeline import SiteProcessingTimeline

        d = dict(src_dict)
        start_time = datetime.datetime.fromisoformat(d.pop("startTime"))

        end_time = datetime.datetime.fromisoformat(d.pop("endTime"))

        bucket_minutes = d.pop("bucketMinutes")

        use_extracted_date = d.pop("useExtractedDate")

        timelines = []
        _timelines = d.pop("timelines")
        for timelines_item_data in _timelines:
            timelines_item = SiteProcessingTimeline.from_dict(timelines_item_data)

            timelines.append(timelines_item)

        processing_timeline_response = cls(
            start_time=start_time,
            end_time=end_time,
            bucket_minutes=bucket_minutes,
            use_extracted_date=use_extracted_date,
            timelines=timelines,
        )

        processing_timeline_response.additional_properties = d
        return processing_timeline_response

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
