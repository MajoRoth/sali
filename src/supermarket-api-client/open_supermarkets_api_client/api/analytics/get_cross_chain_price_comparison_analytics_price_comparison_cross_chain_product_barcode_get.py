from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.cross_chain_price_comparison_response import CrossChainPriceComparisonResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    product_barcode: int,
    *,
    current_only: bool | Unset = True,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["current_only"] = current_only

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/analytics/price-comparison/cross-chain/{product_barcode}".format(
            product_barcode=quote(str(product_barcode), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CrossChainPriceComparisonResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = CrossChainPriceComparisonResponse.from_dict(response.json())

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
) -> Response[CrossChainPriceComparisonResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    product_barcode: int,
    *,
    client: AuthenticatedClient | Client,
    current_only: bool | Unset = True,
) -> Response[CrossChainPriceComparisonResponse | HTTPValidationError]:
    """Get Cross Chain Price Comparison

    Args:
        product_barcode (int):
        current_only (bool | Unset):  Default: True.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CrossChainPriceComparisonResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        product_barcode=product_barcode,
        current_only=current_only,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    product_barcode: int,
    *,
    client: AuthenticatedClient | Client,
    current_only: bool | Unset = True,
) -> CrossChainPriceComparisonResponse | HTTPValidationError | None:
    """Get Cross Chain Price Comparison

    Args:
        product_barcode (int):
        current_only (bool | Unset):  Default: True.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CrossChainPriceComparisonResponse | HTTPValidationError
    """

    return sync_detailed(
        product_barcode=product_barcode,
        client=client,
        current_only=current_only,
    ).parsed


async def asyncio_detailed(
    product_barcode: int,
    *,
    client: AuthenticatedClient | Client,
    current_only: bool | Unset = True,
) -> Response[CrossChainPriceComparisonResponse | HTTPValidationError]:
    """Get Cross Chain Price Comparison

    Args:
        product_barcode (int):
        current_only (bool | Unset):  Default: True.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CrossChainPriceComparisonResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        product_barcode=product_barcode,
        current_only=current_only,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    product_barcode: int,
    *,
    client: AuthenticatedClient | Client,
    current_only: bool | Unset = True,
) -> CrossChainPriceComparisonResponse | HTTPValidationError | None:
    """Get Cross Chain Price Comparison

    Args:
        product_barcode (int):
        current_only (bool | Unset):  Default: True.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CrossChainPriceComparisonResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            product_barcode=product_barcode,
            client=client,
            current_only=current_only,
        )
    ).parsed
