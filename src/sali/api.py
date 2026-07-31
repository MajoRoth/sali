"""HTTP API for extracting verified receipt evidence from URLs and images."""

from __future__ import annotations

import logging
import os
import threading
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from sali.cart_comparison.catalog import CatalogUnavailableError
from sali.cart_comparison.models import CartComparison
from sali.cart_comparison.ocr_correction import OcrReceiptCorrector
from sali.cart_comparison.service import CartComparisonService
from sali.nearby.models import (
    GeoPoint,
    NearbyRequest,
    NearbyResponse,
    NearbyUrlRequest,
)
from sali.nearby.service import default_service
from sali.nearby.stores import default_directory
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
type CorrectReceipt = Callable[[ReceiptDocument], ReceiptDocument]
type CompareCart = Callable[[ReceiptDocument, str | None], CartComparison]
type PriceNearby = Callable[[ReceiptDocument, GeoPoint, int, int, bool], NearbyResponse]
type ListNearbyStores = Callable[[float, float, int, int], "NearbyStoreList"]


class NearbyStoreSummary(BaseModel):
    """One real branch near the shopper, with no claim about prices."""

    model_config = ConfigDict(extra="forbid")

    store_id: str
    chain_id: str
    chain: str
    branch: str
    city: str | None
    address: str | None
    lat: float
    lng: float
    distance_m: float


class NearbyStoreList(BaseModel):
    """The branches around a point — true whether or not any price is known."""

    model_config = ConfigDict(extra="forbid")

    stores: list[NearbyStoreSummary]
    total_in_radius: int


class ReceiptExtractionRequest(BaseModel):
    """The untrusted receipt URL supplied by the browser."""

    model_config = ConfigDict(extra="forbid", strict=True)

    url: str


class CartComparisonRequest(BaseModel):
    """A Receipt Document to price, optionally narrowed to one city."""

    model_config = ConfigDict(extra="forbid", strict=True)

    document: ReceiptDocument
    city: str | None = None


class CartComparisonUrlRequest(ReceiptExtractionRequest):
    """Extract a Digital Receipt and price its cart in one call."""

    city: str | None = None


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str


class ApiErrorResponse(BaseModel):
    error: ApiError


logger = logging.getLogger("sali.api")


#: Any loopback origin, on any port.
#:
#: A browser treats `http://localhost:5173` and `http://127.0.0.1:5173` as two
#: different origins even though they are one machine, and Vite silently moves to
#: 5174 when 5173 is taken. Pinning a single string meant the preflight came back
#: as a bare `400 Disallowed CORS origin`, which in the browser surfaces only as a
#: failed fetch — indistinguishable from the API being down.
_LOOPBACK_ORIGIN = r"http://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"


def _cors_origins() -> list[str]:
    configured = os.environ.get("SALI_CORS_ORIGINS", "")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def _cors_origin_regex() -> str | None:
    """Trust loopback unless the deployment names its origins explicitly.

    Setting `SALI_CORS_ORIGINS` turns this off, so a deployed API allows exactly
    what it was configured to allow and nothing else.
    """
    return None if _cors_origins() else _LOOPBACK_ORIGIN


