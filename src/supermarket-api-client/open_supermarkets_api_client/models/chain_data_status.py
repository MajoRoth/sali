from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChainDataStatus")


@_attrs_define
class ChainDataStatus:
    """
    Attributes:
        chain_extracted_code (str):
        chain_id (str):
        promo_listing_count (int):
        store_count (int):
        product_listing_count (int):
        is_stale (bool):
        chain_name (None | str | Unset):
        last_update (datetime.datetime | None | Unset):
        hours_since_update (float | None | Unset):
    """

    chain_extracted_code: str
    chain_id: str
    promo_listing_count: int
    store_count: int
    product_listing_count: int
    is_stale: bool
    chain_name: None | str | Unset = UNSET
    last_update: datetime.datetime | None | Unset = UNSET
    hours_since_update: float | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chain_extracted_code = self.chain_extracted_code

        chain_id = self.chain_id

        promo_listing_count = self.promo_listing_count

        store_count = self.store_count

        product_listing_count = self.product_listing_count

        is_stale = self.is_stale

        chain_name: None | str | Unset
        if isinstance(self.chain_name, Unset):
            chain_name = UNSET
        else:
            chain_name = self.chain_name

        last_update: None | str | Unset
        if isinstance(self.last_update, Unset):
            last_update = UNSET
        elif isinstance(self.last_update, datetime.datetime):
            last_update = self.last_update.isoformat()
        else:
            last_update = self.last_update

        hours_since_update: float | None | Unset
        if isinstance(self.hours_since_update, Unset):
            hours_since_update = UNSET
        else:
            hours_since_update = self.hours_since_update

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ChainExtractedCode": chain_extracted_code,
                "chainId": chain_id,
                "PromoListingCount": promo_listing_count,
                "storeCount": store_count,
                "productListingCount": product_listing_count,
                "isStale": is_stale,
            }
        )
        if chain_name is not UNSET:
            field_dict["chainName"] = chain_name
        if last_update is not UNSET:
            field_dict["lastUpdate"] = last_update
        if hours_since_update is not UNSET:
            field_dict["hoursSinceUpdate"] = hours_since_update

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        chain_extracted_code = d.pop("ChainExtractedCode")

        chain_id = d.pop("chainId")

        promo_listing_count = d.pop("PromoListingCount")

        store_count = d.pop("storeCount")

        product_listing_count = d.pop("productListingCount")

        is_stale = d.pop("isStale")

        def _parse_chain_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        chain_name = _parse_chain_name(d.pop("chainName", UNSET))

        def _parse_last_update(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_update_type_0 = datetime.datetime.fromisoformat(data)

                return last_update_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        last_update = _parse_last_update(d.pop("lastUpdate", UNSET))

        def _parse_hours_since_update(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        hours_since_update = _parse_hours_since_update(d.pop("hoursSinceUpdate", UNSET))

        chain_data_status = cls(
            chain_extracted_code=chain_extracted_code,
            chain_id=chain_id,
            promo_listing_count=promo_listing_count,
            store_count=store_count,
            product_listing_count=product_listing_count,
            is_stale=is_stale,
            chain_name=chain_name,
            last_update=last_update,
            hours_since_update=hours_since_update,
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
