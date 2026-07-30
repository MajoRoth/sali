from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.promotion_group_response import PromotionGroupResponse


T = TypeVar("T", bound="PromotionResponse")


@_attrs_define
class PromotionResponse:
    """
    Attributes:
        promotion_id (int):
        promotion_description (str):
        promotion_start_datetime (datetime.datetime):
        promotion_end_datetime (datetime.datetime):
        promotion_update_datetime (datetime.datetime):
        target_population (str):
        minimum_quantity_for_promo (int):
        maximum_quantity_for_promo (int):
        discount_rate (float):
        minimum_purchase_amount (float):
        maximum_purchase_amount (float):
        additional_promo_restrictions (str):
        additional_promo_text (str):
        reward_type (int):
        discount_type (int):
        promotion_items (str):
        clubs (str):
        weight_unit (str):
        is_weighted_promo (int):
        item_type (int):
        gifts_items (str):
        promotion_groups (list[PromotionGroupResponse]):
    """

    promotion_id: int
    promotion_description: str
    promotion_start_datetime: datetime.datetime
    promotion_end_datetime: datetime.datetime
    promotion_update_datetime: datetime.datetime
    target_population: str
    minimum_quantity_for_promo: int
    maximum_quantity_for_promo: int
    discount_rate: float
    minimum_purchase_amount: float
    maximum_purchase_amount: float
    additional_promo_restrictions: str
    additional_promo_text: str
    reward_type: int
    discount_type: int
    promotion_items: str
    clubs: str
    weight_unit: str
    is_weighted_promo: int
    item_type: int
    gifts_items: str
    promotion_groups: list[PromotionGroupResponse]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        promotion_id = self.promotion_id

        promotion_description = self.promotion_description

        promotion_start_datetime = self.promotion_start_datetime.isoformat()

        promotion_end_datetime = self.promotion_end_datetime.isoformat()

        promotion_update_datetime = self.promotion_update_datetime.isoformat()

        target_population = self.target_population

        minimum_quantity_for_promo = self.minimum_quantity_for_promo

        maximum_quantity_for_promo = self.maximum_quantity_for_promo

        discount_rate = self.discount_rate

        minimum_purchase_amount = self.minimum_purchase_amount

        maximum_purchase_amount = self.maximum_purchase_amount

        additional_promo_restrictions = self.additional_promo_restrictions

        additional_promo_text = self.additional_promo_text

        reward_type = self.reward_type

        discount_type = self.discount_type

        promotion_items = self.promotion_items

        clubs = self.clubs

        weight_unit = self.weight_unit

        is_weighted_promo = self.is_weighted_promo

        item_type = self.item_type

        gifts_items = self.gifts_items

        promotion_groups = []
        for promotion_groups_item_data in self.promotion_groups:
            promotion_groups_item = promotion_groups_item_data.to_dict()
            promotion_groups.append(promotion_groups_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "promotion_id": promotion_id,
                "promotion_description": promotion_description,
                "promotion_start_datetime": promotion_start_datetime,
                "promotion_end_datetime": promotion_end_datetime,
                "promotion_update_datetime": promotion_update_datetime,
                "target_population": target_population,
                "minimum_quantity_for_promo": minimum_quantity_for_promo,
                "maximum_quantity_for_promo": maximum_quantity_for_promo,
                "discount_rate": discount_rate,
                "minimum_purchase_amount": minimum_purchase_amount,
                "maximum_purchase_amount": maximum_purchase_amount,
                "additional_promo_restrictions": additional_promo_restrictions,
                "additional_promo_text": additional_promo_text,
                "reward_type": reward_type,
                "discount_type": discount_type,
                "promotion_items": promotion_items,
                "clubs": clubs,
                "weight_unit": weight_unit,
                "is_weighted_promo": is_weighted_promo,
                "item_type": item_type,
                "gifts_items": gifts_items,
                "promotion_groups": promotion_groups,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.promotion_group_response import PromotionGroupResponse

        d = dict(src_dict)
        promotion_id = d.pop("promotion_id")

        promotion_description = d.pop("promotion_description")

        promotion_start_datetime = datetime.datetime.fromisoformat(d.pop("promotion_start_datetime"))

        promotion_end_datetime = datetime.datetime.fromisoformat(d.pop("promotion_end_datetime"))

        promotion_update_datetime = datetime.datetime.fromisoformat(d.pop("promotion_update_datetime"))

        target_population = d.pop("target_population")

        minimum_quantity_for_promo = d.pop("minimum_quantity_for_promo")

        maximum_quantity_for_promo = d.pop("maximum_quantity_for_promo")

        discount_rate = d.pop("discount_rate")

        minimum_purchase_amount = d.pop("minimum_purchase_amount")

        maximum_purchase_amount = d.pop("maximum_purchase_amount")

        additional_promo_restrictions = d.pop("additional_promo_restrictions")

        additional_promo_text = d.pop("additional_promo_text")

        reward_type = d.pop("reward_type")

        discount_type = d.pop("discount_type")

        promotion_items = d.pop("promotion_items")

        clubs = d.pop("clubs")

        weight_unit = d.pop("weight_unit")

        is_weighted_promo = d.pop("is_weighted_promo")

        item_type = d.pop("item_type")

        gifts_items = d.pop("gifts_items")

        promotion_groups = []
        _promotion_groups = d.pop("promotion_groups")
        for promotion_groups_item_data in _promotion_groups:
            promotion_groups_item = PromotionGroupResponse.from_dict(promotion_groups_item_data)

            promotion_groups.append(promotion_groups_item)

        promotion_response = cls(
            promotion_id=promotion_id,
            promotion_description=promotion_description,
            promotion_start_datetime=promotion_start_datetime,
            promotion_end_datetime=promotion_end_datetime,
            promotion_update_datetime=promotion_update_datetime,
            target_population=target_population,
            minimum_quantity_for_promo=minimum_quantity_for_promo,
            maximum_quantity_for_promo=maximum_quantity_for_promo,
            discount_rate=discount_rate,
            minimum_purchase_amount=minimum_purchase_amount,
            maximum_purchase_amount=maximum_purchase_amount,
            additional_promo_restrictions=additional_promo_restrictions,
            additional_promo_text=additional_promo_text,
            reward_type=reward_type,
            discount_type=discount_type,
            promotion_items=promotion_items,
            clubs=clubs,
            weight_unit=weight_unit,
            is_weighted_promo=is_weighted_promo,
            item_type=item_type,
            gifts_items=gifts_items,
            promotion_groups=promotion_groups,
        )

        promotion_response.additional_properties = d
        return promotion_response

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
