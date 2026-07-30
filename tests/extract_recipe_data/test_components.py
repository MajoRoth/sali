"""Tests for receipt extraction support components."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from scripts.extract_recipe_data.credentials import ApiKeyProvider
from scripts.extract_recipe_data.document_writer import ReceiptDocumentWriter
from scripts.extract_recipe_data.errors import HostedReceiptError, OutputExistsError
from scripts.extract_recipe_data.models import NormalizedReceipt, validate_and_reconcile
from scripts.extract_recipe_data.url_validation import ReceiptUrlValidator


def receipt_document():
    receipt = NormalizedReceipt.model_validate(
        {
            "merchant": {
                "name": "Example Market",
                "branch_name": None,
                "branch_number": None,
            },
            "transaction": {
                "receipt_id": None,
                "purchased_at": None,
                "transaction_number": None,
                "type": "purchase",
                "currency": "ILS",
            },
            "totals": {
                "subtotal": "10.00",
                "discounts": "0",
                "total": "10.00",
            },
            "items": [
                {
                    "position": 1,
                    "code": None,
                    "name": "Example product",
                    "categories": [],
                    "quantity": "1",
                    "unit": "item",
                    "unit_price": "10.00",
                    "gross_total": "10.00",
                    "adjustments": [],
                    "final_total": "10.00",
                }
            ],
        }
    )
    return validate_and_reconcile(receipt)


def test_api_key_provider_uses_injected_environment_and_env_file(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY='file-key'\n", encoding="utf-8")
    environment: dict[str, str] = {}

    assert ApiKeyProvider(env_file, environment).load() == "file-key"
    assert environment == {"OPENAI_API_KEY": "file-key"}

    environment["OPENAI_API_KEY"] = "shell-key"
    assert ApiKeyProvider(env_file, environment).load() == "shell-key"


def test_api_key_provider_rejects_empty_configuration(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=''\n", encoding="utf-8")

    with pytest.raises(HostedReceiptError, match="not configured"):
        ApiKeyProvider(env_file, {}).load()


def test_url_validator_normalizes_hostname_and_default_path() -> None:
    assert ReceiptUrlValidator().validate("https://Receipt.Example") == (
        "https://receipt.example/",
        "receipt.example",
    )


def test_document_writer_is_private_and_requires_force_to_replace(
    tmp_path: Path,
) -> None:
    output = tmp_path / "receipt.json"
    writer = ReceiptDocumentWriter()

    writer.write(receipt_document(), output)

    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "1.0"

    with pytest.raises(OutputExistsError):
        writer.write(receipt_document(), output)

    writer.write(receipt_document(), output, force=True)
