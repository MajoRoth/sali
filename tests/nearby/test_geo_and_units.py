"""Distance, coordinate sanity, and unit folding."""

import pytest

from sali.nearby.geo import distance_meters, is_valid_coordinate
from sali.nearby.units import normalize_unit

TEL_AVIV = (32.0809, 34.7806)
RAMAT_GAN = (32.0684, 34.8248)


def test_distance_between_known_points_is_right_to_the_hundred_meters() -> None:
    # Tel Aviv centre to Ramat Gan is about 4.3 km on the ground.
    assert distance_meters(TEL_AVIV, RAMAT_GAN) == pytest.approx(4300, abs=200)


def test_distance_to_self_is_zero() -> None:
    assert distance_meters(TEL_AVIV, TEL_AVIV) == 0.0


def test_distance_is_symmetric() -> None:
    assert distance_meters(TEL_AVIV, RAMAT_GAN) == pytest.approx(
        distance_meters(RAMAT_GAN, TEL_AVIV)
    )


def test_null_island_is_not_a_valid_coordinate() -> None:
    """`0, 0` is the price database's way of saying it does not know.

    Treated as real it would place every unlocated branch on one spot in the
    Gulf of Guinea, and each would look like the nearest shop to nobody.
    """
    assert not is_valid_coordinate(0.0, 0.0)
    assert not is_valid_coordinate(None, None)
    assert not is_valid_coordinate(32.0, None)


def test_out_of_range_coordinates_are_rejected() -> None:
    assert not is_valid_coordinate(91.0, 34.0)
    assert not is_valid_coordinate(32.0, 181.0)


def test_real_coordinates_are_accepted() -> None:
    assert is_valid_coordinate(*TEL_AVIV)


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("kg", "kg"),
        ("KG", "kg"),
        ("Kg.", "kg"),
        ('ק"ג', "kg"),
        ("קילו", "kg"),
        ("גרם", "g"),
        ("ליטר", "l"),
        ('מ"ל', "ml"),
        ("unit", "unit"),
        ("יחידה", "unit"),
        # Anything unrecognised is a countable thing, which is what an
        # unlabelled receipt line means.
        ("", "unit"),
        (None, "unit"),
        ("שקית", "unit"),
    ],
)
def test_units_fold_onto_the_contract_vocabulary(printed, expected) -> None:
    assert normalize_unit(printed) == expected
