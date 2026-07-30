from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RowBucketMetric")


@_attrs_define
class RowBucketMetric:
    """
    Attributes:
        total_loaded (int):
        total_published (int):
    """

    total_loaded: int
    total_published: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        total_loaded = self.total_loaded

        total_published = self.total_published

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "totalLoaded": total_loaded,
                "totalPublished": total_published,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        total_loaded = d.pop("totalLoaded")

        total_published = d.pop("totalPublished")

        row_bucket_metric = cls(
            total_loaded=total_loaded,
            total_published=total_published,
        )

        row_bucket_metric.additional_properties = d
        return row_bucket_metric

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
