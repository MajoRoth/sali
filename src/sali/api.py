"""HTTP API for extracting verified receipt evidence from URLs and images."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Annotated

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from sali.receipt_extraction.errors import (
    HostedReceiptError,
    InvalidReceiptImageError,
    InvalidReceiptUrlError,
    ReceiptInspectionFailure,
)
from sali.receipt_extraction.hosted_extractor import OpenAIReceiptExtractor
from sali.receipt_extraction.image_extractor import OpenAIReceiptImageExtractor
from sali.receipt_extraction.image_total_extractor import (
    OpenAIReceiptImageTotalExtractor,
)
from sali.receipt_extraction.image_validation import (
    MAX_RECEIPT_IMAGE_BYTES,
    ReceiptImageValidator,
)
from sali.receipt_extraction.models import ReceiptDocument, ReceiptImageTotalDocument
from sali.receipt_extraction.receipt_image import ReceiptImage
from sali.receipt_extraction.url_validation import ReceiptUrlValidator

type ExtractReceipt = Callable[[str], ReceiptDocument]
type ExtractReceiptImage = Callable[[ReceiptImage], ReceiptDocument]
type ExtractReceiptImageTotal = Callable[[ReceiptImage], ReceiptImageTotalDocument]


class ReceiptExtractionRequest(BaseModel):
    """The untrusted receipt URL supplied by the browser."""

    model_config = ConfigDict(extra="forbid", strict=True)

    url: str


class ApiError(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    error: ApiError


def _cors_origins() -> list[str]:
    configured = os.environ.get("SALI_CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _safe_failure_message(code: str, *, is_image: bool) -> str:
    messages = (
        {
            "blocked": "The receipt image could not be accessed.",
            "insufficient_evidence": "The image did not contain enough receipt information.",
            "not_receipt": "The image did not show a receipt.",
            "refused": "The receipt image could not be processed.",
            "unreachable": "The receipt image could not be processed.",
        }
        if is_image
        else {
            "blocked": "The receipt link could not be accessed.",
            "insufficient_evidence": "The link did not contain enough receipt information.",
            "not_receipt": "The link did not lead to a Digital Receipt.",
            "refused": "The receipt link could not be processed.",
            "unreachable": "The receipt link could not be reached.",
        }
    )
    return messages.get(
        code,
        "The receipt image could not be verified."
        if is_image
        else "The receipt link could not be verified.",
    )


def create_app(
    extract_receipt: ExtractReceipt | None = None,
    extract_receipt_image: ExtractReceiptImage | None = None,
    extract_receipt_image_total: ExtractReceiptImageTotal | None = None,
) -> FastAPI:
    """Create an API app; injection keeps contract tests independent of OpenAI."""
    extractor = extract_receipt or OpenAIReceiptExtractor().extract
    image_extractor = extract_receipt_image or OpenAIReceiptImageExtractor().extract
    image_total_extractor = (
        extract_receipt_image_total or OpenAIReceiptImageTotalExtractor().extract
    )
    app = FastAPI(
        title="sali Receipt API",
        version="0.1.0",
        description=(
            "Extract a reconciled Receipt Document from one public HTTPS URL "
            "or one uploaded Receipt Image."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        message = (
            "A receipt image is required."
            if request.url.path.startswith("/api/receipts/extract-image")
            else "A receipt URL is required."
        )
        return _error(422, "invalid_request", message)

    @app.exception_handler(InvalidReceiptUrlError)
    async def invalid_url(
        _request: Request, _exc: InvalidReceiptUrlError
    ) -> JSONResponse:
        return _error(422, "invalid_url", "Use a public HTTPS link to a receipt.")

    @app.exception_handler(InvalidReceiptImageError)
    async def invalid_image(
        _request: Request,
        _exc: InvalidReceiptImageError,
    ) -> JSONResponse:
        return _error(
            422,
            "invalid_image",
            "Upload one JPEG, PNG, or WEBP receipt image no larger than 10 MiB.",
        )

    @app.exception_handler(ReceiptInspectionFailure)
    async def inspection_failed(
        request: Request,
        exc: ReceiptInspectionFailure,
    ) -> JSONResponse:
        return _error(
            422,
            exc.failure_code,
            _safe_failure_message(
                exc.failure_code,
                is_image=request.url.path.startswith("/api/receipts/extract-image"),
            ),
        )

    @app.exception_handler(HostedReceiptError)
    async def extraction_unavailable(
        _request: Request,
        _exc: HostedReceiptError,
    ) -> JSONResponse:
        return _error(
            503,
            "extraction_unavailable",
            "Receipt extraction is temporarily unavailable. Please try again.",
        )

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/api/receipts/extract",
        response_model=ReceiptDocument,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    def extract(request: ReceiptExtractionRequest) -> ReceiptDocument:
        """Synchronously extract one receipt without retaining its URL or output."""
        ReceiptUrlValidator().validate(request.url)
        return extractor(request.url)

    async def validated_receipt_image(
        image: UploadFile,
    ) -> ReceiptImage:
        try:
            data = await image.read(MAX_RECEIPT_IMAGE_BYTES + 1)
            return ReceiptImageValidator().validate(data, image.content_type)
        finally:
            await image.close()

    @app.post(
        "/api/receipts/extract-image",
        response_model=ReceiptDocument,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    async def extract_image(image: Annotated[UploadFile, File(...)]) -> ReceiptDocument:
        """Extract one Receipt Image without retaining the upload or output."""
        return image_extractor(await validated_receipt_image(image))

    @app.post(
        "/api/receipts/extract-image-total",
        response_model=ReceiptImageTotalDocument,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    async def extract_image_total(
        image: Annotated[UploadFile, File(...)],
    ) -> ReceiptImageTotalDocument:
        """Extract a verified Receipt Image Total without retaining the upload."""
        return image_total_extractor(await validated_receipt_image(image))

    return app


app = create_app()


def main() -> None:
    """Run the trusted local development server."""
    import uvicorn

    uvicorn.run("sali.api:app", host="127.0.0.1", port=8000, reload=True)
