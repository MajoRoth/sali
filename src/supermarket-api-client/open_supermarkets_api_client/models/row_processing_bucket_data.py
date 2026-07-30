from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RowProcessingBucketData")


@_attrs_define
class RowProcessingBucketData:
    """
    Attributes:
        bucket_start (datetime.datetime):
        bucket_end (datetime.datetime):
        total_loaded_from_file (int):
        total_published_records (int):
    """

    bucket_start: datetime.datetime
    bucket_end: datetime.datetime
    total_loaded_from_file: int
    total_published_records: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bucket_start = self.bucket_start.isoformat()

        bucket_end = self.bucket_end.isoformat()

        total_loaded_from_file = self.total_loaded_from_file

        total_published_records = self.total_published_records

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bucketStart": bucket_start,
                "bucketEnd": bucket_end,
                "totalLoadedFromFile": total_loaded_from_file,
                "totalPublishedRecords": total_published_records,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        bucket_start = datetime.datetime.fromisoformat(d.pop("bucketStart"))

        bucket_end = datetime.datetime.fromisoformat(d.pop("bucketEnd"))

        total_loaded_from_file = d.pop("totalLoadedFromFile")

        total_published_records = d.pop("totalPublishedRecords")

        row_processing_bucket_data = cls(
            bucket_start=bucket_start,
            bucket_end=bucket_end,
            total_loaded_from_file=total_loaded_from_file,
            total_published_records=total_published_records,
        )

        row_processing_bucket_data.additional_properties = d
        return row_processing_bucket_data

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
