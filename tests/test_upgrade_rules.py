import pytest

from src.upgrade_rules import (
    check_eligibility,
    load_chart,
    miles_for_bucket,
    total_upgrade_miles,
)


@pytest.fixture(scope="module")
def chart():
    return load_chart()


# ------ Mileage by route + bucket ------

@pytest.mark.parametrize("fare_class", ["Q", "H", "M"])
def test_tpe_ord_economy_standard_is_70000(chart, fare_class):
    e = check_eligibility(chart, "TPE-ORD", fare_class)
    assert e.upgradeable is True
    assert e.cabin == "Economy"
    assert e.fare_family == "Standard"
    assert e.miles_to_business == 70000


@pytest.mark.parametrize("fare_class", ["L", "T"])
def test_tpe_ord_premium_economy_standard_is_40000(chart, fare_class):
    e = check_eligibility(chart, "TPE-ORD", fare_class)
    assert e.upgradeable is True
    assert e.cabin == "Premium Economy"
    assert e.fare_family == "Standard"
    assert e.miles_to_business == 40000


@pytest.mark.parametrize("fare_class", ["Q", "H", "M"])
def test_lax_tpe_economy_standard_is_60000(chart, fare_class):
    e = check_eligibility(chart, "LAX-TPE", fare_class)
    assert e.upgradeable is True
    assert e.miles_to_business == 60000


@pytest.mark.parametrize("fare_class", ["L", "T"])
def test_lax_tpe_premium_economy_standard_is_35000(chart, fare_class):
    e = check_eligibility(chart, "LAX-TPE", fare_class)
    assert e.upgradeable is True
    assert e.miles_to_business == 35000


# ------ Non-upgradeable fare classes ------

def test_p_is_non_upgradeable(chart):
    for route in ("TPE-ORD", "LAX-TPE"):
        e = check_eligibility(chart, route, "P")
        assert e.upgradeable is False
        assert "NON-UPGRADEABLE" in e.reason


@pytest.mark.parametrize("fare_class", ["A", "V", "W", "S"])
def test_avws_are_non_upgradeable(chart, fare_class):
    for route in ("TPE-ORD", "LAX-TPE"):
        e = check_eligibility(chart, route, fare_class)
        assert e.upgradeable is False


# ------ Totals across both legs / 2 pax ------

def test_two_pax_economy_standard_both_legs_is_260000(chart):
    routes = ["TPE-ORD", "LAX-TPE"]
    per_person, total = total_upgrade_miles(chart, routes, "Economy", "Standard",
                                            passengers=2)
    assert per_person == 130_000
    assert total == 260_000


def test_two_pax_premium_economy_standard_both_legs_is_150000(chart):
    routes = ["TPE-ORD", "LAX-TPE"]
    per_person, total = total_upgrade_miles(chart, routes, "Premium Economy",
                                            "Standard", passengers=2)
    assert per_person == 75_000
    assert total == 150_000


# ------ Up family sanity ------

def test_up_family_lookup_lax_tpe(chart):
    assert miles_for_bucket(chart, "LAX-TPE", "Economy", "Up") == 50_000
    assert miles_for_bucket(chart, "LAX-TPE", "Premium Economy", "Up") == 31_500


def test_up_family_lookup_tpe_ord(chart):
    assert miles_for_bucket(chart, "TPE-ORD", "Economy", "Up") == 58_500
    assert miles_for_bucket(chart, "TPE-ORD", "Premium Economy", "Up") == 36_000


def test_unknown_route_raises(chart):
    with pytest.raises(KeyError):
        miles_for_bucket(chart, "JFK-LHR", "Economy", "Standard")
