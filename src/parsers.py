"""Heuristic paste-and-parse for EVA fare quotes and ExpertFlyer text.

These NEVER fetch anything. The user pastes text they already see in their own
logged-in browser session. Parsers extract best-guess structured values and
always return what they found plus warnings, so the user confirms before use.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

_AIRPORT = re.compile(r"\b([A-Z]{3})\b")
_FLIGHT = re.compile(r"\b(?:BR|B7)\s?(\d{1,4})\b")
_TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
_MONEY = re.compile(
    r"(?:NT\$|TWD|US\$|USD|\$|EUR|€|JPY|¥)\s?([\d,]+(?:\.\d{1,2})?)"
    r"|([\d,]{4,}(?:\.\d{1,2})?)\s?(TWD|USD|NTD)",
    re.IGNORECASE,
)
_CABIN_PATTERNS = [
    ("Premium Economy", re.compile(r"premium\s*economy", re.I)),
    ("Business", re.compile(r"\b(business|royal laurel)\b", re.I)),
    ("Economy", re.compile(r"\beconomy\b", re.I)),
]
_FAMILY_PATTERNS = [
    ("Up", re.compile(r"\bup\b", re.I)),
    ("Standard", re.compile(r"\bstandard\b", re.I)),
    ("Basic", re.compile(r"\bbasic\b", re.I)),
    ("Discount", re.compile(r"\bdiscount\b", re.I)),
]
_FARE_CLASS = re.compile(
    r"(?:booking\s*class|fare\s*class|class\s*of\s*service|RBD)\s*[:\-]?\s*([A-Z])\b",
    re.I,
)
_FARE_CLASS_PAREN = re.compile(r"\(([A-Z])\)")
# ExpertFlyer-style availability tokens, e.g. "J9 C9 D4 Z0 I0"
_BUCKET = re.compile(r"\b([A-Z])(\d{1,2})\b")
_BUSINESS_BUCKETS = set("JCDZIRPN")  # common EVA business inventory letters


@dataclass
class ParsedFare:
    cabin: Optional[str] = None
    fare_family: Optional[str] = None
    fare_class: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    flight_numbers: List[str] = field(default_factory=list)
    airports: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw: str = ""


@dataclass
class ParsedExpertFlyer:
    flight_number: Optional[str] = None
    aircraft: Optional[str] = None
    departure: Optional[str] = None
    arrival: Optional[str] = None
    airports: List[str] = field(default_factory=list)
    business_buckets: List[str] = field(default_factory=list)
    open_business_buckets: int = 0
    suggested_clue: str = "unknown"  # strong | weak | seatmap_only | unknown
    notes: str = ""
    warnings: List[str] = field(default_factory=list)
    raw: str = ""


def _money(text: str):
    m = _MONEY.search(text)
    if not m:
        return None, None
    amt = m.group(1) or m.group(3 - 1) or m.group(2)
    cur = None
    head = text[max(0, m.start() - 5):m.start() + 4].upper()
    if "TWD" in head or "NT$" in head or "NTD" in head:
        cur = "TWD"
    elif "USD" in head or "US$" in head or "$" in head:
        cur = "USD"
    if m.group(3):
        cur = {"NTD": "TWD"}.get(m.group(3).upper(), m.group(3).upper())
    try:
        return float(amt.replace(",", "")), cur
    except (TypeError, ValueError):
        return None, cur


def parse_fare_quote(text: str) -> ParsedFare:
    p = ParsedFare(raw=text or "")
    if not text or not text.strip():
        p.warnings.append("Empty input.")
        return p

    for label, rx in _CABIN_PATTERNS:
        if rx.search(text):
            p.cabin = label
            break
    for label, rx in _FAMILY_PATTERNS:
        if rx.search(text):
            p.fare_family = label
            break

    m = _FARE_CLASS.search(text)
    if m:
        p.fare_class = m.group(1).upper()
    else:
        mp = _FARE_CLASS_PAREN.search(text)
        if mp:
            p.fare_class = mp.group(1).upper()

    p.price, p.currency = _money(text)
    p.flight_numbers = sorted({f"BR{n}" for n in _FLIGHT.findall(text)})
    p.airports = sorted(set(_AIRPORT.findall(text)) - {
        "USD", "TWD", "NTD", "EUR", "JPY", "GMT", "UTC", "EVA", "AIR", "BR",
        "PNR", "RBD", "ECO"
    })

    if not p.cabin:
        p.warnings.append("Cabin not detected - confirm manually.")
    if not p.fare_class:
        p.warnings.append(
            "Fare class not detected. This matters: P / A / V / W / S are "
            "non-upgradeable. Confirm the booking class."
        )
    if p.price is None:
        p.warnings.append("Price not detected - enter it manually.")
    if not p.fare_family:
        p.warnings.append("Fare family (Standard/Up) not detected.")
    return p


def parse_expertflyer(text: str) -> ParsedExpertFlyer:
    p = ParsedExpertFlyer(raw=text or "")
    if not text or not text.strip():
        p.warnings.append("Empty input.")
        return p

    fl = _FLIGHT.search(text)
    if fl:
        p.flight_number = f"BR{fl.group(1)}"
    times = _TIME.findall(text)
    if times:
        p.departure = f"{times[0][0]}:{times[0][1]}"
        if len(times) > 1:
            p.arrival = f"{times[1][0]}:{times[1][1]}"
    am = re.search(r"\b(Boeing\s?7\d{2}[- ]?\d{0,3}\w*|Airbus\s?A3\d{2}\w*|"
                   r"77W|77L|789|78\d|33\d|359)\b", text, re.I)
    if am:
        p.aircraft = am.group(1)
    p.airports = sorted(set(_AIRPORT.findall(text)) - {
        "USD", "TWD", "GMT", "UTC", "EVA"
    })

    buckets = _BUCKET.findall(text)
    open_biz = 0
    biz_seen = []
    for letter, num in buckets:
        if letter in _BUSINESS_BUCKETS:
            biz_seen.append(f"{letter}{num}")
            if int(num) > 0:
                open_biz += 1
    p.business_buckets = biz_seen
    p.open_business_buckets = open_biz

    has_seatmap_words = bool(re.search(r"seat\s*map|unassigned|open seat", text, re.I))
    if biz_seen and open_biz >= 2:
        p.suggested_clue = "strong"
        p.notes = (f"{open_biz} business inventory buckets appear open "
                   f"({', '.join(biz_seen)}).")
    elif biz_seen and open_biz == 1:
        p.suggested_clue = "weak"
        p.notes = f"Only 1 business bucket appears open ({', '.join(biz_seen)})."
    elif has_seatmap_words:
        p.suggested_clue = "seatmap_only"
        p.notes = ("Seat-map language detected but no business fare-bucket "
                   "inventory parsed.")
    else:
        p.suggested_clue = "unknown"
        p.warnings.append(
            "No business fare-bucket inventory or seat-map clue parsed."
        )

    p.warnings.append(
        "ExpertFlyer is a third-party clue only. Fare-bucket / seat-map data "
        "is NOT EVA mileage-upgrade inventory. Confirm clue level yourself."
    )
    return p
