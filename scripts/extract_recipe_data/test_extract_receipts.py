from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.extract_recipe_data.extract_receipts import (
    ExtractionError,
    ReceiptSource,
    _deduplicate_sources,
    fetch_receipt,
    normalize_receipt,
    parse_receipt_source,
    write_csv,
)

RECEIPT_ID = "11111111-1111-4111-8111-111111111111"
BUSINESS_ID = "22222222-2222-4222-8222-222222222222"


class ExtractReceiptsTests(unittest.TestCase):
    def test_parse_receipt_source_from_url(self) -> None:
        source = parse_receipt_source(
            "https://receipts.weezmo.com/cms.html"
            f"?q={RECEIPT_ID}&b={BUSINESS_ID}&cookie=true"
        )

        self.assertEqual(source, ReceiptSource(RECEIPT_ID, BUSINESS_ID))

    def test_parse_receipt_source_from_bare_uuid(self) -> None:
        self.assertEqual(
            parse_receipt_source(RECEIPT_ID),
            ReceiptSource(RECEIPT_ID),
        )

    def test_parse_receipt_source_rejects_invalid_sources(self) -> None:
        invalid_sources = [
            "not-a-uuid",
            "00000000-0000-0000-0000-000000000000",
            f"https://example.com/cms.html?q={RECEIPT_ID}",
            "https://receipts.weezmo.com/cms.html?cookie=true",
        ]

        for source in invalid_sources:
            with self.subTest(source=source), self.assertRaises(ExtractionError):
                parse_receipt_source(source)

    @patch("scripts.extract_recipe_data.extract_receipts.urlopen")
    def test_fetch_receipt_rejects_weezmo_demo_fallback(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = io.BytesIO(
            json.dumps(
                [{"id": "00000000-0000-0000-0000-000000000000"}]
            ).encode()
        )

        with self.assertRaisesRegex(
            ExtractionError,
            "did not return the requested receipt",
        ):
            fetch_receipt(ReceiptSource(RECEIPT_ID))

    @patch("scripts.extract_recipe_data.extract_receipts.urlopen")
    def test_fetch_receipt_checks_business_id_from_url(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = io.BytesIO(
            json.dumps(
                [{"id": RECEIPT_ID, "businessID": "wrong-business-id"}]
            ).encode()
        )

        with self.assertRaisesRegex(ExtractionError, "business ID"):
            fetch_receipt(ReceiptSource(RECEIPT_ID, BUSINESS_ID))

    def test_deduplicate_sources_uses_receipt_id_and_keeps_business_check(
        self,
    ) -> None:
        sources = [
            ReceiptSource(RECEIPT_ID),
            ReceiptSource(RECEIPT_ID, BUSINESS_ID),
        ]

        self.assertEqual(
            _deduplicate_sources(sources),
            [ReceiptSource(RECEIPT_ID, BUSINESS_ID)],
        )

    def test_normalize_receipt_flattens_items_and_adjustments(self) -> None:
        receipt = {
            "id": RECEIPT_ID,
            "businessID": BUSINESS_ID,
            "branchID": "branch-id",
            "createdDate": "2026-06-26T13:05:37Z",
            "currency": None,
            "total": 56.99,
            "transactionNumber": "973",
            "receiptType": "Purchase",
            "tBusiness": {
                "businessName": "יוחננוף",
                "currencyCode": "ILS",
            },
            "tBranch": {
                "branchName": "yohananof",
                "internalID": "024",
            },
            "items": [
                {
                    "id": "item-id",
                    "name": "פילה עוף טרי פרימיו",
                    "itemCode": "400082",
                    "price": 59.9,
                    "quantity": 1.038,
                    "total": 62.18,
                    "discount": None,
                    "discountCalc": 0,
                    "additionalData": [
                        {"key": "פילה עוף טרי 54.90", "value": "-5.19"}
                    ],
                    "categories": [],
                    "subItems": [],
                }
            ],
        }

        result = normalize_receipt(receipt)

        self.assertEqual(result.currency, "ILS")
        self.assertEqual(result.calculated_total, result.receipt_total)
        self.assertEqual(result.rows[0]["item_code"], "400082")
        self.assertEqual(result.rows[0]["quantity"], "1.038")
        self.assertEqual(
            result.rows[0]["candidate_adjustment_total"],
            "-5.19",
        )
        self.assertEqual(result.rows[0]["adjustment_total"], "-5.19")
        self.assertEqual(result.rows[0]["adjustment_status"], "applied_reconciled")
        self.assertEqual(result.rows[0]["net_line_total"], "56.99")
        self.assertIn(
            "פילה עוף טרי 54.90",
            result.rows[0]["adjustments_json"],
        )

    def test_unknown_numeric_metadata_is_not_applied_as_money(self) -> None:
        result = normalize_receipt(
            {
                "id": RECEIPT_ID,
                "total": 10,
                "items": [
                    {
                        "name": "Item",
                        "price": 10,
                        "quantity": 1,
                        "total": 10,
                        "additionalData": [
                            {"key": "loyalty points", "value": "25"}
                        ],
                    }
                ],
            }
        )

        self.assertEqual(result.rows[0]["candidate_adjustment_total"], "0")
        self.assertEqual(result.rows[0]["adjustment_total"], "0")
        self.assertEqual(result.rows[0]["net_line_total"], "10")

    def test_unreconciled_negative_metadata_is_not_applied(self) -> None:
        result = normalize_receipt(
            {
                "id": RECEIPT_ID,
                "total": 10,
                "items": [
                    {
                        "name": "Item",
                        "price": 10,
                        "quantity": 1,
                        "total": 10,
                        "additionalData": [
                            {"key": "unknown negative value", "value": "-2"}
                        ],
                    }
                ],
            }
        )

        self.assertEqual(result.rows[0]["candidate_adjustment_total"], "-2")
        self.assertEqual(result.rows[0]["adjustment_total"], "0")
        self.assertEqual(
            result.rows[0]["adjustment_status"],
            "not_applied_unreconciled",
        )
        self.assertEqual(result.rows[0]["net_line_total"], "10")

    def test_formula_like_remote_text_is_escaped_for_spreadsheets(self) -> None:
        result = normalize_receipt(
            {
                "id": RECEIPT_ID,
                "total": 1,
                "items": [
                    {
                        "name": "=1+1",
                        "price": 1,
                        "quantity": 1,
                        "total": 1,
                    }
                ],
            }
        )

        self.assertEqual(result.rows[0]["product_name"], "'=1+1")

    def test_write_csv_uses_utf8_bom_and_preserves_hebrew(self) -> None:
        result = normalize_receipt(
            {
                "id": RECEIPT_ID,
                "total": 5.5,
                "tBusiness": {
                    "businessName": "בדיקה",
                    "currencyCode": "ILS",
                },
                "items": [
                    {
                        "id": "item-id",
                        "name": "חלב",
                        "itemCode": "000123",
                        "price": 5.5,
                        "quantity": 1,
                        "total": 5.5,
                    }
                ],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "receipt.csv"

            self.assertEqual(write_csv([result], output), 1)
            self.assertTrue(output.read_bytes().startswith(b"\xef\xbb\xbf"))

            with output.open(encoding="utf-8-sig", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(rows[0]["product_name"], "חלב")
        self.assertEqual(rows[0]["item_code"], "000123")


if __name__ == "__main__":
    unittest.main()
