"""Upgrade confidence scoring.

ExpertFlyer / seat-map data can never produce High and is always labeled
"NOT official EVA upgrade confirmation".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .upgrade_rules import FareClassInfo


@dataclass
class ConfidenceAssessment:
    level: str  # "High" | "Medium" | "Low" | "Do Not Buy"
    reasoning: str
    is_official: bool


def assess(
    fare: FareClassInfo,
    official_confirmed: bool = False,
    official_waitlist: bool = False,
    expertflyer_clue: Optional[str] = None,  # strong|weak|seatmap_only|None
    seatmap_only: bool = False,
) -> ConfidenceAssessment:
    if not fare.upgradeable:
        return ConfidenceAssessment(
            "Do Not Buy",
            f"Fare class {fare.fare_class} is NON-UPGRADEABLE. "
            "DO NOT BUY FOR UPGRADE.",
            False,
        )
    if official_confirmed:
        return ConfidenceAssessment(
            "High", "Official EVA upgrade confirmation (manually entered).",
            True)
    if official_waitlist:
        return ConfidenceAssessment(
            "Medium",
            "Official EVA waitlist confirmed. Not guaranteed to clear.",
            True)

    clue = (expertflyer_clue or "").strip().lower()
    if clue == "strong":
        return ConfidenceAssessment(
            "Medium",
            "ExpertFlyer shows strong supporting clues. Medium confidence "
            "only - NOT official EVA upgrade confirmation.",
            False)
    if clue == "weak":
        return ConfidenceAssessment(
            "Low",
            "ExpertFlyer shows weak clues only. NOT official EVA "
            "upgrade confirmation.",
            False)
    if clue == "seatmap_only" or seatmap_only:
        return ConfidenceAssessment(
            "Low",
            "Seat map only. Seat-map availability is not the same as "
            "mileage upgrade availability.",
            False)
    return ConfidenceAssessment(
        "Low",
        "Fare class is upgradeable but upgrade availability is unknown. "
        "Verify with EVA.",
        False)
