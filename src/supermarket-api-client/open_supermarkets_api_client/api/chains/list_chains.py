from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_chains_response import GetChainsResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_include_stores: bool | None | Unset
    if isinstance(include_stores, Unset):
        json_include_stores = UNSET
    else:
        json_include_stores = include_stores
    params["includeStores"] = json_include_stores

    json_include_stats: bool | None | Unset
    if isinstance(include_stats, Unset):
        json_include_stats = UNSET
    else:
        json_include_stats = include_stats
    params["includeStats"] = json_include_stats

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/chains/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> GetChainsResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = GetChainsResponse.from_dict(response.json())

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
) -> Response[GetChainsResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> Response[GetChainsResponse | HTTPValidationError]:
    """Get Chains

     Get all chains with optional store information and statistics.

    Args:
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetChainsResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        include_stores=include_stores,
        include_stats=include_stats,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> GetChainsResponse | HTTPValidationError | None:
    """Get Chains

     Get all chains with optional store information and statistics.

    Args:
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetChainsResponse | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        include_stores=include_stores,
        include_stats=include_stats,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> Response[GetChainsResponse | HTTPValidationError]:
    """Get Chains

     Get all chains with optional store information and statistics.

    Args:
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetChainsResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        include_stores=include_stores,
        include_stats=include_stats,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> GetChainsResponse | HTTPValidationError | None:
    """Get Chains

     Get all chains with optional store information and statistics.

    Args:
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetChainsResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            include_stores=include_stores,
            include_stats=include_stats,
        )
    ).parsed
