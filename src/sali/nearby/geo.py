"""Distance on the ground, so "nearby" means walkable rather than alphabetical.

The price database has no radius filter, so narrowing to what a shopper can
reach happens here, against the coordinates every store record carries.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000.0


def distance_meters(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> float:
    """Great-circle distance between two WGS84 (lat, lng) points, in meters."""
    lat1, lng1 = origin
    lat2, lng2 = destination
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    haversine = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * asin(sqrt(haversine))


def is_valid_coordinate(lat: float | None, lng: float | None) -> bool:
    """Whether a coordinate pair is usable.

    Store records routinely carry `0, 0` for "we do not know", which is a real
    point in the Gulf of Guinea and would otherwise place every unlocated branch
    at the same spot 4,000 km away.
    """
    if lat is None or lng is None:
        return False
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        return False
    return not (abs(lat) < 1e-6 and abs(lng) < 1e-6)


__all__ = ["EARTH_RADIUS_M", "distance_meters", "is_valid_coordinate"]
