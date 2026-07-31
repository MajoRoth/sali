from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.chain_data_status import ChainDataStatus
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    chain_id: str,
    *,
    stale_threshold_hours: int | Unset = 24,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["stale_threshold_hours"] = stale_threshold_hours

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/health/pipeline/chain/{chain_id}".format(
            chain_id=quote(str(chain_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ChainDataStatus | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ChainDataStatus.from_dict(response.json())

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
) -> Response[ChainDataStatus | HTTPValidationError]:
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
    stale_threshold_hours: int | Unset = 24,
) -> Response[ChainDataStatus | HTTPValidationError]:
    """Get Chain Pipeline Status

    Args:
        chain_id (str):
        stale_threshold_hours (int | Unset):  Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ChainDataStatus | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        chain_id=chain_id,
        stale_threshold_hours=stale_threshold_hours,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    chain_id: str,
    *,
    client: AuthenticatedClient | Client,
    stale_threshold_hours: int | Unset = 24,
) -> ChainDataStatus | HTTPValidationError | None:
    """Get Chain Pipeline Status

    Args:
        chain_id (str):
        stale_threshold_hours (int | Unset):  Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ChainDataStatus | HTTPValidationError
    """

    return sync_detailed(
        chain_id=chain_id,
        client=client,
        stale_threshold_hours=stale_threshold_hours,
    ).parsed


async def asyncio_detailed(
    chain_id: str,
    *,
    client: AuthenticatedClient | Client,
    stale_threshold_hours: int | Unset = 24,
) -> Response[ChainDataStatus | HTTPValidationError]:
    """Get Chain Pipeline Status

    Args:
        chain_id (str):
        stale_threshold_hours (int | Unset):  Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ChainDataStatus | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        chain_id=chain_id,
        stale_threshold_hours=stale_threshold_hours,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    chain_id: str,
    *,
    client: AuthenticatedClient | Client,
    stale_threshold_hours: int | Unset = 24,
) -> ChainDataStatus | HTTPValidationError | None:
    """Get Chain Pipeline Status

    Args:
        chain_id (str):
        stale_threshold_hours (int | Unset):  Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ChainDataStatus | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            chain_id=chain_id,
            client=client,
            stale_threshold_hours=stale_threshold_hours,
        )
    ).parsed
