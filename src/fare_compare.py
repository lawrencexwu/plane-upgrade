"""Compare Economy vs Premium Economy upgrade economics."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional

from .upgrade_rules import load_chart, total_upgrade_miles


@dataclass
class ComparisonInput:
    routes: List[str]
    passengers: int
    economy_price: float
    premium_economy_price: float
    currency: str
    economy_family: str  # "Standard" | "Up"
    premium_family: str  # "Standard" | "Up"
    mile_value: float    # value of one EVA mile in the same currency as prices
    # Price interpretation: TOTAL trip cost for the whole booking
    # (all passengers, all legs). The CLI is explicit about this.


@dataclass
class ComparisonResult:
    routes: List[str]
    passengers: int
    currency: str
    economy_family: str
    premium_family: str
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

    def to_dict(self) -> dict:
        return asdict(self)


def compare(inp: ComparisonInput, chart: Optional[dict] = None) -> ComparisonResult:
    if chart is None:
        chart = load_chart()

    eco_pp, eco_total = total_upgrade_miles(
        chart, inp.routes, "Economy", inp.economy_family, inp.passengers
    )
    pre_pp, pre_total = total_upgrade_miles(
        chart, inp.routes, "Premium Economy", inp.premium_family, inp.passengers
    )

    saved_pp = eco_pp - pre_pp
    saved_total = eco_total - pre_total
    upcharge = inp.premium_economy_price - inp.economy_price

    implied: Optional[float] = None
    if saved_total > 0:
        implied = upcharge / saved_total

    rec, reason = _recommend(inp, implied, upcharge, saved_total)

    return ComparisonResult(
        routes=inp.routes,
        passengers=inp.passengers,
        currency=inp.currency,
        economy_family=inp.economy_family,
        premium_family=inp.premium_family,
        economy_miles_per_person=eco_pp,
        premium_miles_per_person=pre_pp,
        economy_miles_total=eco_total,
        premium_miles_total=pre_total,
        miles_saved_per_person=saved_pp,
        miles_saved_total=saved_total,
        economy_price=inp.economy_price,
        premium_economy_price=inp.premium_economy_price,
        cash_upcharge=upcharge,
        implied_cost_per_saved_mile=implied,
        mile_value=inp.mile_value,
        recommendation=rec,
        reasoning=reason,
    )


def _recommend(inp, implied, upcharge, saved_total):
    if saved_total <= 0:
        return (
            "Indeterminate",
            "Premium Economy does not save miles vs Economy in this scenario.",
        )
    if upcharge <= 0:
        return (
            "Premium Economy",
            "Premium Economy is cheaper than (or equal to) Economy AND saves miles. "
            "No reason to buy Economy.",
        )
    if implied is None:
        return "Indeterminate", "Could not compute implied cost per saved mile."

    if implied <= inp.mile_value:
        return (
            "Premium Economy",
            f"Implied cost per saved mile ({implied:.3f} {inp.currency}) is at or "
            f"below your mile valuation ({inp.mile_value} {inp.currency}). "
            "Buying Premium Economy converts cash into miles efficiently.",
        )
    if implied <= inp.mile_value * 1.5:
        return (
            "Borderline — Premium Economy may still be worth it",
            f"Implied cost per saved mile ({implied:.3f} {inp.currency}) is "
            f"moderately above your mile valuation ({inp.mile_value} "
            f"{inp.currency}). Premium Economy may still be worth it for the "
            "fallback cabin comfort if the upgrade does not clear.",
        )
    return (
        "Economy",
        f"Implied cost per saved mile ({implied:.3f} {inp.currency}) is well "
        f"above your mile valuation ({inp.mile_value} {inp.currency}). Economy "
        "is more cash-efficient, but it uses many more miles to upgrade.",
    )
