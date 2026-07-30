from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.cross_chain_price_comparison_response import CrossChainPriceComparisonResponse


T = TypeVar("T", bound="ComparePricesResponse")


@_attrs_define
class ComparePricesResponse:
    """Response for GET /products/compare-prices

    Attributes:
        comparisons (list[CrossChainPriceComparisonResponse]):
        not_found_product_ids (list[str] | Unset):
        product_ids_with_no_listings (list[str] | Unset):
    """

    comparisons: list[CrossChainPriceComparisonResponse]
    not_found_product_ids: list[str] | Unset = UNSET
    product_ids_with_no_listings: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        comparisons = []
        for comparisons_item_data in self.comparisons:
            comparisons_item = comparisons_item_data.to_dict()
            comparisons.append(comparisons_item)

        not_found_product_ids: list[str] | Unset = UNSET
        if not isinstance(self.not_found_product_ids, Unset):
            not_found_product_ids = self.not_found_product_ids

        product_ids_with_no_listings: list[str] | Unset = UNSET
        if not isinstance(self.product_ids_with_no_listings, Unset):
            product_ids_with_no_listings = self.product_ids_with_no_listings

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "comparisons": comparisons,
            }
        )
        if not_found_product_ids is not UNSET:
            field_dict["notFoundProductIds"] = not_found_product_ids
        if product_ids_with_no_listings is not UNSET:
            field_dict["productIdsWithNoListings"] = product_ids_with_no_listings

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.cross_chain_price_comparison_response import CrossChainPriceComparisonResponse

        d = dict(src_dict)
        comparisons = []
        _comparisons = d.pop("comparisons")
        for comparisons_item_data in _comparisons:
            comparisons_item = CrossChainPriceComparisonResponse.from_dict(comparisons_item_data)

            comparisons.append(comparisons_item)

        not_found_product_ids = cast(list[str], d.pop("notFoundProductIds", UNSET))

        product_ids_with_no_listings = cast(list[str], d.pop("productIdsWithNoListings", UNSET))

        compare_prices_response = cls(
            comparisons=comparisons,
            not_found_product_ids=not_found_product_ids,
            product_ids_with_no_listings=product_ids_with_no_listings,
        )

        compare_prices_response.additional_properties = d
        return compare_prices_response

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
