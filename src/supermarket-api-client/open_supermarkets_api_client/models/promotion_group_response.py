from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.promotion_item_response import PromotionItemResponse


T = TypeVar("T", bound="PromotionGroupResponse")


@_attrs_define
class PromotionGroupResponse:
    """
    Attributes:
        group_id (str):
        group_name (str):
        min_purchase_amount (float):
        discount_type (int):
        promotion_items (list[PromotionItemResponse]):
    """

    group_id: str
    group_name: str
    min_purchase_amount: float
    discount_type: int
    promotion_items: list[PromotionItemResponse]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        group_id = self.group_id

        group_name = self.group_name

        min_purchase_amount = self.min_purchase_amount

        discount_type = self.discount_type

        promotion_items = []
        for promotion_items_item_data in self.promotion_items:
            promotion_items_item = promotion_items_item_data.to_dict()
            promotion_items.append(promotion_items_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "group_id": group_id,
                "group_name": group_name,
                "min_purchase_amount": min_purchase_amount,
                "discount_type": discount_type,
                "promotion_items": promotion_items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.promotion_item_response import PromotionItemResponse

        d = dict(src_dict)
        group_id = d.pop("group_id")

        group_name = d.pop("group_name")

        min_purchase_amount = d.pop("min_purchase_amount")

        discount_type = d.pop("discount_type")

        promotion_items = []
        _promotion_items = d.pop("promotion_items")
        for promotion_items_item_data in _promotion_items:
            promotion_items_item = PromotionItemResponse.from_dict(promotion_items_item_data)

            promotion_items.append(promotion_items_item)

        promotion_group_response = cls(
            group_id=group_id,
            group_name=group_name,
            min_purchase_amount=min_purchase_amount,
            discount_type=discount_type,
            promotion_items=promotion_items,
        )

        promotion_group_response.additional_properties = d
        return promotion_group_response

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
