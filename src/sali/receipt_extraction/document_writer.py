"""Private, atomic JSON persistence for receipt documents."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

if __package__:
    from .errors import OutputExistsError
    from .models import ReceiptDocument
else:
    from errors import OutputExistsError
    from models import ReceiptDocument


class ReceiptDocumentWriter:
    """Persist receipt documents without exposing or replacing them by accident."""

    def write(
        self,
        document: ReceiptDocument,
        output: Path,
        *,
        force: bool = False,
    ) -> None:
        self._write_payload(
            document.model_dump(mode="json"),
            output,
            force=force,
        )

    @staticmethod
    def _write_payload(
        payload: Mapping[str, object],
        output: Path,
        *,
        force: bool,
    ) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = (
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(file_descriptor, 0o600)
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
                file.write(serialized)
                file.flush()
                os.fsync(file.fileno())

            if force:
                os.replace(temporary_path, output)
                return

            try:
                os.link(temporary_path, output)
            except FileExistsError as exc:
                raise OutputExistsError(output) from exc
            temporary_path.unlink()
        finally:
            temporary_path.unlink(missing_ok=True)
