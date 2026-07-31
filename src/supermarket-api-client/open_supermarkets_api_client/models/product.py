from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Product")


@_attrs_define
class Product:
    """
    Attributes:
        id (str):
        product_barcode (int):
        internal_barcode (int):
        product_name (str):
        manufacturer_or_importer_name (str):
        country_of_origin (str):
        product_description (str):
        product_quantity_measure (str):
        product_quantity (int):
        unit_of_measure (str):
        items_per_package (int):
        is_weighted (int):
        item_type (int):
        last_updated (datetime.datetime | None | Unset):
    """

    id: str
    product_barcode: int
    internal_barcode: int
    product_name: str
    manufacturer_or_importer_name: str
    country_of_origin: str
    product_description: str
    product_quantity_measure: str
    product_quantity: int
    unit_of_measure: str
    items_per_package: int
    is_weighted: int
    item_type: int
    last_updated: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        product_barcode = self.product_barcode

        internal_barcode = self.internal_barcode

        product_name = self.product_name

        manufacturer_or_importer_name = self.manufacturer_or_importer_name

        country_of_origin = self.country_of_origin

        product_description = self.product_description

        product_quantity_measure = self.product_quantity_measure

        product_quantity = self.product_quantity

        unit_of_measure = self.unit_of_measure

        items_per_package = self.items_per_package

        is_weighted = self.is_weighted

        item_type = self.item_type

        last_updated: None | str | Unset
        if isinstance(self.last_updated, Unset):
            last_updated = UNSET
        elif isinstance(self.last_updated, datetime.datetime):
            last_updated = self.last_updated.isoformat()
        else:
            last_updated = self.last_updated

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "productBarcode": product_barcode,
                "internalBarcode": internal_barcode,
                "productName": product_name,
                "manufacturerOrImporterName": manufacturer_or_importer_name,
                "countryOfOrigin": country_of_origin,
                "productDescription": product_description,
                "productQuantityMeasure": product_quantity_measure,
                "productQuantity": product_quantity,
                "unitOfMeasure": unit_of_measure,
                "itemsPerPackage": items_per_package,
                "isWeighted": is_weighted,
                "itemType": item_type,
            }
        )
        if last_updated is not UNSET:
            field_dict["lastUpdated"] = last_updated

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        product_barcode = d.pop("productBarcode")

        internal_barcode = d.pop("internalBarcode")

        product_name = d.pop("productName")

        manufacturer_or_importer_name = d.pop("manufacturerOrImporterName")

        country_of_origin = d.pop("countryOfOrigin")

        product_description = d.pop("productDescription")

        product_quantity_measure = d.pop("productQuantityMeasure")

        product_quantity = d.pop("productQuantity")

        unit_of_measure = d.pop("unitOfMeasure")

        items_per_package = d.pop("itemsPerPackage")

        is_weighted = d.pop("isWeighted")

        item_type = d.pop("itemType")

        def _parse_last_updated(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_updated_type_0 = datetime.datetime.fromisoformat(data)

                return last_updated_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        last_updated = _parse_last_updated(d.pop("lastUpdated", UNSET))

        product = cls(
            id=id,
            product_barcode=product_barcode,
            internal_barcode=internal_barcode,
            product_name=product_name,
            manufacturer_or_importer_name=manufacturer_or_importer_name,
            country_of_origin=country_of_origin,
            product_description=product_description,
            product_quantity_measure=product_quantity_measure,
            product_quantity=product_quantity,
            unit_of_measure=unit_of_measure,
            items_per_package=items_per_package,
            is_weighted=is_weighted,
            item_type=item_type,
            last_updated=last_updated,
        )

        product.additional_properties = d
        return product

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
