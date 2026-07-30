from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.chain_price_data import ChainPriceData
    from ..models.overall_statistics import OverallStatistics


T = TypeVar("T", bound="CrossChainPriceComparisonResponse")


@_attrs_define
class CrossChainPriceComparisonResponse:
    """Response for GET /analytics/price-comparison/cross-chain

    Attributes:
        product_barcode (int):
        product_name (str):
        manufacturer (None | str):
        current_only (bool):
        overall_statistics (OverallStatistics): Overall price statistics
        chain_comparison (list[ChainPriceData]):
    """

    product_barcode: int
    product_name: str
    manufacturer: None | str
    current_only: bool
    overall_statistics: OverallStatistics
    chain_comparison: list[ChainPriceData]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        product_barcode = self.product_barcode

        product_name = self.product_name

        manufacturer: None | str
        manufacturer = self.manufacturer

        current_only = self.current_only

        overall_statistics = self.overall_statistics.to_dict()

        chain_comparison = []
        for chain_comparison_item_data in self.chain_comparison:
            chain_comparison_item = chain_comparison_item_data.to_dict()
            chain_comparison.append(chain_comparison_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "productBarcode": product_barcode,
                "productName": product_name,
                "manufacturer": manufacturer,
                "currentOnly": current_only,
                "overallStatistics": overall_statistics,
                "chainComparison": chain_comparison,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chain_price_data import ChainPriceData
        from ..models.overall_statistics import OverallStatistics

        d = dict(src_dict)
        product_barcode = d.pop("productBarcode")

        product_name = d.pop("productName")

        def _parse_manufacturer(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        manufacturer = _parse_manufacturer(d.pop("manufacturer"))

        current_only = d.pop("currentOnly")

        overall_statistics = OverallStatistics.from_dict(d.pop("overallStatistics"))

        chain_comparison = []
        _chain_comparison = d.pop("chainComparison")
        for chain_comparison_item_data in _chain_comparison:
            chain_comparison_item = ChainPriceData.from_dict(chain_comparison_item_data)

            chain_comparison.append(chain_comparison_item)

        cross_chain_price_comparison_response = cls(
            product_barcode=product_barcode,
            product_name=product_name,
            manufacturer=manufacturer,
            current_only=current_only,
            overall_statistics=overall_statistics,
            chain_comparison=chain_comparison,
        )

        cross_chain_price_comparison_response.additional_properties = d
        return cross_chain_price_comparison_response

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
