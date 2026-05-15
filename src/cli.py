"""Command line interface for the EVA fare/upgrade decision tool."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional

from . import expertflyer_input
from .confidence import assess
from .fare_compare import ComparisonInput, compare
from .models import ExpertFlyerCheck, FareQuote
from .report_generator import build_report, save_report
from .upgrade_rules import (
    check_eligibility,
    load_chart,
    load_settings,
    miles_for_bucket,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FARE_CSV = DATA_DIR / "fare_checks.csv"


def _print_kv(items):
    width = max(len(k) for k, _ in items)
    for k, v in items:
        print(f"  {k.ljust(width)} : {v}")


def _append_fare_csv(quote: FareQuote):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    row = quote.to_dict()
    write_header = not FARE_CSV.exists()
    with open(FARE_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)


def cmd_compare(args) -> int:
    inp = ComparisonInput(
        routes=args.routes,
        passengers=args.passengers,
        economy_price=args.economy_price,
        premium_economy_price=args.premium_economy_price,
        currency=args.currency,
        economy_family=args.economy_family.capitalize(),
        premium_family=args.premium_family.capitalize(),
        mile_value=args.mile_value,
    )
    result = compare(inp)

    print("== EVA Fare Comparison ==")
    _print_kv([
        ("Routes", " + ".join(result.routes)),
        ("Passengers", result.passengers),
        ("Compare", f"Economy {result.economy_family} vs "
                    f"Premium Economy {result.premium_family}"),
        ("Currency", result.currency),
    ])
    print()
    print("-- Upgrade miles --")
    _print_kv([
        (f"Economy {result.economy_family} / person",
         f"{result.economy_miles_per_person:,}"),
        (f"Premium Economy {result.premium_family} / person",
         f"{result.premium_miles_per_person:,}"),
        (f"Economy {result.economy_family} total ({result.passengers} pax)",
         f"{result.economy_miles_total:,}"),
        (f"Premium Economy {result.premium_family} total ({result.passengers} pax)",
         f"{result.premium_miles_total:,}"),
        ("Miles saved / person", f"{result.miles_saved_per_person:,}"),
        ("Miles saved total", f"{result.miles_saved_total:,}"),
    ])
    print()
    print("-- Cash --")
    _print_kv([
        ("Economy price (booking total)",
         f"{result.economy_price:,.2f} {result.currency}"),
        ("Premium Economy price (booking total)",
         f"{result.premium_economy_price:,.2f} {result.currency}"),
        ("Cash upcharge", f"{result.cash_upcharge:,.2f} {result.currency}"),
        ("Implied cost / saved mile",
         "n/a" if result.implied_cost_per_saved_mile is None
         else f"{result.implied_cost_per_saved_mile:.4f} {result.currency}/mile"),
        ("Your mile valuation",
         f"{result.mile_value} {result.currency}/mile"),
    ])
    print()
    print(f"Recommendation: {result.recommendation}")
    print(f"Reason: {result.reasoning}")
    print()
    print("NOTE: Prices interpreted as TOTAL trip cost for the booking "
          "(all passengers, all legs).")
    return 0


def cmd_eligibility(args) -> int:
    chart = load_chart()
    e = check_eligibility(chart, args.route, args.fare_class)
    print(f"Route       : {e.route}")
    print(f"Fare class  : {e.fare_class}")
    if e.upgradeable:
        print(f"Cabin       : {e.cabin}")
        print(f"Fare family : {e.fare_family}")
        print(f"Upgradeable : YES")
        print(f"Miles to Business (per person): {e.miles_to_business:,}")
    else:
        print("Upgradeable : NO")
    print(f"Reason      : {e.reason}")
    return 0


def cmd_add_expertflyer(args) -> int:
    check = ExpertFlyerCheck(
        route=args.route,
        date=args.date,
        airline=args.airline,
        flight_number=args.flight_number,
        aircraft=args.aircraft or "",
        scheduled_departure=args.departure or "",
        scheduled_arrival=args.arrival or "",
        business_seatmap_notes=args.business_seatmap_notes or "",
        premium_seatmap_notes=args.premium_seatmap_notes or "",
        economy_seatmap_notes=args.economy_seatmap_notes or "",
        seat_count_observations=args.seat_count_observations or "",
        fare_bucket_notes=args.fare_bucket_notes or "",
        business_availability_clue=args.business_availability_clue or "",
        premium_availability_clue=args.premium_availability_clue or "",
        confidence_clue=args.confidence_clue or "unknown",
        notes=args.notes or "",
        screenshot_path=args.screenshot_path or "",
    )
    path = expertflyer_input.save(check)
    print(f"Saved ExpertFlyer check to {path}")
    print("REMINDER: ExpertFlyer is a THIRD-PARTY CLUE, not official EVA "
          "upgrade confirmation.")
    return 0


def cmd_add_fare(args) -> int:
    quote = FareQuote(
        route=args.route,
        cabin=args.cabin,
        fare_family=args.fare_family,
        fare_class=args.fare_class,
        price=args.price,
        taxes_fees=args.taxes_fees or 0.0,
        currency=args.currency,
        passengers=args.passengers,
        flight_number=args.flight_number,
        date=args.date,
        source=args.source,
        notes=args.notes or "",
    )
    _append_fare_csv(quote)
    print(f"Saved fare quote to {FARE_CSV}")
    return 0


def cmd_report(args) -> int:
    inp = ComparisonInput(
        routes=args.routes,
        passengers=args.passengers,
        economy_price=args.economy_price,
        premium_economy_price=args.premium_economy_price,
        currency=args.currency,
        economy_family=args.economy_family.capitalize(),
        premium_family=args.premium_family.capitalize(),
        mile_value=args.mile_value,
    )
    chart = load_chart()
    result = compare(inp, chart=chart)

    per_leg = []
    for r in args.routes:
        per_leg.append({
            "route": r,
            "economy_pp": miles_for_bucket(chart, r, "Economy", inp.economy_family),
            "premium_pp": miles_for_bucket(chart, r, "Premium Economy",
                                           inp.premium_family),
        })

    ef_check: Optional[ExpertFlyerCheck] = None
    if args.include_latest_expertflyer:
        ef_check = expertflyer_input.latest_any()

    # Eligibility-based confidence: if user supplies a fare class, derive it.
    confidence = None
    if args.fare_class and args.routes:
        elig = check_eligibility(chart, args.routes[0], args.fare_class)
        confidence = assess(
            elig,
            official_confirmed=args.official_confirmed,
            official_waitlist=args.official_waitlist,
            expertflyer_clue=(ef_check.confidence_clue if ef_check else None),
            seatmap_only=args.seatmap_only,
        )

    content = build_report(result, ef_check=ef_check, confidence=confidence,
                           per_leg_breakdown=per_leg)
    path = save_report(content, filename=args.output)
    print(content)
    print(f"\nReport saved to {path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="src.cli",
        description="EVA Air fare-and-upgrade decision assistant (local).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # compare
    c = sub.add_parser("compare", help="Compare Economy vs Premium Economy upgrade economics.")
    c.add_argument("--routes", nargs="+", required=True,
                   help="One or more route codes, e.g. TPE-ORD LAX-TPE")
    c.add_argument("--passengers", type=int, default=2)
    c.add_argument("--economy-price", type=float, required=True,
                   help="Total Economy price for the whole booking.")
    c.add_argument("--premium-economy-price", type=float, required=True,
                   help="Total Premium Economy price for the whole booking.")
    c.add_argument("--currency", default="TWD")
    c.add_argument("--economy-family", choices=["standard", "up", "Standard", "Up"],
                   default="standard")
    c.add_argument("--premium-family", choices=["standard", "up", "Standard", "Up"],
                   default="standard")
    c.add_argument("--mile-value", type=float, required=True,
                   help="Your value per EVA mile in the same currency.")
    c.set_defaults(func=cmd_compare)

    # eligibility
    e = sub.add_parser("eligibility", help="Check fare class upgrade eligibility.")
    e.add_argument("--route", required=True)
    e.add_argument("--fare-class", required=True)
    e.set_defaults(func=cmd_eligibility)

    # add-expertflyer-check
    a = sub.add_parser("add-expertflyer-check",
                       help="Save a manual ExpertFlyer observation.")
    a.add_argument("--route", required=True)
    a.add_argument("--date", required=True)
    a.add_argument("--airline", required=True)
    a.add_argument("--flight-number", required=True)
    a.add_argument("--aircraft", default="")
    a.add_argument("--departure", default="")
    a.add_argument("--arrival", default="")
    a.add_argument("--business-seatmap-notes", default="")
    a.add_argument("--premium-seatmap-notes", default="")
    a.add_argument("--economy-seatmap-notes", default="")
    a.add_argument("--seat-count-observations", default="")
    a.add_argument("--fare-bucket-notes", default="")
    a.add_argument("--business-availability-clue", default="")
    a.add_argument("--premium-availability-clue", default="")
    a.add_argument("--confidence-clue",
                   choices=["strong", "weak", "none", "unknown"],
                   default="unknown")
    a.add_argument("--notes", default="")
    a.add_argument("--screenshot-path", default="")
    a.set_defaults(func=cmd_add_expertflyer)

    # add-fare (small helper, since the user spec lists fare history persistence)
    f = sub.add_parser("add-fare", help="Persist a fare quote to fare_checks.csv.")
    f.add_argument("--route", required=True)
    f.add_argument("--cabin", required=True)
    f.add_argument("--fare-family", required=True)
    f.add_argument("--fare-class", required=True)
    f.add_argument("--price", type=float, required=True)
    f.add_argument("--taxes-fees", type=float, default=0.0)
    f.add_argument("--currency", default="TWD")
    f.add_argument("--passengers", type=int, default=2)
    f.add_argument("--flight-number", default=None)
    f.add_argument("--date", default=None)
    f.add_argument("--source", default="manual")
    f.add_argument("--notes", default="")
    f.set_defaults(func=cmd_add_fare)

    # report
    r = sub.add_parser("report", help="Generate a Markdown decision report.")
    r.add_argument("--routes", nargs="+", required=True)
    r.add_argument("--passengers", type=int, default=2)
    r.add_argument("--economy-price", type=float, required=True)
    r.add_argument("--premium-economy-price", type=float, required=True)
    r.add_argument("--currency", default="TWD")
    r.add_argument("--economy-family", choices=["standard", "up", "Standard", "Up"],
                   default="standard")
    r.add_argument("--premium-family", choices=["standard", "up", "Standard", "Up"],
                   default="standard")
    r.add_argument("--mile-value", type=float, required=True)
    r.add_argument("--include-latest-expertflyer", action="store_true")
    r.add_argument("--fare-class", default=None,
                   help="Optional: fare class to use for confidence scoring.")
    r.add_argument("--official-confirmed", action="store_true")
    r.add_argument("--official-waitlist", action="store_true")
    r.add_argument("--seatmap-only", action="store_true")
    r.add_argument("--output", default=None,
                   help="Optional report filename (under reports/).")
    r.set_defaults(func=cmd_report)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
