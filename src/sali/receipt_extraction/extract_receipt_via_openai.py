"""Compatibility entry point for automatic Digital Receipt extraction."""

from __future__ import annotations

import os
from argparse import ArgumentParser
from pathlib import Path

if __package__:
    from .application import ReceiptExtractionApplication
    from .configuration import (
        ENV_FILE,
        HOSTED_EXTRACTION_PROMPT,
        MODEL,
        OUTPUT_FILE,
        PAGE_EXTRACTION_PROMPT,
    )
    from .credentials import ApiKeyProvider
    from .document_writer import ReceiptDocumentWriter
    from .errors import HostedReceiptError, OutputExistsError
    from .hosted_extractor import (
        HostedReceiptExtractor,
        HostedReceiptInspection,
        OpenAIReceiptExtractor,
        _OpenAIClient,
    )
    from .models import ReceiptDocument
    from .url_validation import ReceiptUrlValidator
else:
    from application import ReceiptExtractionApplication
    from configuration import (
        ENV_FILE,
        HOSTED_EXTRACTION_PROMPT,
        MODEL,
        OUTPUT_FILE,
        PAGE_EXTRACTION_PROMPT,
    )
    from credentials import ApiKeyProvider
    from document_writer import ReceiptDocumentWriter
    from errors import HostedReceiptError, OutputExistsError
    from hosted_extractor import (
        HostedReceiptExtractor,
        HostedReceiptInspection,
        OpenAIReceiptExtractor,
        _OpenAIClient,
    )
    from models import ReceiptDocument
    from url_validation import ReceiptUrlValidator


def extract_receipt_url_via_openai(url: str) -> ReceiptDocument:
    """Inspect one URL through hosted or rendered evidence and return a receipt."""
    return OpenAIReceiptExtractor().extract(url)


def _extract_with_client(
    url: str,
    *,
    client: _OpenAIClient,
) -> ReceiptDocument:
    return HostedReceiptExtractor(client).extract(url)


def _validate_receipt_url(url: str) -> tuple[str, str]:
    return ReceiptUrlValidator().validate(url)


def _load_api_key(*, env_file: Path = ENV_FILE) -> str:
    return ApiKeyProvider(env_file).load()


def write_receipt_document(
    document: ReceiptDocument,
    output: Path,
    *,
    force: bool = False,
) -> None:
    """Write one private UTF-8 JSON document without accidental replacement."""
    ReceiptDocumentWriter().write(document, output, force=force)


def _application() -> ReceiptExtractionApplication:
    return ReceiptExtractionApplication(
        output_file=OUTPUT_FILE,
        extract_receipt=extract_receipt_url_via_openai,
        write_receipt=write_receipt_document,
    )


def build_parser() -> ArgumentParser:
    return _application().build_parser()


def run_cli(argv: list[str] | None = None) -> int:
    return _application().run(argv)


def main() -> None:
    raise SystemExit(run_cli())


__all__ = [
    "HOSTED_EXTRACTION_PROMPT",
    "MODEL",
    "OUTPUT_FILE",
    "PAGE_EXTRACTION_PROMPT",
    "ApiKeyProvider",
    "HostedReceiptError",
    "HostedReceiptExtractor",
    "HostedReceiptInspection",
    "OpenAIReceiptExtractor",
    "OutputExistsError",
    "ReceiptDocumentWriter",
    "ReceiptExtractionApplication",
    "ReceiptUrlValidator",
    "extract_receipt_url_via_openai",
    "main",
    "os",
    "run_cli",
    "write_receipt_document",
]


if __name__ == "__main__":
    main()
