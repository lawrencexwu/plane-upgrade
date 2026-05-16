"""Region-based EVA upgrade chart: airport -> region -> upgrade miles.

Only region pairs marked verified in the YAML return mileage. Unverified or
absent pairs return status="unverified" so the tool never guesses on a money
decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

CHART_PATH = Path(__file__).resolve().parent.parent / "config" / "eva_upgrade_chart.yaml"
SETTINGS_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"

# (cabin, family) -> award-entry key
BUCKET_KEYS = {
    ("economy", "standard"): "economy_standard",
    ("economy", "up"): "economy_up",
    ("premium economy", "standard"): "premium_economy_standard",
    ("premium economy", "up"): "premium_economy_up",
}


def load_chart(path: Path = CHART_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_settings(path: Path = SETTINGS_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


@dataclass
class FareClassInfo:
    fare_class: str
    upgradeable: bool
    cabin: Optional[str]       # "Economy" | "Premium Economy"
    fare_family: Optional[str]  # "Standard" | "Up"
    reason: str


@dataclass
class LegMiles:
    origin: str
    destination: str
    origin_region: Optional[str]
    destination_region: Optional[str]
    status: str   # "ok" | "unverified" | "unknown_airport"
    miles: Optional[int]
    cabin: str
    fare_family: str
    note: str


def classify_fare_class(chart: dict, fare_class: str) -> FareClassInfo:
    fc = (fare_class or "").strip().upper()
    fcfg = chart["fare_classes"]

    non = [c.upper() for c in fcfg.get("non_upgradeable", [])]
    if fc in non:
        return FareClassInfo(
            fc, False, None, None,
            f"Fare class {fc} is NON-UPGRADEABLE (Discount/Basic). "
            "DO NOT BUY FOR UPGRADE.",
        )

    for cabin_key, cabin_label in (("economy", "Economy"),
                                   ("premium_economy", "Premium Economy")):
        for fam_key, fam_label in (("standard", "Standard"), ("up", "Up")):
            classes = [c.upper() for c in fcfg.get(cabin_key, {}).get(fam_key, [])]
            if fc in classes:
                return FareClassInfo(
                    fc, True, cabin_label, fam_label,
                    f"Fare class {fc} = {cabin_label} {fam_label}.",
                )

    return FareClassInfo(
        fc, False, None, None,
        f"Fare class {fc} not found in chart. Treat as unknown / not "
        "upgradeable until confirmed with EVA.",
    )


def airport_region(chart: dict, airport: str) -> Optional[str]:
    return chart.get("airports", {}).get(airport.strip().upper())


def _award_key(region_a: str, region_b: str) -> str:
    return "|".join(sorted([region_a, region_b]))


def _bucket_key(cabin: str, fare_family: str) -> str:
    key = (cabin.strip().lower(), fare_family.strip().lower())
    if key not in BUCKET_KEYS:
        raise ValueError(f"Unknown cabin/family: {cabin!r}/{fare_family!r}")
    return BUCKET_KEYS[key]


def leg_upgrade_miles(
    chart: dict,
    origin: str,
    destination: str,
    cabin: str,
    fare_family: str,
) -> LegMiles:
    """Resolve upgrade miles for one leg. Never guesses unverified pairs."""
    origin = origin.strip().upper()
    destination = destination.strip().upper()
    ro = airport_region(chart, origin)
    rd = airport_region(chart, destination)

    if ro is None or rd is None:
        missing = ", ".join(
            a for a, r in ((origin, ro), (destination, rd)) if r is None
        )
        return LegMiles(
            origin, destination, ro, rd, "unknown_airport", None,
            cabin, fare_family,
            f"Airport(s) not in region map: {missing}. Add to "
            "config/eva_upgrade_chart.yaml.",
        )

    award = chart.get("upgrade_award", {}).get(_award_key(ro, rd))
    if not award or not award.get("verified"):
        return LegMiles(
            origin, destination, ro, rd, "unverified", None,
            cabin, fare_family,
            f"Upgrade chart value for {ro} <-> {rd} is NOT verified. "
            "Confirm with EVA and add it to the YAML before trusting a verdict.",
        )

    bk = _bucket_key(cabin, fare_family)
    miles = award.get(bk)
    if miles is None:
        return LegMiles(
            origin, destination, ro, rd, "unverified", None,
            cabin, fare_family,
            f"No {bk} value for {ro} <-> {rd} in the chart.",
        )

    return LegMiles(
        origin, destination, ro, rd, "ok", int(miles),
        cabin, fare_family,
        f"{cabin} {fare_family}: {int(miles):,} miles/person, {origin}->"
        f"{destination} ({ro} <-> {rd}).",
    )
