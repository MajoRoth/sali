"""Validated in-memory Receipt Image evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReceiptImageMediaType = Literal["image/jpeg", "image/png", "image/webp"]


@dataclass(frozen=True)
class ReceiptImage:
    """One validated image upload kept only for the current extraction request."""

    data: bytes
    media_type: ReceiptImageMediaType
