import pytest

from src.upgrade_rules import (
    classify_fare_class,
    leg_upgrade_miles,
    load_chart,
)


@pytest.fixture(scope="module")
def chart():
    return load_chart()


@pytest.mark.parametrize("fc", ["Q", "H", "M"])
def test_tpe_ord_economy_standard_70000(chart, fc):
    info = classify_fare_class(chart, fc)
    assert info.upgradeable and info.cabin == "Economy"
    lm = leg_upgrade_miles(chart, "TPE", "ORD", "Economy", "Standard")
    assert lm.status == "ok" and lm.miles == 70000


@pytest.mark.parametrize("fc", ["L", "T"])
def test_tpe_ord_premium_economy_standard_40000(chart, fc):
    info = classify_fare_class(chart, fc)
    assert info.cabin == "Premium Economy" and info.fare_family == "Standard"
    lm = leg_upgrade_miles(chart, "TPE", "ORD", "Premium Economy", "Standard")
    assert lm.miles == 40000


def test_lax_tpe_economy_standard_60000(chart):
    lm = leg_upgrade_miles(chart, "LAX", "TPE", "Economy", "Standard")
    assert lm.status == "ok" and lm.miles == 60000


def test_lax_tpe_premium_economy_standard_35000(chart):
    lm = leg_upgrade_miles(chart, "LAX", "TPE", "Premium Economy", "Standard")
    assert lm.miles == 35000


def test_direction_is_symmetric(chart):
    assert (leg_upgrade_miles(chart, "ORD", "TPE", "Economy", "Standard").miles
            == leg_upgrade_miles(chart, "TPE", "ORD", "Economy",
                                 "Standard").miles)


def test_p_non_upgradeable(chart):
    assert classify_fare_class(chart, "P").upgradeable is False


@pytest.mark.parametrize("fc", ["A", "V", "W", "S"])
def test_avws_non_upgradeable(chart, fc):
    assert classify_fare_class(chart, fc).upgradeable is False


def test_unverified_region_pair_is_flagged_not_guessed(chart):
    lm = leg_upgrade_miles(chart, "TPE", "LHR", "Economy", "Standard")
    assert lm.status == "unverified"
    assert lm.miles is None


def test_unknown_airport_flagged(chart):
    lm = leg_upgrade_miles(chart, "TPE", "ZZZ", "Economy", "Standard")
    assert lm.status == "unknown_airport"
    assert lm.miles is None
