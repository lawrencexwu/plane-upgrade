"""Load EVA upgrade chart YAML and answer eligibility / mileage questions."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

CHART_PATH = Path(__file__).resolve().parent.parent / "config" / "eva_upgrade_chart.yaml"
SETTINGS_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"

# Cabin/family canonical bucket keys used in YAML
BUCKET_KEYS = {
    ("economy", "standard"): "economy_standard",
    ("economy", "up"): "economy_up",
    ("premium economy", "standard"): "premium_economy_standard",
    ("premium economy", "up"): "premium_economy_up",
}


@dataclass
class FareEligibility:
    route: str
    fare_class: str
    upgradeable: bool
    cabin: Optional[str]
    fare_family: Optional[str]
    miles_to_business: Optional[int]
    reason: str


def load_chart(path: Path = CHART_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_settings(path: Path = SETTINGS_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _route_block(chart: dict, route: str) -> dict:
    routes = chart.get("routes", {})
    if route not in routes:
        raise KeyError(
            f"Route '{route}' not found in chart. Known routes: {list(routes)}"
        )
    return routes[route]


def _bucket_key(cabin: str, fare_family: str) -> str:
    key = (cabin.strip().lower(), fare_family.strip().lower())
    if key not in BUCKET_KEYS:
        raise ValueError(
            f"Unknown cabin/family combo: cabin={cabin!r}, family={fare_family!r}. "
            f"Supported: {list(BUCKET_KEYS)}"
        )
    return BUCKET_KEYS[key]


def check_eligibility(chart: dict, route: str, fare_class: str) -> FareEligibility:
    """Return upgrade eligibility + mileage cost for the given route and fare class."""
    fare_class = fare_class.strip().upper()
    block = _route_block(chart, route)
    upgrade = block["upgrade_to_business"]

    non = upgrade.get("non_upgradeable", {}).get("fare_classes", [])
    if fare_class in [c.upper() for c in non]:
        return FareEligibility(
            route=route,
            fare_class=fare_class,
            upgradeable=False,
            cabin=None,
            fare_family=None,
            miles_to_business=None,
            reason=(
                f"Fare class {fare_class} is NON-UPGRADEABLE on {route} "
                f"(Discount/Basic). DO NOT BUY FOR UPGRADE."
            ),
        )

    for key, group in upgrade.items():
        if key == "non_upgradeable":
            continue
        classes = [c.upper() for c in group.get("fare_classes", [])]
        if fare_class in classes:
            return FareEligibility(
                route=route,
                fare_class=fare_class,
                upgradeable=True,
                cabin=group["cabin"],
                fare_family=group["fare_family"],
                miles_to_business=int(group["miles"]),
                reason=(
                    f"Fare class {fare_class} = {group['cabin']} "
                    f"{group['fare_family']}: upgradeable to Business/Royal "
                    f"Laurel for {group['miles']:,} miles per person."
                ),
            )

    return FareEligibility(
        route=route,
        fare_class=fare_class,
        upgradeable=False,
        cabin=None,
        fare_family=None,
        miles_to_business=None,
        reason=(
            f"Fare class {fare_class} not listed in upgrade chart for {route}. "
            f"Treat as unknown / not upgradeable until verified with EVA."
        ),
    )


def miles_for_bucket(chart: dict, route: str, cabin: str, fare_family: str) -> int:
    """Look up upgrade miles by cabin + fare family (e.g. Economy / Standard)."""
    block = _route_block(chart, route)
    key = _bucket_key(cabin, fare_family)
    upgrade = block["upgrade_to_business"]
    if key not in upgrade:
        raise KeyError(f"Bucket {key} not configured for route {route}")
    return int(upgrade[key]["miles"])


def total_upgrade_miles(
    chart: dict,
    routes: list,
    cabin: str,
    fare_family: str,
    passengers: int,
):
    """Return (miles_per_person_total, miles_all_passengers_total)."""
    per_person = sum(miles_for_bucket(chart, r, cabin, fare_family) for r in routes)
    return per_person, per_person * passengers
