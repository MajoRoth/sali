"""Stitching two datasets into one directory: placement, aliases, and honesty."""

from sali.nearby.stores import _city_aliases, _place_name


def test_junk_city_values_are_not_shown_as_places() -> None:
    """A third of upstream rows carry a float or a postcode in the city column,
    and "טיב טעם, 5000.0" reads as a real address if it is passed through."""
    assert _place_name("תל אביב") == "תל אביב"
    assert _place_name("nan") is None
    assert _place_name("5000.0") is None
    assert _place_name("8300") is None
    assert _place_name("") is None
    assert _place_name(None) is None


def test_a_city_is_matchable_by_the_names_people_actually_write() -> None:
    """The directory says `תל אביב - יפו`; a shop name says `תל אביב`. Testing
    whether the long form appears inside the short one finds nothing."""
    aliases = _city_aliases({"תל אביב - יפו": (32.07, 34.78)})

    assert aliases["תל אביב - יפו"] == "תל אביב - יפו"
    assert aliases["תל אביב"] == "תל אביב - יפו"
    assert aliases["יפו"] == "תל אביב - יפו"


def test_an_alias_two_cities_share_is_dropped_rather_than_guessed() -> None:
    """Placing a shop in the wrong city is worse than not placing it."""
    aliases = _city_aliases(
        {"כפר סבא - מרכז": (32.17, 34.90), "הוד השרון - מרכז": (32.15, 34.88)}
    )

    # "מרכז" belongs to both, so it identifies neither.
    assert "מרכז" not in aliases
    assert aliases["כפר סבא"] == "כפר סבא - מרכז"
    assert aliases["הוד השרון"] == "הוד השרון - מרכז"


def test_very_short_fragments_are_not_treated_as_cities() -> None:
    """Two-letter fragments match half the shop names in the country."""
    aliases = _city_aliases({"א - בית שמש": (31.75, 34.98)})

    assert "א" not in aliases
    assert aliases["בית שמש"] == "א - בית שמש"
