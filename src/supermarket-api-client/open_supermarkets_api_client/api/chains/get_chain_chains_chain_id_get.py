from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.chain_response import ChainResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    chain_id: str,
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
        "url": "/chains/{chain_id}".format(
            chain_id=quote(str(chain_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ChainResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ChainResponse.from_dict(response.json())

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
) -> Response[ChainResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    chain_id: str,
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> Response[ChainResponse | HTTPValidationError]:
    """Get Chain

    Args:
        chain_id (str):
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ChainResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        chain_id=chain_id,
        include_stores=include_stores,
        include_stats=include_stats,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    chain_id: str,
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> ChainResponse | HTTPValidationError | None:
    """Get Chain

    Args:
        chain_id (str):
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ChainResponse | HTTPValidationError
    """

    return sync_detailed(
        chain_id=chain_id,
        client=client,
        include_stores=include_stores,
        include_stats=include_stats,
    ).parsed


async def asyncio_detailed(
    chain_id: str,
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> Response[ChainResponse | HTTPValidationError]:
    """Get Chain

    Args:
        chain_id (str):
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ChainResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        chain_id=chain_id,
        include_stores=include_stores,
        include_stats=include_stats,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    chain_id: str,
    *,
    client: AuthenticatedClient | Client,
    include_stores: bool | None | Unset = False,
    include_stats: bool | None | Unset = False,
) -> ChainResponse | HTTPValidationError | None:
    """Get Chain

    Args:
        chain_id (str):
        include_stores (bool | None | Unset): Include store information Default: False.
        include_stats (bool | None | Unset): Include chain statistics Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ChainResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            chain_id=chain_id,
            client=client,
            include_stores=include_stores,
            include_stats=include_stats,
        )
    ).parsed
