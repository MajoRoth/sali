import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.processing_timeline_response import ProcessingTimelineResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    params["bucket_minutes"] = bucket_minutes

    params["use_extracted_date"] = use_extracted_date

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/health/processing-timeline",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | ProcessingTimelineResponse | None:
    if response.status_code == 200:
        response_200 = ProcessingTimelineResponse.from_dict(response.json())

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
) -> Response[HTTPValidationError | ProcessingTimelineResponse]:
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
    use_extracted_date: bool | Unset = False,
) -> Response[HTTPValidationError | ProcessingTimelineResponse]:
    """Get Processing Timeline

     Get processing timeline for all unique extracted_from_site values.

    Returns the number of files processed per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, use extracted_date (supermarket publish date);
            if False, use created_at (processing time) Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProcessingTimelineResponse]
    """

    kwargs = _get_kwargs(
        start_time=start_time,
        end_time=end_time,
        bucket_minutes=bucket_minutes,
        use_extracted_date=use_extracted_date,
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
    use_extracted_date: bool | Unset = False,
) -> HTTPValidationError | ProcessingTimelineResponse | None:
    """Get Processing Timeline

     Get processing timeline for all unique extracted_from_site values.

    Returns the number of files processed per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, use extracted_date (supermarket publish date);
            if False, use created_at (processing time) Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProcessingTimelineResponse
    """

    return sync_detailed(
        client=client,
        start_time=start_time,
        end_time=end_time,
        bucket_minutes=bucket_minutes,
        use_extracted_date=use_extracted_date,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> Response[HTTPValidationError | ProcessingTimelineResponse]:
    """Get Processing Timeline

     Get processing timeline for all unique extracted_from_site values.

    Returns the number of files processed per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, use extracted_date (supermarket publish date);
            if False, use created_at (processing time) Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProcessingTimelineResponse]
    """

    kwargs = _get_kwargs(
        start_time=start_time,
        end_time=end_time,
        bucket_minutes=bucket_minutes,
        use_extracted_date=use_extracted_date,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> HTTPValidationError | ProcessingTimelineResponse | None:
    """Get Processing Timeline

     Get processing timeline for all unique extracted_from_site values.

    Returns the number of files processed per site per time bucket.
    Delegates per-site computation to /site-bucket-counts (shared cache).

    Args:
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, use extracted_date (supermarket publish date);
            if False, use created_at (processing time) Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProcessingTimelineResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            start_time=start_time,
            end_time=end_time,
            bucket_minutes=bucket_minutes,
            use_extracted_date=use_extracted_date,
        )
    ).parsed
