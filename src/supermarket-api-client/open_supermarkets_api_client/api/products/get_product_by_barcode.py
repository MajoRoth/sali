from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.product_barcode_response import ProductBarcodeResponse
from ...types import Response


def _get_kwargs(
    barcode: int,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/products/barcode/{barcode}".format(
            barcode=quote(str(barcode), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | ProductBarcodeResponse | None:
    if response.status_code == 200:
        response_200 = ProductBarcodeResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | ProductBarcodeResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    barcode: int,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | ProductBarcodeResponse]:
    """Find By Barcode

     Find product by barcode.

    Args:
        barcode (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProductBarcodeResponse]
    """

    kwargs = _get_kwargs(
        barcode=barcode,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    barcode: int,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | ProductBarcodeResponse | None:
    """Find By Barcode

     Find product by barcode.

    Args:
        barcode (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProductBarcodeResponse
    """

    return sync_detailed(
        barcode=barcode,
        client=client,
    ).parsed


async def asyncio_detailed(
    barcode: int,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | ProductBarcodeResponse]:
    """Find By Barcode

     Find product by barcode.

    Args:
        barcode (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProductBarcodeResponse]
    """

    kwargs = _get_kwargs(
        barcode=barcode,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    barcode: int,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | ProductBarcodeResponse | None:
    """Find By Barcode

     Find product by barcode.

    Args:
        barcode (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProductBarcodeResponse
    """

    return (
        await asyncio_detailed(
            barcode=barcode,
            client=client,
        )
    ).parsed
