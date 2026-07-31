from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_stores_response import GetStoresResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    lat: float,
    lng: float,
    radius: float,
    chain_id: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["lat"] = lat

    params["lng"] = lng

    params["radius"] = radius

    json_chain_id: None | str | Unset
    if isinstance(chain_id, Unset):
        json_chain_id = UNSET
    else:
        json_chain_id = chain_id
    params["chain_id"] = json_chain_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/stores/nearby",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> GetStoresResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = GetStoresResponse.from_dict(response.json())

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
) -> Response[GetStoresResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    lat: float,
    lng: float,
    radius: float,
    chain_id: None | str | Unset = UNSET,
) -> Response[GetStoresResponse | HTTPValidationError]:
    """Get Stores Nearby

     Get all stores within a given radius (in meters) of a location.

    Args:
        lat (float): Latitude of the center point
        lng (float): Longitude of the center point
        radius (float): Radius in meters to search within
        chain_id (None | str | Unset): Filter by chainId or chainCode

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetStoresResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        lat=lat,
        lng=lng,
        radius=radius,
        chain_id=chain_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    lat: float,
    lng: float,
    radius: float,
    chain_id: None | str | Unset = UNSET,
) -> GetStoresResponse | HTTPValidationError | None:
    """Get Stores Nearby

     Get all stores within a given radius (in meters) of a location.

    Args:
        lat (float): Latitude of the center point
        lng (float): Longitude of the center point
        radius (float): Radius in meters to search within
        chain_id (None | str | Unset): Filter by chainId or chainCode

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetStoresResponse | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        lat=lat,
        lng=lng,
        radius=radius,
        chain_id=chain_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    lat: float,
    lng: float,
    radius: float,
    chain_id: None | str | Unset = UNSET,
) -> Response[GetStoresResponse | HTTPValidationError]:
    """Get Stores Nearby

     Get all stores within a given radius (in meters) of a location.

    Args:
        lat (float): Latitude of the center point
        lng (float): Longitude of the center point
        radius (float): Radius in meters to search within
        chain_id (None | str | Unset): Filter by chainId or chainCode

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetStoresResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        lat=lat,
        lng=lng,
        radius=radius,
        chain_id=chain_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    lat: float,
    lng: float,
    radius: float,
    chain_id: None | str | Unset = UNSET,
) -> GetStoresResponse | HTTPValidationError | None:
    """Get Stores Nearby

     Get all stores within a given radius (in meters) of a location.

    Args:
        lat (float): Latitude of the center point
        lng (float): Longitude of the center point
        radius (float): Radius in meters to search within
        chain_id (None | str | Unset): Filter by chainId or chainCode

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetStoresResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            lat=lat,
            lng=lng,
            radius=radius,
            chain_id=chain_id,
        )
    ).parsed
