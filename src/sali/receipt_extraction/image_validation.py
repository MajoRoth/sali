"""Admission policy for user-supplied Receipt Images."""

from __future__ import annotations

from typing import cast

from .errors import InvalidReceiptImageError
from .receipt_image import ReceiptImage, ReceiptImageMediaType

MAX_RECEIPT_IMAGE_BYTES = 10 * 1024 * 1024

_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_WEBP_RIFF_SIGNATURE = b"RIFF"
_WEBP_SIGNATURE = b"WEBP"
_SUPPORTED_MEDIA_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


class ReceiptImageValidator:
    """Validate declared media type, bounded size, and recognizable image bytes."""

    def validate(self, data: bytes, declared_media_type: str | None) -> ReceiptImage:
        if not data:
            raise InvalidReceiptImageError("receipt image is empty")
        if len(data) > MAX_RECEIPT_IMAGE_BYTES:
            raise InvalidReceiptImageError("receipt image exceeds the size limit")

        media_type = self._normalize_media_type(declared_media_type)
        actual_media_type = self._detect_media_type(data)
        if media_type != actual_media_type:
            raise InvalidReceiptImageError(
                "receipt image media type does not match its bytes"
            )

        return ReceiptImage(data=data, media_type=actual_media_type)

    @staticmethod
    def _normalize_media_type(value: str | None) -> ReceiptImageMediaType:
        media_type = (value or "").split(";", 1)[0].strip().lower()
        if media_type not in _SUPPORTED_MEDIA_TYPES:
            raise InvalidReceiptImageError("receipt image media type is unsupported")
        return cast(ReceiptImageMediaType, media_type)

    @staticmethod
    def _detect_media_type(data: bytes) -> ReceiptImageMediaType:
        if data.startswith(_JPEG_SIGNATURE):
            return "image/jpeg"
        if data.startswith(_PNG_SIGNATURE):
            return "image/png"
        if data.startswith(_WEBP_RIFF_SIGNATURE) and data[8:12] == _WEBP_SIGNATURE:
            return "image/webp"
        raise InvalidReceiptImageError(
            "receipt image bytes are unsupported or unreadable"
        )
