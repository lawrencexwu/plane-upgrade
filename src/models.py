"""Dataclasses for fare quotes, flight records, and ExpertFlyer checks."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class FareQuote:
    route: str
    cabin: str
    fare_family: str
    fare_class: Optional[str]
    price: float
    taxes_fees: float = 0.0
    currency: str = "TWD"
    passengers: int = 2
    flight_number: Optional[str] = None
    date: Optional[str] = None
    source: str = "manual"
    notes: str = ""
    timestamp: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FlightRecord:
    flight_number: str
    aircraft_type: str = ""
    scheduled_departure: str = ""
    scheduled_arrival: str = ""
    cabin_layout_notes: str = ""
    source: str = "manual"
    screenshot_path: str = ""
    aircraft_change_warning: str = (
        "Aircraft type and seat map can change before departure."
    )
    timestamp: str = field(default_factory=_utc_now)


@dataclass
class ExpertFlyerCheck:
    route: str
    date: str
    airline: str
    flight_number: str
    aircraft: str = ""
    scheduled_departure: str = ""
    scheduled_arrival: str = ""
    business_seatmap_notes: str = ""
    premium_seatmap_notes: str = ""
    economy_seatmap_notes: str = ""
    seat_count_observations: str = ""
    fare_bucket_notes: str = ""
    business_availability_clue: str = ""
    premium_availability_clue: str = ""
    confidence_clue: str = "unknown"  # strong | weak | none | unknown
    notes: str = ""
    screenshot_path: str = ""
    source: str = "ExpertFlyer"
    checked_at: str = field(default_factory=_utc_now)
    disclaimer: str = (
        "Third-party clue only. NOT official EVA upgrade confirmation. "
        "Seat map availability != upgrade availability. "
        "Paid business inventory != mileage upgrade inventory."
    )

    def to_dict(self) -> dict:
        return asdict(self)
