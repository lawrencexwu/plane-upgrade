"""CLI for the EVA fare/upgrade decision tool."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import expertflyer_input
from .confidence import assess
from .fare_compare import ComparisonInput, compare
from .models import ExpertFlyerCheck
from .parsers import parse_expertflyer, parse_fare_quote
from .report_generator import build_report, save_report
from .trip import Leg, Trip
from .upgrade_rules import classify_fare_class, leg_upgrade_miles, load_chart


def _legs_from_args(leg_codes: List[str]) -> List[Leg]:
    legs = []
    for code in leg_codes:
        o, _, d = code.partition("-")
        if not o or not d:
            raise SystemExit(f"Bad leg '{code}', expected ORIG-DEST e.g. TPE-ORD")
        legs.append(Leg(o.upper(), d.upper()))
    return legs


def _trip(args) -> Trip:
    legs = _legs_from_args(args.legs)
    tt = "one_way" if len(legs) == 1 else (
        "round_trip" if len(legs) == 2 else "multi_city")
    return Trip(tt, legs, passengers=args.passengers)


def cmd_compare(args) -> int:
    inp = ComparisonInput(
        trip=_trip(args),
        economy_price=args.economy_price,
        premium_economy_price=args.premium_economy_price,
        currency=args.currency,
        economy_family=args.economy_family.capitalize(),
        premium_family=args.premium_family.capitalize(),
        mile_value=args.mile_value,
    )
    r = compare(inp)
    print(f"\n=== {r.recommendation} ===")
    print(r.reasoning)
    if r.blocked:
        return 0
    print()
    print(f"Cash upcharge            : {r.cash_upcharge:,.0f} {r.currency}")
    print(f"Miles saved (total)      : {r.miles_saved_total:,}")
    print(f"Economy miles  (total)   : {r.economy_miles_total:,}")
    print(f"Premium miles  (total)   : {r.premium_miles_total:,}")
    if r.implied_cost_per_saved_mile is not None:
        print(f"Implied cost / saved mile: "
              f"{r.implied_cost_per_saved_mile:.4f} {r.currency} "
              f"(your value {r.mile_value})")
    print("\nNOTE: prices = TOTAL booking cost (all passengers, all legs).")
    return 0


def cmd_eligibility(args) -> int:
    chart = load_chart()
    fc = classify_fare_class(chart, args.fare_class)
    print(f"Fare class : {fc.fare_class}")
    print(f"Upgradeable: {'YES' if fc.upgradeable else 'NO'}")
    if fc.upgradeable:
        print(f"Cabin/fam  : {fc.cabin} {fc.fare_family}")
    print(f"Reason     : {fc.reason}")
    if args.leg and fc.upgradeable:
        o, _, d = args.leg.partition("-")
        lm = leg_upgrade_miles(chart, o, d, fc.cabin, fc.fare_family)
        print(f"Leg {args.leg}: {lm.note}")
    return 0


def cmd_parse_fare(args) -> int:
    p = parse_fare_quote(sys.stdin.read() if args.stdin else args.text or "")
    print("Parsed fare quote:")
    for k in ("cabin", "fare_family", "fare_class", "price", "currency",
              "flight_numbers", "airports"):
        print(f"  {k:15}: {getattr(p, k)}")
    for w in p.warnings:
        print(f"  ! {w}")
    return 0


def cmd_parse_ef(args) -> int:
    p = parse_expertflyer(sys.stdin.read() if args.stdin else args.text or "")
    print("Parsed ExpertFlyer text:")
    for k in ("flight_number", "aircraft", "departure", "arrival",
              "business_buckets", "open_business_buckets", "suggested_clue",
              "notes"):
        print(f"  {k:22}: {getattr(p, k)}")
    for w in p.warnings:
        print(f"  ! {w}")
    return 0


def cmd_add_ef(args) -> int:
    check = ExpertFlyerCheck(
        route=args.route, date=args.date, airline=args.airline,
        flight_number=args.flight_number, aircraft=args.aircraft or "",
        scheduled_departure=args.departure or "",
        scheduled_arrival=args.arrival or "",
        business_seatmap_notes=args.business_seatmap_notes or "",
        premium_seatmap_notes=args.premium_seatmap_notes or "",
        fare_bucket_notes=args.fare_bucket_notes or "",
        confidence_clue=args.confidence_clue or "unknown",
        notes=args.notes or "", screenshot_path=args.screenshot_path or "",
    )
    path = expertflyer_input.save(check)
    print(f"Saved to {path}")
    print("REMINDER: ExpertFlyer is a THIRD-PARTY CLUE, not official EVA "
          "upgrade confirmation.")
    return 0


def cmd_report(args) -> int:
    chart = load_chart()
    inp = ComparisonInput(
        trip=_trip(args),
        economy_price=args.economy_price,
        premium_economy_price=args.premium_economy_price,
        currency=args.currency,
        economy_family=args.economy_family.capitalize(),
        premium_family=args.premium_family.capitalize(),
        mile_value=args.mile_value,
    )
    r = compare(inp, chart=chart)
    ef = expertflyer_input.latest_any() if args.include_latest_expertflyer else None
    conf = None
    if args.fare_class:
        fc = classify_fare_class(chart, args.fare_class)
        conf = assess(fc, official_confirmed=args.official_confirmed,
                      official_waitlist=args.official_waitlist,
                      expertflyer_clue=(ef.confidence_clue if ef else None),
                      seatmap_only=args.seatmap_only)
    md = build_report(r, ef_check=ef, confidence=conf)
    path = save_report(md, filename=args.output)
    print(md)
    print(f"\nReport saved to {path}")
    return 0


def _add_trip_args(sp):
    sp.add_argument("--legs", nargs="+", required=True,
                    help="Legs as ORIG-DEST, e.g. TPE-ORD LAX-TPE "
                         "(1=one-way, 2=round-trip, 3+=multi-city)")
    sp.add_argument("--passengers", type=int, default=2)
    sp.add_argument("--economy-price", type=float, required=True)
    sp.add_argument("--premium-economy-price", type=float, required=True)
    sp.add_argument("--currency", default="TWD")
    sp.add_argument("--economy-family",
                    choices=["standard", "up", "Standard", "Up"],
                    default="standard")
    sp.add_argument("--premium-family",
                    choices=["standard", "up", "Standard", "Up"],
                    default="standard")
    sp.add_argument("--mile-value", type=float, required=True)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="src.cli",
                                description="EVA fare/upgrade decision tool.")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compare")
    _add_trip_args(c)
    c.set_defaults(func=cmd_compare)

    e = sub.add_parser("eligibility")
    e.add_argument("--fare-class", required=True)
    e.add_argument("--leg", default=None, help="Optional ORIG-DEST for miles.")
    e.set_defaults(func=cmd_eligibility)

    pf = sub.add_parser("parse-fare")
    pf.add_argument("--text", default=None)
    pf.add_argument("--stdin", action="store_true")
    pf.set_defaults(func=cmd_parse_fare)

    pe = sub.add_parser("parse-expertflyer")
    pe.add_argument("--text", default=None)
    pe.add_argument("--stdin", action="store_true")
    pe.set_defaults(func=cmd_parse_ef)

    a = sub.add_parser("add-expertflyer-check")
    a.add_argument("--route", required=True)
    a.add_argument("--date", required=True)
    a.add_argument("--airline", required=True)
    a.add_argument("--flight-number", required=True)
    a.add_argument("--aircraft", default="")
    a.add_argument("--departure", default="")
    a.add_argument("--arrival", default="")
    a.add_argument("--business-seatmap-notes", default="")
    a.add_argument("--premium-seatmap-notes", default="")
    a.add_argument("--fare-bucket-notes", default="")
    a.add_argument("--confidence-clue",
                   choices=["strong", "weak", "seatmap_only", "none", "unknown"],
                   default="unknown")
    a.add_argument("--notes", default="")
    a.add_argument("--screenshot-path", default="")
    a.set_defaults(func=cmd_add_ef)

    r = sub.add_parser("report")
    _add_trip_args(r)
    r.add_argument("--include-latest-expertflyer", action="store_true")
    r.add_argument("--fare-class", default=None)
    r.add_argument("--official-confirmed", action="store_true")
    r.add_argument("--official-waitlist", action="store_true")
    r.add_argument("--seatmap-only", action="store_true")
    r.add_argument("--output", default=None)
    r.set_defaults(func=cmd_report)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
