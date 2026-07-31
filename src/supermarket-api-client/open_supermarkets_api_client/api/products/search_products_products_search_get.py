from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.product_search_page import ProductSearchPage
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    query: str,
    store_id: None | str | Unset = UNSET,
    chain_id: None | str | Unset = UNSET,
    active: bool | Unset = False,
    limit: int | Unset = 10,
    offset: int | Unset = 0,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["query"] = query

    json_store_id: None | str | Unset
    if isinstance(store_id, Unset):
        json_store_id = UNSET
    else:
        json_store_id = store_id
    params["store_id"] = json_store_id

    json_chain_id: None | str | Unset
    if isinstance(chain_id, Unset):
        json_chain_id = UNSET
    else:
        json_chain_id = chain_id
    params["chain_id"] = json_chain_id

    params["active"] = active

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/products/search",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | ProductSearchPage | None:
    if response.status_code == 200:
        response_200 = ProductSearchPage.from_dict(response.json())

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
) -> Response[HTTPValidationError | ProductSearchPage]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    store_id: None | str | Unset = UNSET,
    chain_id: None | str | Unset = UNSET,
    active: bool | Unset = False,
    limit: int | Unset = 10,
    offset: int | Unset = 0,
) -> Response[HTTPValidationError | ProductSearchPage]:
    """Search Products

    Args:
        query (str): Search query for product name
        store_id (None | str | Unset): Filter by store ID
        chain_id (None | str | Unset): Filter by chain ID
        active (bool | Unset): Show only products that have active listing Default: False.
        limit (int | Unset): Max items (max 100) Default: 10.
        offset (int | Unset): Items to skip Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProductSearchPage]
    """

    kwargs = _get_kwargs(
        query=query,
        store_id=store_id,
        chain_id=chain_id,
        active=active,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    store_id: None | str | Unset = UNSET,
    chain_id: None | str | Unset = UNSET,
    active: bool | Unset = False,
    limit: int | Unset = 10,
    offset: int | Unset = 0,
) -> HTTPValidationError | ProductSearchPage | None:
    """Search Products

    Args:
        query (str): Search query for product name
        store_id (None | str | Unset): Filter by store ID
        chain_id (None | str | Unset): Filter by chain ID
        active (bool | Unset): Show only products that have active listing Default: False.
        limit (int | Unset): Max items (max 100) Default: 10.
        offset (int | Unset): Items to skip Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProductSearchPage
    """

    return sync_detailed(
        client=client,
        query=query,
        store_id=store_id,
        chain_id=chain_id,
        active=active,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    store_id: None | str | Unset = UNSET,
    chain_id: None | str | Unset = UNSET,
    active: bool | Unset = False,
    limit: int | Unset = 10,
    offset: int | Unset = 0,
) -> Response[HTTPValidationError | ProductSearchPage]:
    """Search Products

    Args:
        query (str): Search query for product name
        store_id (None | str | Unset): Filter by store ID
        chain_id (None | str | Unset): Filter by chain ID
        active (bool | Unset): Show only products that have active listing Default: False.
        limit (int | Unset): Max items (max 100) Default: 10.
        offset (int | Unset): Items to skip Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProductSearchPage]
    """

    kwargs = _get_kwargs(
        query=query,
        store_id=store_id,
        chain_id=chain_id,
        active=active,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    store_id: None | str | Unset = UNSET,
    chain_id: None | str | Unset = UNSET,
    active: bool | Unset = False,
    limit: int | Unset = 10,
    offset: int | Unset = 0,
) -> HTTPValidationError | ProductSearchPage | None:
    """Search Products

    Args:
        query (str): Search query for product name
        store_id (None | str | Unset): Filter by store ID
        chain_id (None | str | Unset): Filter by chain ID
        active (bool | Unset): Show only products that have active listing Default: False.
        limit (int | Unset): Max items (max 100) Default: 10.
        offset (int | Unset): Items to skip Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProductSearchPage
    """

    return (
        await asyncio_detailed(
            client=client,
            query=query,
            store_id=store_id,
            chain_id=chain_id,
            active=active,
            limit=limit,
            offset=offset,
        )
    ).parsed
