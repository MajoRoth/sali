from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.time_bucket_data import TimeBucketData


T = TypeVar("T", bound="SiteProcessingTimeline")


@_attrs_define
class SiteProcessingTimeline:
    """
    Attributes:
        extracted_from_site (str):
        buckets (list[TimeBucketData]):
    """

    extracted_from_site: str
    buckets: list[TimeBucketData]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        extracted_from_site = self.extracted_from_site

        buckets = []
        for buckets_item_data in self.buckets:
            buckets_item = buckets_item_data.to_dict()
            buckets.append(buckets_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "extractedFromSite": extracted_from_site,
                "buckets": buckets,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.time_bucket_data import TimeBucketData

        d = dict(src_dict)
        extracted_from_site = d.pop("extractedFromSite")

        buckets = []
        _buckets = d.pop("buckets")
        for buckets_item_data in _buckets:
            buckets_item = TimeBucketData.from_dict(buckets_item_data)

            buckets.append(buckets_item)

        site_processing_timeline = cls(
            extracted_from_site=extracted_from_site,
            buckets=buckets,
        )

        site_processing_timeline.additional_properties = d
        return site_processing_timeline

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
