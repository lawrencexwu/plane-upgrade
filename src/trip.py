"""Trip model: one-way / round-trip / multi-city, made of legs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .upgrade_rules import LegMiles, leg_upgrade_miles


@dataclass
class Leg:
    origin: str
    destination: str
    date: Optional[str] = None
    flight_number: Optional[str] = None

    def code(self) -> str:
        return f"{self.origin.upper()}-{self.destination.upper()}"


@dataclass
class Trip:
    trip_type: str  # "one_way" | "round_trip" | "multi_city"
    legs: List[Leg] = field(default_factory=list)
    passengers: int = 2

    @staticmethod
    def one_way(origin, destination, date=None, flight=None, passengers=2) -> "Trip":
        return Trip("one_way",
                    [Leg(origin, destination, date, flight)],
                    passengers)

    @staticmethod
    def round_trip(origin, destination, out_date=None, ret_date=None,
                   passengers=2) -> "Trip":
        return Trip("round_trip", [
            Leg(origin, destination, out_date),
            Leg(destination, origin, ret_date),
        ], passengers)

    @staticmethod
    def multi_city(legs: List[Leg], passengers=2) -> "Trip":
        return Trip("multi_city", list(legs), passengers)


@dataclass
class TripMiles:
    legs: List[LegMiles]
    cabin: str
    fare_family: str
    passengers: int
    per_person_total: int           # sum of resolved (ok) legs
    all_passengers_total: int
    has_unresolved: bool            # any leg not "ok"
    unresolved_notes: List[str]


def resolve_trip_miles(chart: dict, trip: Trip, cabin: str,
                       fare_family: str) -> TripMiles:
    leg_results: List[LegMiles] = []
    per_person = 0
    unresolved = []
    for leg in trip.legs:
        lm = leg_upgrade_miles(chart, leg.origin, leg.destination,
                               cabin, fare_family)
        leg_results.append(lm)
        if lm.status == "ok" and lm.miles is not None:
            per_person += lm.miles
        else:
            unresolved.append(f"{leg.code()}: {lm.note}")
    return TripMiles(
        legs=leg_results,
        cabin=cabin,
        fare_family=fare_family,
        passengers=trip.passengers,
        per_person_total=per_person,
        all_passengers_total=per_person * trip.passengers,
        has_unresolved=bool(unresolved),
        unresolved_notes=unresolved,
    )
