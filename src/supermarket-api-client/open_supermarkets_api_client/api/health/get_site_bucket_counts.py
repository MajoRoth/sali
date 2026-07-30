import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.site_bucket_counts_response import SiteBucketCountsResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    site: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["site"] = site

    json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    params["bucket_minutes"] = bucket_minutes

    params["use_extracted_date"] = use_extracted_date

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/health/site-bucket-counts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | SiteBucketCountsResponse | None:
    if response.status_code == 200:
        response_200 = SiteBucketCountsResponse.from_dict(response.json())

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
) -> Response[HTTPValidationError | SiteBucketCountsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    site: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> Response[HTTPValidationError | SiteBucketCountsResponse]:
    """Get Site Bucket Counts

     Compute per-bucket file counts and row metrics for a single site.

    Cached for 60 seconds. Also called internally by /processing-timeline and /row-processing-timeline.

    Args:
        site (str): extracted_from_site value to query
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, file counts use extracted_date; row metrics
            always use created_at Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SiteBucketCountsResponse]
    """

    kwargs = _get_kwargs(
        site=site,
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
    site: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> HTTPValidationError | SiteBucketCountsResponse | None:
    """Get Site Bucket Counts

     Compute per-bucket file counts and row metrics for a single site.

    Cached for 60 seconds. Also called internally by /processing-timeline and /row-processing-timeline.

    Args:
        site (str): extracted_from_site value to query
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, file counts use extracted_date; row metrics
            always use created_at Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SiteBucketCountsResponse
    """

    return sync_detailed(
        client=client,
        site=site,
        start_time=start_time,
        end_time=end_time,
        bucket_minutes=bucket_minutes,
        use_extracted_date=use_extracted_date,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    site: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> Response[HTTPValidationError | SiteBucketCountsResponse]:
    """Get Site Bucket Counts

     Compute per-bucket file counts and row metrics for a single site.

    Cached for 60 seconds. Also called internally by /processing-timeline and /row-processing-timeline.

    Args:
        site (str): extracted_from_site value to query
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, file counts use extracted_date; row metrics
            always use created_at Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SiteBucketCountsResponse]
    """

    kwargs = _get_kwargs(
        site=site,
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
    site: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    bucket_minutes: int,
    use_extracted_date: bool | Unset = False,
) -> HTTPValidationError | SiteBucketCountsResponse | None:
    """Get Site Bucket Counts

     Compute per-bucket file counts and row metrics for a single site.

    Cached for 60 seconds. Also called internally by /processing-timeline and /row-processing-timeline.

    Args:
        site (str): extracted_from_site value to query
        start_time (datetime.datetime): Start time of the range (ISO format)
        end_time (datetime.datetime): End time of the range (ISO format)
        bucket_minutes (int): Time bucket size in minutes
        use_extracted_date (bool | Unset): If True, file counts use extracted_date; row metrics
            always use created_at Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SiteBucketCountsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            site=site,
            start_time=start_time,
            end_time=end_time,
            bucket_minutes=bucket_minutes,
            use_extracted_date=use_extracted_date,
        )
    ).parsed
