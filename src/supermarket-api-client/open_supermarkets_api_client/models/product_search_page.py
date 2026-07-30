from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.product import Product


T = TypeVar("T", bound="ProductSearchPage")


@_attrs_define
class ProductSearchPage:
    """Response for GET /products/search (cursor-style, no total count)

    Attributes:
        items (list[Product]):
        limit (int):
        offset (int):
        has_more (bool):
        next_offset (int | None):
    """

    items: list[Product]
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        limit = self.limit

        offset = self.offset

        has_more = self.has_more

        next_offset: int | None
        next_offset = self.next_offset

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "items": items,
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.product import Product

        d = dict(src_dict)
        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = Product.from_dict(items_item_data)

            items.append(items_item)

        limit = d.pop("limit")

        offset = d.pop("offset")

        has_more = d.pop("has_more")

        def _parse_next_offset(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        next_offset = _parse_next_offset(d.pop("next_offset"))

        product_search_page = cls(
            items=items,
            limit=limit,
            offset=offset,
            has_more=has_more,
            next_offset=next_offset,
        )

        product_search_page.additional_properties = d
        return product_search_page

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
