import pytest

from src.fare_compare import ComparisonInput, compare


def _inp(**overrides):
    base = dict(
        routes=["TPE-ORD", "LAX-TPE"],
        passengers=2,
        economy_price=110_000.0,   # booking total
        premium_economy_price=160_000.0,
        currency="TWD",
        economy_family="Standard",
        premium_family="Standard",
        mile_value=0.8,
    )
    base.update(overrides)
    return ComparisonInput(**base)


def test_standard_premium_saves_110000_miles_for_2_pax():
    r = compare(_inp())
    assert r.economy_miles_total == 260_000
    assert r.premium_miles_total == 150_000
    assert r.miles_saved_total == 110_000
    assert r.miles_saved_per_person == 55_000


def test_implied_cost_per_saved_mile_computed_correctly():
    r = compare(_inp(economy_price=100_000, premium_economy_price=210_000))
    # upcharge 110,000 TWD / 110,000 miles saved = 1.0 TWD per mile
    assert r.cash_upcharge == pytest.approx(110_000)
    assert r.miles_saved_total == 110_000
    assert r.implied_cost_per_saved_mile == pytest.approx(1.0)


def test_recommendation_premium_when_implied_below_mile_value():
    # upcharge 55,000 / 110,000 miles = 0.5 TWD per mile, valuation 0.8
    r = compare(_inp(economy_price=100_000, premium_economy_price=155_000,
                     mile_value=0.8))
    assert r.recommendation == "Premium Economy"
    assert r.implied_cost_per_saved_mile == pytest.approx(0.5)


def test_recommendation_borderline_when_moderately_above():
    # upcharge 110,000 / 110,000 = 1.0; valuation 0.8 -> within 1.5x
    r = compare(_inp(economy_price=100_000, premium_economy_price=210_000,
                     mile_value=0.8))
    assert "Borderline" in r.recommendation


def test_recommendation_economy_when_far_above_valuation():
    # upcharge 220,000 / 110,000 = 2.0; valuation 0.8 -> >> 1.5x
    r = compare(_inp(economy_price=100_000, premium_economy_price=320_000,
                     mile_value=0.8))
    assert r.recommendation == "Economy"


def test_up_family_saves_82000_miles_for_2_pax():
    r = compare(_inp(economy_family="Up", premium_family="Up"))
    # per person 108,500 vs 67,500 -> saves 41,000; *2 = 82,000
    assert r.economy_miles_total == 217_000
    assert r.premium_miles_total == 135_000
    assert r.miles_saved_total == 82_000
