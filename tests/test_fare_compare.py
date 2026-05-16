import pytest

from src.fare_compare import ComparisonInput, compare
from src.trip import Leg, Trip


def _trip(passengers=2):
    return Trip("multi_city", [Leg("TPE", "ORD"), Leg("LAX", "TPE")],
                passengers)


def _inp(**kw):
    base = dict(
        trip=_trip(),
        economy_price=110_000.0,
        premium_economy_price=160_000.0,
        currency="TWD",
        economy_family="Standard",
        premium_family="Standard",
        mile_value=0.8,
    )
    base.update(kw)
    return ComparisonInput(**base)


def test_two_pax_economy_standard_both_legs_260000():
    r = compare(_inp())
    assert r.economy_miles_per_person == 130_000
    assert r.economy_miles_total == 260_000


def test_two_pax_premium_economy_standard_150000():
    r = compare(_inp())
    assert r.premium_miles_per_person == 75_000
    assert r.premium_miles_total == 150_000


def test_standard_premium_saves_110000_for_2_pax():
    r = compare(_inp())
    assert r.miles_saved_total == 110_000
    assert r.miles_saved_per_person == 55_000


def test_implied_cost_per_saved_mile_correct():
    r = compare(_inp(economy_price=100_000, premium_economy_price=210_000))
    assert r.cash_upcharge == pytest.approx(110_000)
    assert r.implied_cost_per_saved_mile == pytest.approx(1.0)


def test_recommend_premium_when_below_value():
    r = compare(_inp(economy_price=100_000, premium_economy_price=155_000,
                      mile_value=0.8))
    assert "PREMIUM ECONOMY" in r.recommendation


def test_recommend_borderline_when_moderately_above():
    r = compare(_inp(economy_price=100_000, premium_economy_price=210_000,
                      mile_value=0.8))
    assert "BORDERLINE" in r.recommendation


def test_recommend_economy_when_far_above():
    r = compare(_inp(economy_price=100_000, premium_economy_price=320_000,
                      mile_value=0.8))
    assert r.recommendation == "BUY ECONOMY"


def test_up_family_saves_82000_for_2_pax():
    r = compare(_inp(economy_family="Up", premium_family="Up"))
    assert r.economy_miles_total == 217_000
    assert r.premium_miles_total == 135_000
    assert r.miles_saved_total == 82_000


def test_unverified_leg_blocks_verdict():
    trip = Trip("round_trip", [Leg("TPE", "LHR"), Leg("LHR", "TPE")], 2)
    r = compare(_inp(trip=trip))
    assert r.blocked is True
    assert "Cannot give a verdict" in r.recommendation
