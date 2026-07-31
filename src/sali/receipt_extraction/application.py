"""Command-line application orchestration for automatic receipt extraction."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

if __package__:
    from .errors import HostedReceiptError, OutputExistsError
    from .models import ReceiptDocument
else:
    from errors import HostedReceiptError, OutputExistsError
    from models import ReceiptDocument

ExtractReceipt = Callable[[str], ReceiptDocument]
WriteReceipt = Callable[..., None]


class ReceiptExtractionApplication:
    """Coordinate CLI parsing, extraction, persistence, and user-facing errors."""

    def __init__(
        self,
        output_file: Path,
        extract_receipt: ExtractReceipt,
        write_receipt: WriteReceipt,
    ) -> None:
        self._output_file = output_file
        self._extract_receipt = extract_receipt
        self._write_receipt = write_receipt

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description=(
                "Extract one Digital Receipt URL using hosted browsing with "
                "a generic rendered-page fallback."
            )
        )
        parser.add_argument(
            "url",
            metavar="DIGITAL_RECEIPT_URL",
            help="one public HTTPS Digital Receipt URL",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=f"replace the existing {self._output_file.name}",
        )
        return parser

    def run(self, argv: list[str] | None = None) -> int:
        args = self.build_parser().parse_args(argv)

        if self._output_file.exists() and not args.force:
            self._print_output_exists()
            return 2

        try:
            document = self._extract_receipt(args.url)
            self._write_receipt(
                document,
                self._output_file,
                force=args.force,
            )
        except OutputExistsError:
            self._print_output_exists()
            return 2
        except HostedReceiptError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(
            f"Wrote {len(document.receipt.items)} product item(s) "
            f"to {self._output_file}"
        )
        return 0

    def _print_output_exists(self) -> None:
        print(
            f"error: output already exists: {self._output_file}; "
            "pass --force to replace it",
            file=sys.stderr,
        )