def _logs_failure_detail() -> bool:
    """Whether to log model- and page-derived failure text.

    Off by default: `failure_reason` quotes the merchant page, so it can carry
    receipt content that this service promises not to retain.
    """
    return os.environ.get("SALI_LOG_FAILURE_DETAIL", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _error(status_code: int, code: str, message: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


def _log_failure(
    request: Request,
    request_id: str,
    code: str,
    exc: BaseException | None = None,
) -> None:
    """Record why a request failed without writing receipt content to the log.

    Reconciliation errors name field paths (`receipt.items[3].gross_total`) and
    never carry values, so they are safe to log and are what actually explains a
    rejected extraction.
    """
    details: list[str] = []
    current: BaseException | None = exc
    seen = 0
    while current is not None and seen < 6:
        errors = getattr(current, "errors", None)
        if isinstance(errors, tuple | list):
            details.extend(str(error) for error in errors)
        diagnostics = getattr(current, "diagnostics", None)
        if diagnostics:
            details.append(str(diagnostics))
        if _logs_failure_detail():
            details.append(f"{type(current).__name__}: {current}")
        else:
            details.append(type(current).__name__)
        current = current.__cause__ or current.__context__
        seen += 1

    logger.warning(
        "receipt request failed id=%s path=%s code=%s detail=%s",
        request_id,
        request.url.path,
        code,
        " | ".join(dict.fromkeys(details)) or "none",
    )


def _request_id() -> str:
    return uuid.uuid4().hex[:12]


def _reads_an_image(request: Request) -> bool:
    """Whether the failing route took an upload, so errors name the right input."""
    return request.url.path.endswith("-image") or request.url.path.endswith(
        "-image-total"
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


#: Anywhere real; the directory it builds is nationwide and shared, so the
#: point only decides which rows get filtered, not which get fetched.
_WARM_POINT = (32.0853, 34.7818)


def _warm_directory() -> None:
    try:
        default_directory().nearby(_WARM_POINT, 1)
    except Exception:  # noqa: BLE001 - warming is best-effort by definition
        logger.warning("store directory warm-up failed; it will build on demand")


def _default_price_nearby(
    document: ReceiptDocument,
    location: GeoPoint,
    radius_m: int,
    limit: int,
    include_online: bool,
) -> NearbyResponse:
    return default_service().price(
        document,
        location=location,
        radius_m=radius_m,
        limit=limit,
        include_online=include_online,
    )


def _default_list_nearby_stores(
    lat: float,
    lng: float,
    radius_m: int,
    limit: int,
) -> NearbyStoreList:
    found = default_directory().nearby((lat, lng), radius_m)
    return NearbyStoreList(
        stores=[
            NearbyStoreSummary(
                store_id=record.store.store_id,
                chain_id=record.store.chain_id,
                chain=record.store.chain_name,
                branch=record.store.store_name,
                city=record.store.city,
                address=record.store.address,
                lat=record.store.lat,  # type: ignore[arg-type]
                lng=record.store.lng,  # type: ignore[arg-type]
                distance_m=round(record.distance_m, 1),
            )
            for record in found[:limit]
        ],
        total_in_radius=len(found),
    )


def _corrected[Source](
    extract: Callable[[Source], ReceiptDocument],
    correct: CorrectReceipt,
) -> Callable[[Source], ReceiptDocument]:
    """Extraction with catalogue error-correction applied to its output.

    Composed here, once, so every route that extracts — plain extraction and
    the extract-then-price combinations alike — returns a corrected document
    without each endpoint having to remember to ask.
    """

    def extract_and_correct(source: Source) -> ReceiptDocument:
        return correct(extract(source))

    return extract_and_correct


def create_app(
    extract_receipt: ExtractReceipt | None = None,
    extract_receipt_image: ExtractReceiptImage | None = None,
    extract_receipt_image_total: ExtractReceiptImageTotal | None = None,
    correct_receipt: CorrectReceipt | None = None,
    compare_cart: CompareCart | None = None,
    price_nearby: PriceNearby | None = None,
    list_nearby_stores: ListNearbyStores | None = None,
) -> FastAPI:
    """Create an API app; injection keeps contract tests independent of OpenAI
    and of the price catalogue."""
    corrector = correct_receipt or OcrReceiptCorrector().correct
    extractor = _corrected(
        extract_receipt or OpenAIReceiptExtractor().extract, corrector
    )
    image_extractor = _corrected(
        extract_receipt_image or OpenAIReceiptImageExtractor().extract, corrector
    )
    image_total_extractor = (
        extract_receipt_image_total or OpenAIReceiptImageTotalExtractor().extract
    )
    cart_comparer = compare_cart or (
        lambda document, city: CartComparisonService().compare(document, city=city)
    )
    nearby_pricer = price_nearby or _default_price_nearby
    store_lister = list_nearby_stores or _default_list_nearby_stores
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        """Assemble the store directory before the first shopper needs it.

        It is around sixty upstream calls and a good fifteen seconds, cached for
        hours afterwards — so whoever arrives first would otherwise pay for
        everyone. Done on a daemon thread because it is an optimisation: if it
        is slow or fails, requests still work, they just build it themselves.
        """
        warm = threading.Thread(
            target=_warm_directory, name="sali-warm-directory", daemon=True
        )
        warm.start()
        yield

    app = FastAPI(
        lifespan=lifespan,
        title="sali Receipt API",
        version="0.2.0",
        description=(
            "Extract a reconciled Receipt Document from one public HTTPS URL "
            "or one uploaded Receipt Image, and price its cart across the "
            "supermarkets that stock every item."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://34.165.235.189:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        path = request.url.path
        if path == "/api/stores/nearby":
            message = "A lat and lng are required."
        elif path == "/api/carts/nearby":
            message = "A Receipt Document and a location are required."
        elif path == "/api/carts/nearby-url":
            message = "A receipt URL and a location are required."
        elif path == "/api/carts/nearby-image":
            message = "A receipt image and a location are required."
        elif path == "/api/carts/compare":
            message = "A Receipt Document is required."
        elif _reads_an_image(request):
            message = "A receipt image is required."
        else:
            message = "A receipt URL is required."
        return _error(422, "invalid_request", message, _request_id())

    @app.exception_handler(InvalidReceiptUrlError)
    async def invalid_url(
        _request: Request, _exc: InvalidReceiptUrlError
    ) -> JSONResponse:
        return _error(
            422,
            "invalid_url",
            "Use a public HTTPS link to a receipt.",
            _request_id(),
        )

    @app.exception_handler(InvalidReceiptImageError)
    async def invalid_image(
        _request: Request,
        _exc: InvalidReceiptImageError,
    ) -> JSONResponse:
        return _error(
            422,
            "invalid_image",
            "Upload one JPEG, PNG, or WEBP receipt image no larger than 10 MiB.",
            _request_id(),
        )

    @app.exception_handler(ReceiptInspectionFailure)
    async def inspection_failed(
        request: Request,
        exc: ReceiptInspectionFailure,
    ) -> JSONResponse:
        request_id = _request_id()
        _log_failure(request, request_id, exc.failure_code, exc)
        return _error(
            422,
            exc.failure_code,
            _safe_failure_message(exc.failure_code, is_image=_reads_an_image(request)),
            request_id,
        )

    @app.exception_handler(HostedReceiptError)
    async def extraction_unavailable(
        request: Request,
        exc: HostedReceiptError,
    ) -> JSONResponse:
        request_id = _request_id()
        _log_failure(request, request_id, "extraction_unavailable", exc)
        return _error(
            503,
            "extraction_unavailable",
            "Receipt extraction is temporarily unavailable. Please try again.",
            request_id,
        )

    @app.exception_handler(CatalogUnavailableError)
    async def catalog_unavailable(
        request: Request,
        exc: CatalogUnavailableError,
    ) -> JSONResponse:
        request_id = _request_id()
        _log_failure(request, request_id, "price_database_unavailable", exc)
        return _error(
            503,
            "price_database_unavailable",
            "The price database is temporarily unavailable. Please try again.",
            request_id,
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

    @app.post(
        "/api/carts/compare",
        response_model=CartComparison,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    def compare(request: CartComparisonRequest) -> CartComparison:
        """Price an already-extracted Receipt Document across stores."""
        # Saved receipts can predate catalogue correction.  The pass is
        # idempotent and shares the catalogue cache with pricing, so correcting
        # at this ingress fixes old documents without repeating network work.
        return cart_comparer(corrector(request.document), request.city)

    @app.post(
        "/api/carts/compare-url",
        response_model=CartComparison,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    def compare_url(request: CartComparisonUrlRequest) -> CartComparison:
        """Extract a Digital Receipt and rank stores for its cart in one call."""
        ReceiptUrlValidator().validate(request.url)
        return cart_comparer(extractor(request.url), request.city)

    @app.post(
        "/api/carts/compare-image",
        response_model=CartComparison,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    async def compare_image(
        image: Annotated[UploadFile, File(...)],
        city: Annotated[str | None, Form()] = None,
    ) -> CartComparison:
        """Extract a Receipt Image and rank stores for its cart in one call."""
        document = image_extractor(await validated_receipt_image(image))
        return cart_comparer(document, city)

    # -- Nearby: the app's own view, in `docs/nearby-schema.md` terms ---------
    #
    # These are camelCase on the wire while everything above is snake_case. See
    # `sali.nearby.models` for why that split is deliberate and contained.

    @app.get(
        "/api/stores/nearby",
        response_model=NearbyStoreList,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    def stores_nearby(
        lat: Annotated[float, Query(ge=-90.0, le=90.0)],
        lng: Annotated[float, Query(ge=-180.0, le=180.0)],
        radius_m: Annotated[int, Query(gt=0, le=50_000)] = 5_000,
        limit: Annotated[int, Query(gt=0, le=200)] = 50,
    ) -> NearbyStoreList:
        """The real branches around a point, whether or not prices are known."""
        return store_lister(lat, lng, radius_m, limit)

    @app.post(
        "/api/carts/nearby",
        response_model=NearbyResponse,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    def nearby(request: NearbyRequest) -> NearbyResponse:
        """Price an extracted receipt against the stores around the shopper."""
        return nearby_pricer(
            corrector(request.document),
            request.location,
            request.radius_m,
            request.limit,
            request.include_online,
        )

    @app.post(
        "/api/carts/nearby-url",
        response_model=NearbyResponse,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    def nearby_url(request: NearbyUrlRequest) -> NearbyResponse:
        """Extract a Digital Receipt and price it nearby, in one call."""
        ReceiptUrlValidator().validate(request.url)
        return nearby_pricer(
            extractor(request.url),
            request.location,
            request.radius_m,
            request.limit,
            request.include_online,
        )

    @app.post(
        "/api/carts/nearby-image",
        response_model=NearbyResponse,
        responses={422: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
    )
    async def nearby_image(
        image: Annotated[UploadFile, File(...)],
        lat: Annotated[float, Form(ge=-90.0, le=90.0)],
        lng: Annotated[float, Form(ge=-180.0, le=180.0)],
        radius_m: Annotated[int, Form(gt=0, le=50_000)] = 5_000,
        limit: Annotated[int, Form(gt=0, le=200)] = 30,
        include_online: Annotated[bool, Form()] = False,
    ) -> NearbyResponse:
        """Extract a Receipt Image and price it nearby, in one call."""
        document = image_extractor(await validated_receipt_image(image))
        return nearby_pricer(
            document, GeoPoint(lat=lat, lng=lng), radius_m, limit, include_online
        )

    return app


app = create_app()


def main() -> None:
    """Run the trusted local development server."""
    import uvicorn
    uvicorn.run("sali.api:app", host="0.0.0.0", port=8000, reload=True)
