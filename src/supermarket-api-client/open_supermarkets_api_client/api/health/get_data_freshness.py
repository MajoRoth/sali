from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.data_freshness import DataFreshness
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    chain_id: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_chain_id: None | str | Unset
    if isinstance(chain_id, Unset):
        json_chain_id = UNSET
    else:
        json_chain_id = chain_id
    params["chain_id"] = json_chain_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/health/data-freshness",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | list[DataFreshness] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = DataFreshness.from_dict(response_200_item_data)

            response_200.append(response_200_item)

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
) -> Response[HTTPValidationError | list[DataFreshness]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    chain_id: None | str | Unset = UNSET,
) -> Response[HTTPValidationError | list[DataFreshness]]:
    """Get Data Freshness

     Get data freshness information for chains or a specific chain. Caching is at get_last_update_time
    level.

    Args:
        chain_id (None | str | Unset): Filter by chain ID

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[DataFreshness]]
    """

    kwargs = _get_kwargs(
        chain_id=chain_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    chain_id: None | str | Unset = UNSET,
) -> HTTPValidationError | list[DataFreshness] | None:
    """Get Data Freshness

     Get data freshness information for chains or a specific chain. Caching is at get_last_update_time
    level.

    Args:
        chain_id (None | str | Unset): Filter by chain ID

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[DataFreshness]
    """

    return sync_detailed(
        client=client,
        chain_id=chain_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    chain_id: None | str | Unset = UNSET,
) -> Response[HTTPValidationError | list[DataFreshness]]:
    """Get Data Freshness

     Get data freshness information for chains or a specific chain. Caching is at get_last_update_time
    level.

    Args:
        chain_id (None | str | Unset): Filter by chain ID

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[DataFreshness]]
    """

    kwargs = _get_kwargs(
        chain_id=chain_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    chain_id: None | str | Unset = UNSET,
) -> HTTPValidationError | list[DataFreshness] | None:
    """Get Data Freshness

     Get data freshness information for chains or a specific chain. Caching is at get_last_update_time
    level.

    Args:
        chain_id (None | str | Unset): Filter by chain ID

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[DataFreshness]
    """

    return (
        await asyncio_detailed(
            client=client,
            chain_id=chain_id,
        )
    ).parsed
