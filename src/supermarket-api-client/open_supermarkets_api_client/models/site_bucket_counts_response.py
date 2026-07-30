from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.row_bucket_metric import RowBucketMetric


T = TypeVar("T", bound="SiteBucketCountsResponse")


@_attrs_define
class SiteBucketCountsResponse:
    """Per-bucket file counts and row metrics for a single extracted_from_site value.

    Attributes:
        site (str):
        start_time (datetime.datetime):
        end_time (datetime.datetime):
        bucket_minutes (int):
        use_extracted_date (bool):
        file_counts (list[int]):
        row_metrics (list[RowBucketMetric]):
    """

    site: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    bucket_minutes: int
    use_extracted_date: bool
    file_counts: list[int]
    row_metrics: list[RowBucketMetric]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        site = self.site

        start_time = self.start_time.isoformat()

        end_time = self.end_time.isoformat()

        bucket_minutes = self.bucket_minutes

        use_extracted_date = self.use_extracted_date

        file_counts = self.file_counts

        row_metrics = []
        for row_metrics_item_data in self.row_metrics:
            row_metrics_item = row_metrics_item_data.to_dict()
            row_metrics.append(row_metrics_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "site": site,
                "startTime": start_time,
                "endTime": end_time,
                "bucketMinutes": bucket_minutes,
                "useExtractedDate": use_extracted_date,
                "fileCounts": file_counts,
                "rowMetrics": row_metrics,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.row_bucket_metric import RowBucketMetric

        d = dict(src_dict)
        site = d.pop("site")

        start_time = datetime.datetime.fromisoformat(d.pop("startTime"))

        end_time = datetime.datetime.fromisoformat(d.pop("endTime"))

        bucket_minutes = d.pop("bucketMinutes")

        use_extracted_date = d.pop("useExtractedDate")

        file_counts = cast(list[int], d.pop("fileCounts"))

        row_metrics = []
        _row_metrics = d.pop("rowMetrics")
        for row_metrics_item_data in _row_metrics:
            row_metrics_item = RowBucketMetric.from_dict(row_metrics_item_data)

            row_metrics.append(row_metrics_item)

        site_bucket_counts_response = cls(
            site=site,
            start_time=start_time,
            end_time=end_time,
            bucket_minutes=bucket_minutes,
            use_extracted_date=use_extracted_date,
            file_counts=file_counts,
            row_metrics=row_metrics,
        )

        site_bucket_counts_response.additional_properties = d
        return site_bucket_counts_response

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
