from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.pipeline_health_response import PipelineHealthResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    stale_threshold_hours: int | Unset = 24,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["stale_threshold_hours"] = stale_threshold_hours

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/health/pipeline",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | PipelineHealthResponse | None:
    if response.status_code == 200:
        response_200 = PipelineHealthResponse.from_dict(response.json())

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
) -> Response[HTTPValidationError | PipelineHealthResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    stale_threshold_hours: int | Unset = 24,
) -> Response[HTTPValidationError | PipelineHealthResponse]:
    """Get Pipeline Health

     Check pipeline health and data freshness.

    Returns information about:
    - Last data update times per chain
    - Number of data sources processed
    - Data staleness indicators
    - Overall pipeline health status

    Per-chain results cached 30 min via FastAPICache in compute_chain_data_status.

    Args:
        stale_threshold_hours (int | Unset): Hours before data is considered stale Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PipelineHealthResponse]
    """

    kwargs = _get_kwargs(
        stale_threshold_hours=stale_threshold_hours,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    stale_threshold_hours: int | Unset = 24,
) -> HTTPValidationError | PipelineHealthResponse | None:
    """Get Pipeline Health

     Check pipeline health and data freshness.

    Returns information about:
    - Last data update times per chain
    - Number of data sources processed
    - Data staleness indicators
    - Overall pipeline health status

    Per-chain results cached 30 min via FastAPICache in compute_chain_data_status.

    Args:
        stale_threshold_hours (int | Unset): Hours before data is considered stale Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PipelineHealthResponse
    """

    return sync_detailed(
        client=client,
        stale_threshold_hours=stale_threshold_hours,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    stale_threshold_hours: int | Unset = 24,
) -> Response[HTTPValidationError | PipelineHealthResponse]:
    """Get Pipeline Health

     Check pipeline health and data freshness.

    Returns information about:
    - Last data update times per chain
    - Number of data sources processed
    - Data staleness indicators
    - Overall pipeline health status

    Per-chain results cached 30 min via FastAPICache in compute_chain_data_status.

    Args:
        stale_threshold_hours (int | Unset): Hours before data is considered stale Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PipelineHealthResponse]
    """

    kwargs = _get_kwargs(
        stale_threshold_hours=stale_threshold_hours,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    stale_threshold_hours: int | Unset = 24,
) -> HTTPValidationError | PipelineHealthResponse | None:
    """Get Pipeline Health

     Check pipeline health and data freshness.

    Returns information about:
    - Last data update times per chain
    - Number of data sources processed
    - Data staleness indicators
    - Overall pipeline health status

    Per-chain results cached 30 min via FastAPICache in compute_chain_data_status.

    Args:
        stale_threshold_hours (int | Unset): Hours before data is considered stale Default: 24.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PipelineHealthResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            stale_threshold_hours=stale_threshold_hours,
        )
    ).parsed
