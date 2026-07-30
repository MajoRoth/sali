from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PromotionItemResponse")


@_attrs_define
class PromotionItemResponse:
    """
    Attributes:
        item_code (str):
        product_barcode (int):
        reward_type (int):
        min_quantity (int):
        max_quantity (int):
        discount_rate (float):
        discounted_price (float):
        original_price (float):
        item_name (str):
        item_description (str):
        item_type (int):
    """

    item_code: str
    product_barcode: int
    reward_type: int
    min_quantity: int
    max_quantity: int
    discount_rate: float
    discounted_price: float
    original_price: float
    item_name: str
    item_description: str
    item_type: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        item_code = self.item_code

        product_barcode = self.product_barcode

        reward_type = self.reward_type

        min_quantity = self.min_quantity

        max_quantity = self.max_quantity

        discount_rate = self.discount_rate

        discounted_price = self.discounted_price

        original_price = self.original_price

        item_name = self.item_name

        item_description = self.item_description

        item_type = self.item_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "item_code": item_code,
                "product_barcode": product_barcode,
                "reward_type": reward_type,
                "min_quantity": min_quantity,
                "max_quantity": max_quantity,
                "discount_rate": discount_rate,
                "discounted_price": discounted_price,
                "original_price": original_price,
                "item_name": item_name,
                "item_description": item_description,
                "item_type": item_type,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        item_code = d.pop("item_code")

        product_barcode = d.pop("product_barcode")

        reward_type = d.pop("reward_type")

        min_quantity = d.pop("min_quantity")

        max_quantity = d.pop("max_quantity")

        discount_rate = d.pop("discount_rate")

        discounted_price = d.pop("discounted_price")

        original_price = d.pop("original_price")

        item_name = d.pop("item_name")

        item_description = d.pop("item_description")

        item_type = d.pop("item_type")

        promotion_item_response = cls(
            item_code=item_code,
            product_barcode=product_barcode,
            reward_type=reward_type,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            discount_rate=discount_rate,
            discounted_price=discounted_price,
            original_price=original_price,
            item_name=item_name,
            item_description=item_description,
            item_type=item_type,
        )

        promotion_item_response.additional_properties = d
        return promotion_item_response

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
