from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from uuid import UUID

API_URL = "https://receipts.weezmo.com/api/receipts/{receipt_id}?withTemplate=false"
ALLOWED_PAGE_HOST = "receipts.weezmo.com"
DEFAULT_OUTPUT = Path(__file__).with_name("weezmo_receipts.csv")

CSV_FIELDS = [
    "receipt_id",
    "business_id",
    "business_name",
    "branch_id",
    "branch_name",
    "branch_number",
    "purchased_at",
    "transaction_number",
    "currency",
    "receipt_total",
    "receipt_type",
    "item_position",
    "item_path",
    "item_id",
    "parent_item_id",
    "item_code",
    "product_name",
    "unit_price",
    "quantity",
    "gross_line_total",
    "api_discount",
    "api_discount_calc",
    "candidate_adjustment_total",
    "adjustment_total",
    "adjustment_status",
    "net_line_total",
    "adjustments_json",
    "categories_json",
]

JsonObject = dict[str, Any]
UNSAFE_CSV_TEXT_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class ExtractionError(RuntimeError):
    """Raised when a receipt cannot be fetched or safely normalized."""


@dataclass(frozen=True)
class ReceiptSource:
    receipt_id: str
    expected_business_id: str | None = None


@dataclass(frozen=True)
class ExtractedReceipt:
    receipt_id: str
    currency: str
    receipt_total: Decimal | None
    rows: list[dict[str, str]]

    @property
    def calculated_total(self) -> Decimal:
        return sum(
            (
                value
                for row in self.rows
                if (value := _to_decimal(row["net_line_total"])) is not None
            ),
            start=Decimal("0"),
        )


def _normalized_uuid(value: str, label: str) -> str:
    try:
        parsed = UUID(value.strip())
    except (ValueError, AttributeError) as exc:
        raise ExtractionError(f"{label} is not a valid UUID: {value!r}") from exc
    if parsed.int == 0:
        raise ExtractionError(f"{label} cannot be the all-zero demo UUID")
    return str(parsed)


def parse_receipt_source(source: str) -> ReceiptSource:
    """Parse either a Weezmo receipt URL or a bare receipt UUID."""
    source = source.strip()
    if not source:
        raise ExtractionError("receipt source cannot be empty")

    if "://" not in source:
        return ReceiptSource(receipt_id=_normalized_uuid(source, "receipt ID"))

    parsed = urlparse(source)
    if parsed.scheme not in {"http", "https"} or parsed.hostname != ALLOWED_PAGE_HOST:
        raise ExtractionError(
            f"expected a {ALLOWED_PAGE_HOST} URL, received {source!r}"
        )

    query = parse_qs(parsed.query)
    receipt_values = query.get("q", [])
    if len(receipt_values) != 1:
        raise ExtractionError("Weezmo URL must contain exactly one non-empty q value")

    business_values = query.get("b", [])
    if len(business_values) > 1:
        raise ExtractionError("Weezmo URL must contain at most one b value")

    business_id = (
        _normalized_uuid(business_values[0], "business ID")
        if business_values
        else None
    )
    return ReceiptSource(
        receipt_id=_normalized_uuid(receipt_values[0], "receipt ID"),
        expected_business_id=business_id,
    )


