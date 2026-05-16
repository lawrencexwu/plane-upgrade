"""Compare Economy vs Premium Economy upgrade economics for a Trip."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional

from .trip import Trip, TripMiles, resolve_trip_miles
from .upgrade_rules import load_chart


@dataclass
class ComparisonInput:
    trip: Trip
    economy_price: float
    premium_economy_price: float
    currency: str
    economy_family: str   # "Standard" | "Up"
    premium_family: str   # "Standard" | "Up"
    mile_value: float
    # Prices = TOTAL booking cost (all passengers, all legs).


@dataclass
class ComparisonResult:
    passengers: int
    currency: str
    economy_family: str
    premium_family: str
    economy: TripMiles
    premium: TripMiles
    economy_miles_per_person: int
    premium_miles_per_person: int
    economy_miles_total: int
    premium_miles_total: int
    miles_saved_per_person: int
    miles_saved_total: int
    economy_price: float
    premium_economy_price: float
    cash_upcharge: float
    implied_cost_per_saved_mile: Optional[float]
    mile_value: float
    recommendation: str
    reasoning: str
    blocked: bool          # True if chart could not resolve a leg
    block_notes: List[str]


def compare(inp: ComparisonInput, chart: Optional[dict] = None) -> ComparisonResult:
    if chart is None:
        chart = load_chart()

    eco = resolve_trip_miles(chart, inp.trip, "Economy", inp.economy_family)
    pre = resolve_trip_miles(chart, inp.trip, "Premium Economy",
                             inp.premium_family)

    saved_pp = eco.per_person_total - pre.per_person_total
    saved_total = eco.all_passengers_total - pre.all_passengers_total
    upcharge = inp.premium_economy_price - inp.economy_price

    blocked = eco.has_unresolved or pre.has_unresolved
    block_notes = sorted(set(eco.unresolved_notes + pre.unresolved_notes))

    implied: Optional[float] = None
    if not blocked and saved_total > 0:
        implied = upcharge / saved_total

    rec, reason = _recommend(inp, implied, upcharge, saved_total, blocked,
                             block_notes)

    return ComparisonResult(
        passengers=inp.trip.passengers,
        currency=inp.currency,
        economy_family=inp.economy_family,
        premium_family=inp.premium_family,
        economy=eco,
        premium=pre,
        economy_miles_per_person=eco.per_person_total,
        premium_miles_per_person=pre.per_person_total,
        economy_miles_total=eco.all_passengers_total,
        premium_miles_total=pre.all_passengers_total,
        miles_saved_per_person=saved_pp,
        miles_saved_total=saved_total,
        economy_price=inp.economy_price,
        premium_economy_price=inp.premium_economy_price,
        cash_upcharge=upcharge,
        implied_cost_per_saved_mile=implied,
        mile_value=inp.mile_value,
        recommendation=rec,
        reasoning=reason,
        blocked=blocked,
        block_notes=block_notes,
    )


def _recommend(inp, implied, upcharge, saved_total, blocked, block_notes):
    if blocked:
        return (
            "Cannot give a verdict - chart not verified",
            "One or more legs resolve to an unverified region pair, so the "
            "mileage math is incomplete. Confirm these with EVA and add them "
            "to config/eva_upgrade_chart.yaml: " + "; ".join(block_notes),
        )
    if saved_total <= 0:
        return ("Indeterminate",
                "Premium Economy does not save miles vs Economy here.")
    if upcharge <= 0:
        return ("BUY PREMIUM ECONOMY",
                "Premium Economy is cheaper than (or equal to) Economy AND "
                "saves miles. No reason to buy Economy.")
    if implied is None:
        return "Indeterminate", "Could not compute implied cost per saved mile."

    if implied <= inp.mile_value:
        return ("BUY PREMIUM ECONOMY",
                f"Implied cost per saved mile ({implied:.3f} {inp.currency}) is "
                f"at/below your mile valuation ({inp.mile_value}). Efficient "
                "conversion of cash into saved miles.")
    if implied <= inp.mile_value * 1.5:
        return ("BORDERLINE - leans Premium Economy",
                f"Implied cost per saved mile ({implied:.3f} {inp.currency}) is "
                f"moderately above your valuation ({inp.mile_value}). May still "
                "be worth it for the fallback cabin if the upgrade does not clear.")
    return ("BUY ECONOMY",
            f"Implied cost per saved mile ({implied:.3f} {inp.currency}) is well "
            f"above your valuation ({inp.mile_value}). Economy is more "
            "cash-efficient, but uses many more miles to upgrade.")
