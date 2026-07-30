from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ChainDataStatus")


@_attrs_define
class ChainDataStatus:
    """
    Attributes:
        chain_extracted_code (str):
        chain_id (str):
        chain_name (None | str):
        last_update (datetime.datetime | None):
        hours_since_update (float | None):
        promo_listing_count (int):
        store_count (int):
        product_listing_count (int):
        is_stale (bool):
    """

    chain_extracted_code: str
    chain_id: str
    chain_name: None | str
    last_update: datetime.datetime | None
    hours_since_update: float | None
    promo_listing_count: int
    store_count: int
    product_listing_count: int
    is_stale: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chain_extracted_code = self.chain_extracted_code

        chain_id = self.chain_id

        chain_name: None | str
        chain_name = self.chain_name

        last_update: None | str
        if isinstance(self.last_update, datetime.datetime):
            last_update = self.last_update.isoformat()
        else:
            last_update = self.last_update

        hours_since_update: float | None
        hours_since_update = self.hours_since_update

        promo_listing_count = self.promo_listing_count

        store_count = self.store_count

        product_listing_count = self.product_listing_count

        is_stale = self.is_stale

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ChainExtractedCode": chain_extracted_code,
                "chainId": chain_id,
                "chainName": chain_name,
                "lastUpdate": last_update,
                "hoursSinceUpdate": hours_since_update,
                "PromoListingCount": promo_listing_count,
                "storeCount": store_count,
                "productListingCount": product_listing_count,
                "isStale": is_stale,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        chain_extracted_code = d.pop("ChainExtractedCode")

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

        def _parse_hours_since_update(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        hours_since_update = _parse_hours_since_update(d.pop("hoursSinceUpdate"))

        promo_listing_count = d.pop("PromoListingCount")

        store_count = d.pop("storeCount")

        product_listing_count = d.pop("productListingCount")

        is_stale = d.pop("isStale")

        chain_data_status = cls(
            chain_extracted_code=chain_extracted_code,
            chain_id=chain_id,
            chain_name=chain_name,
            last_update=last_update,
            hours_since_update=hours_since_update,
            promo_listing_count=promo_listing_count,
            store_count=store_count,
            product_listing_count=product_listing_count,
            is_stale=is_stale,
        )

        chain_data_status.additional_properties = d
        return chain_data_status

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
