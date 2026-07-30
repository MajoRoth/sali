import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.row_processing_timeline_response import RowProcessingTimelineResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    params["bucket_minutes"] = bucket_minutes

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/health/row-processing-timeline",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | RowProcessingTimelineResponse | None:
    if response.status_code == 200:
        response_200 = RowProcessingTimelineResponse.from_dict(response.json())

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
) -> Response[HTTPValidationError | RowProcessingTimelineResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
) -> Response[HTTPValidationError | RowProcessingTimelineResponse]:
    """Get Row Processing Timeline

     Get row processing timeline for all unique extracted_from_site values.

    Returns total rows loaded and published per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RowProcessingTimelineResponse]
    """

    kwargs = _get_kwargs(
        start_time=start_time,
        end_time=end_time,
        bucket_minutes=bucket_minutes,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
) -> HTTPValidationError | RowProcessingTimelineResponse | None:
    """Get Row Processing Timeline

     Get row processing timeline for all unique extracted_from_site values.

    Returns total rows loaded and published per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RowProcessingTimelineResponse
    """

    return sync_detailed(
        client=client,
        start_time=start_time,
        end_time=end_time,
        bucket_minutes=bucket_minutes,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
) -> Response[HTTPValidationError | RowProcessingTimelineResponse]:
    """Get Row Processing Timeline

     Get row processing timeline for all unique extracted_from_site values.

    Returns total rows loaded and published per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RowProcessingTimelineResponse]
    """

    kwargs = _get_kwargs(
        start_time=start_time,
        end_time=end_time,
        bucket_minutes=bucket_minutes,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
) -> HTTPValidationError | RowProcessingTimelineResponse | None:
    """Get Row Processing Timeline

     Get row processing timeline for all unique extracted_from_site values.

    Returns total rows loaded and published per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RowProcessingTimelineResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            start_time=start_time,
            end_time=end_time,
            bucket_minutes=bucket_minutes,
        )
    ).parsed
