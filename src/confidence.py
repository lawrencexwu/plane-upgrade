"""Upgrade confidence scoring.

Never treat ExpertFlyer or seat map data as official EVA upgrade confirmation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .upgrade_rules import FareEligibility


@dataclass
class ConfidenceAssessment:
    level: str  # "High" | "Medium" | "Low" | "Do Not Buy"
    reasoning: str
    is_official: bool


def assess(
    eligibility: FareEligibility,
    official_confirmed: bool = False,
    official_waitlist: bool = False,
    expertflyer_clue: Optional[str] = None,  # "strong" | "weak" | None
    seatmap_only: bool = False,
) -> ConfidenceAssessment:
    """Score upgrade confidence. Manual official-EVA confirmation takes priority."""
    if not eligibility.upgradeable:
        return ConfidenceAssessment(
            "Do Not Buy",
            f"Fare class {eligibility.fare_class} is NON-UPGRADEABLE. "
            "DO NOT BUY FOR UPGRADE.",
            is_official=False,
        )

    if official_confirmed:
        return ConfidenceAssessment(
            "High",
            "Official EVA upgrade availability confirmed (manually entered).",
            is_official=True,
        )

    if official_waitlist:
        return ConfidenceAssessment(
            "Medium",
            "Official EVA waitlist confirmed. Not guaranteed to clear.",
            is_official=True,
        )

    clue = (expertflyer_clue or "").strip().lower()
    if clue == "strong":
        return ConfidenceAssessment(
            "Medium",
            "ExpertFlyer shows strong supporting clues (cabin not full, "
            "relevant fare inventory open, seat map has many unassigned "
            "Business seats). Medium confidence only — NOT official EVA "
            "upgrade confirmation.",
            is_official=False,
        )
    if clue == "weak":
        return ConfidenceAssessment(
            "Low",
            "ExpertFlyer shows weak clues only. NOT official EVA upgrade "
            "confirmation.",
            is_official=False,
        )

    if seatmap_only:
        return ConfidenceAssessment(
            "Low",
            "Seat map looks open, but seat map availability is not the same "
            "as mileage upgrade availability.",
            is_official=False,
        )

    return ConfidenceAssessment(
        "Low",
        "Fare class is upgradeable but upgrade availability is unknown. "
        "Verify with EVA before relying on the upgrade clearing.",
        is_official=False,
    )
