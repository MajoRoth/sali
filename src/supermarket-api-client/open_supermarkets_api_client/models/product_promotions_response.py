from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.promotion_response import PromotionResponse


T = TypeVar("T", bound="ProductPromotionsResponse")


@_attrs_define
class ProductPromotionsResponse:
    """
    Attributes:
        product_barcode (int):
        product_name (str):
        promotions (list[PromotionResponse]):
        total_promotions (int):
    """

    product_barcode: int
    product_name: str
    promotions: list[PromotionResponse]
    total_promotions: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        product_barcode = self.product_barcode

        product_name = self.product_name

        promotions = []
        for promotions_item_data in self.promotions:
            promotions_item = promotions_item_data.to_dict()
            promotions.append(promotions_item)

        total_promotions = self.total_promotions

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "product_barcode": product_barcode,
                "product_name": product_name,
                "promotions": promotions,
                "total_promotions": total_promotions,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.promotion_response import PromotionResponse

        d = dict(src_dict)
        product_barcode = d.pop("product_barcode")

        product_name = d.pop("product_name")

        promotions = []
        _promotions = d.pop("promotions")
        for promotions_item_data in _promotions:
            promotions_item = PromotionResponse.from_dict(promotions_item_data)

            promotions.append(promotions_item)

        total_promotions = d.pop("total_promotions")

        product_promotions_response = cls(
            product_barcode=product_barcode,
            product_name=product_name,
            promotions=promotions,
            total_promotions=total_promotions,
        )

        product_promotions_response.additional_properties = d
        return product_promotions_response

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