def fetch_receipt(source: ReceiptSource, timeout: float = 20.0) -> JsonObject:
    """Fetch one receipt from the JSON endpoint used by Weezmo's frontend."""
    request = Request(
        API_URL.format(receipt_id=source.receipt_id),
        headers={
            "Accept": "application/json",
            "User-Agent": "sali-weezmo-receipt-poc/0.1",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 429:
            message = "Weezmo's daily request limit was reached; try again later"
        else:
            message = f"Weezmo returned HTTP {exc.code}"
        raise ExtractionError(f"{message} for receipt {source.receipt_id}") from exc
    except (URLError, TimeoutError) as exc:
        raise ExtractionError(
            f"could not reach Weezmo for receipt {source.receipt_id}: {exc}"
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ExtractionError(
            f"Weezmo returned invalid JSON for receipt {source.receipt_id}"
        ) from exc

    if not isinstance(payload, list) or len(payload) != 1:
        raise ExtractionError(
            f"unexpected Weezmo response for receipt {source.receipt_id}"
        )

    receipt = payload[0]
    if not isinstance(receipt, dict):
        raise ExtractionError(
            f"unexpected receipt value for receipt {source.receipt_id}"
        )

    returned_id = receipt.get("id")
    if returned_id != source.receipt_id:
        raise ExtractionError(
            "Weezmo did not return the requested receipt "
            f"(requested {source.receipt_id}, received {returned_id!r})"
        )

    returned_business_id = receipt.get("businessID")
    if (
        source.expected_business_id is not None
        and returned_business_id != source.expected_business_id
    ):
        raise ExtractionError(
            "receipt business ID does not match the b value in the source URL"
        )

    return receipt


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None

    text = str(value).strip().replace("₪", "").replace(",", "")
    if not text:
        return None

    try:
        decimal = Decimal(text)
    except InvalidOperation:
        return None
    return decimal if decimal.is_finite() else None


def _decimal_text(value: Any) -> str:
    decimal = _to_decimal(value)
    return format(decimal, "f") if decimal is not None else ""


def _text(value: Any) -> str:
    text = "" if value is None else str(value)
    if text.startswith(UNSAFE_CSV_TEXT_PREFIXES):
        return f"'{text}"
    return text


def _json_text(value: Any) -> str:
    if value in (None, [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _iter_items(
    items: Any,
    *,
    parent_item_id: str = "",
    path_prefix: tuple[int, ...] = (),
) -> Iterator[tuple[JsonObject, str, str]]:
    if not isinstance(items, list):
        return

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        path = (*path_prefix, index)
        item_path = ".".join(str(part) for part in path)
        yield item, parent_item_id, item_path

        item_id = _text(item.get("id"))
        yield from _iter_items(
            item.get("subItems"),
            parent_item_id=item_id,
            path_prefix=path,
        )


def _negative_adjustment_candidate(additional_data: Any) -> Decimal:
    if not isinstance(additional_data, list):
        return Decimal("0")

    total = Decimal("0")
    for entry in additional_data:
        if not isinstance(entry, dict):
            continue
        value = _to_decimal(entry.get("value"))
        if value is not None and value < 0:
            total += value
    return total


def normalize_receipt(receipt: Mapping[str, Any]) -> ExtractedReceipt:
    """Whitelist and flatten product fields from a Weezmo receipt."""
    receipt_id = _text(receipt.get("id"))
    business = _as_mapping(receipt.get("tBusiness"))
    branch = _as_mapping(receipt.get("tBranch"))
    receipt_total = _to_decimal(receipt.get("total"))
    currency = _text(receipt.get("currency") or business.get("currencyCode"))
    flattened_items = list(_iter_items(receipt.get("items")))

    if not flattened_items:
        raise ExtractionError(
            f"receipt {receipt_id} has no structured items; "
            "this POC does not implement an OCR fallback"
        )

    gross_totals = [_to_decimal(item.get("total")) for item, _, _ in flattened_items]
    candidate_adjustments = [
        _negative_adjustment_candidate(item.get("additionalData"))
        for item, _, _ in flattened_items
    ]
    can_apply_adjustments = (
        receipt_total is not None
        and all(total is not None for total in gross_totals)
        and abs(
            sum(
                (total for total in gross_totals if total is not None),
                start=Decimal("0"),
            )
            + sum(candidate_adjustments, start=Decimal("0"))
            - receipt_total
        )
        <= Decimal("0.02")
    )

    rows: list[dict[str, str]] = []
    for (item, parent_item_id, item_path), candidate_adjustment in zip(
        flattened_items,
        candidate_adjustments,
        strict=True,
    ):
        additional_data = item.get("additionalData")
        adjustment_total = (
            candidate_adjustment if can_apply_adjustments else Decimal("0")
        )
        adjustment_status = (
            "none"
            if candidate_adjustment == 0
            else "applied_reconciled"
            if can_apply_adjustments
            else "not_applied_unreconciled"
        )
        gross_total = _to_decimal(item.get("total"))
        net_total = (
            gross_total + adjustment_total if gross_total is not None else None
        )

        rows.append(
            {
                "receipt_id": receipt_id,
                "business_id": _text(receipt.get("businessID")),
                "business_name": _text(business.get("businessName")),
                "branch_id": _text(receipt.get("branchID")),
                "branch_name": _text(branch.get("branchName")),
                "branch_number": _text(branch.get("internalID")),
                "purchased_at": _text(receipt.get("createdDate")),
                "transaction_number": _text(receipt.get("transactionNumber")),
                "currency": currency,
                "receipt_total": _decimal_text(receipt.get("total")),
                "receipt_type": _text(receipt.get("receiptType")),
                "item_position": str(len(rows) + 1),
                "item_path": item_path,
                "item_id": _text(item.get("id")),
                "parent_item_id": _text(item.get("parentId") or parent_item_id),
                "item_code": _text(item.get("itemCode")),
                "product_name": _text(item.get("name")),
                "unit_price": _decimal_text(item.get("price")),
                "quantity": _decimal_text(item.get("quantity")),
                "gross_line_total": _decimal_text(item.get("total")),
                "api_discount": _decimal_text(item.get("discount")),
                "api_discount_calc": _decimal_text(item.get("discountCalc")),
                "candidate_adjustment_total": _decimal_text(
                    candidate_adjustment
                ),
                "adjustment_total": _decimal_text(adjustment_total),
                "adjustment_status": adjustment_status,
                "net_line_total": _decimal_text(net_total),
                "adjustments_json": _json_text(additional_data),
                "categories_json": _json_text(item.get("categories")),
            }
        )

    return ExtractedReceipt(
        receipt_id=receipt_id,
        currency=currency,
        receipt_total=receipt_total,
        rows=rows,
    )


def write_csv(receipts: Sequence[ExtractedReceipt], output: Path) -> int:
    """Write all normalized receipt rows using an Excel-friendly UTF-8 BOM."""
    output.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0

    with output.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for receipt in receipts:
            writer.writerows(receipt.rows)
            row_count += len(receipt.rows)

    return row_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract structured product lines from Weezmo receipt URLs or UUIDs."
        )
    )
    parser.add_argument(
        "sources",
        nargs="+",
        metavar="URL_OR_RECEIPT_ID",
        help="a receipts.weezmo.com URL or a bare Weezmo receipt UUID",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds (default: 20)",
    )
    return parser


def _deduplicate_sources(sources: Sequence[ReceiptSource]) -> list[ReceiptSource]:
    unique: dict[str, ReceiptSource] = {}
    for source in sources:
        existing = unique.get(source.receipt_id)
        if existing is None:
            unique[source.receipt_id] = source
            continue

        if (
            existing.expected_business_id is not None
            and source.expected_business_id is not None
            and existing.expected_business_id != source.expected_business_id
        ):
            raise ExtractionError(
                f"conflicting business IDs supplied for receipt {source.receipt_id}"
            )

        if (
            existing.expected_business_id is None
            and source.expected_business_id is not None
        ):
            unique[source.receipt_id] = source

    return list(unique.values())


def run_cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        parsed_sources = [parse_receipt_source(value) for value in args.sources]
        unique_sources = _deduplicate_sources(parsed_sources)
        receipts = [
            normalize_receipt(fetch_receipt(source, timeout=args.timeout))
            for source in unique_sources
        ]
        row_count = write_csv(receipts, args.output)
    except ExtractionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {row_count} product rows from {len(receipts)} receipt(s) "
        f"to {args.output}"
    )
    for receipt in receipts:
        total = _decimal_text(receipt.receipt_total)
        difference = (
            receipt.calculated_total - receipt.receipt_total
            if receipt.receipt_total is not None
            else None
        )
        reconciliation = (
            f"matches receipt total {total}"
            if difference is not None and abs(difference) <= Decimal("0.02")
            else f"does not reconcile (calculated difference {_decimal_text(difference)})"
            if difference is not None
            else "could not be reconciled because the receipt total is missing"
        )
        print(
            f"- {receipt.receipt_id}: {len(receipt.rows)} rows, "
            f"{receipt.currency or 'unknown currency'} {receipt.calculated_total} "
            f"calculated; {reconciliation}"
        )
    return 0


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
