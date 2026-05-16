"""Generate a Markdown decision report from a ComparisonResult."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .confidence import ConfidenceAssessment
from .fare_compare import ComparisonResult
from .models import ExpertFlyerCheck

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def _i(n) -> str:
    return "n/a" if n is None else f"{int(n):,}"


def build_report(
    result: ComparisonResult,
    ef_check: Optional[ExpertFlyerCheck] = None,
    confidence: Optional[ConfidenceAssessment] = None,
) -> str:
    L: List[str] = []
    L.append("# EVA Air Fare & Upgrade Decision Report")
    L.append("")
    L.append(f"_Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_")
    L.append("")
    L.append(f"- Passengers: {result.passengers}")
    L.append(f"- Compare: Economy **{result.economy_family}** vs "
             f"Premium Economy **{result.premium_family}**")
    L.append(f"- Currency: {result.currency}")
    L.append(f"- Your mile valuation: {result.mile_value} "
             f"{result.currency}/mile")
    L.append("")

    L.append("## Verdict")
    L.append(f"## {result.recommendation}")
    L.append("")
    L.append(result.reasoning)
    L.append("")
    if not result.blocked:
        L.append(f"- Cash upcharge: **{result.cash_upcharge:,.0f} "
                 f"{result.currency}**")
        L.append(f"- Miles saved (total): **{_i(result.miles_saved_total)}**")
        if result.implied_cost_per_saved_mile is not None:
            L.append(f"- Implied cost / saved mile: "
                     f"**{result.implied_cost_per_saved_mile:.4f} "
                     f"{result.currency}** (your value: {result.mile_value})")
    L.append("")

    if result.blocked:
        L.append("## Unverified Chart Legs")
        for n in result.block_notes:
            L.append(f"- {n}")
        L.append("")

    L.append("## Per-Leg Upgrade Mileage (per person)")
    L.append("")
    L.append("| Leg | Region pair | Economy | Premium Economy |")
    L.append("|---|---|---:|---:|")
    for e, p in zip(result.economy.legs, result.premium.legs):
        rp = (f"{e.origin_region} <-> {e.destination_region}"
              if e.origin_region and e.destination_region else "unknown")
        L.append(
            f"| {e.origin}-{e.destination} | {rp} | "
            f"{_i(e.miles) if e.status=='ok' else e.status} | "
            f"{_i(p.miles) if p.status=='ok' else p.status} |"
        )
    L.append("")
    L.append("| Metric | Economy | Premium Economy | Saved |")
    L.append("|---|---:|---:|---:|")
    L.append(f"| Per person total | {_i(result.economy_miles_per_person)} | "
             f"{_i(result.premium_miles_per_person)} | "
             f"{_i(result.miles_saved_per_person)} |")
    L.append(f"| All {result.passengers} passengers | "
             f"{_i(result.economy_miles_total)} | "
             f"{_i(result.premium_miles_total)} | "
             f"{_i(result.miles_saved_total)} |")
    L.append("")

    L.append("## Cash Comparison")
    L.append("> Prices = TOTAL booking cost (all passengers, all legs).")
    L.append("")
    L.append("| Item | Value |")
    L.append("|---|---:|")
    L.append(f"| Economy {result.economy_family} | "
             f"{result.economy_price:,.2f} {result.currency} |")
    L.append(f"| Premium Economy {result.premium_family} | "
             f"{result.premium_economy_price:,.2f} {result.currency} |")
    L.append(f"| Cash upcharge | {result.cash_upcharge:,.2f} "
             f"{result.currency} |")
    L.append("")

    L.append("## ExpertFlyer Observations")
    if ef_check is None:
        L.append("_No ExpertFlyer check recorded._")
    else:
        L.append(f"- Checked at: {ef_check.checked_at}")
        L.append(f"- Flight: {ef_check.flight_number} on {ef_check.date}")
        L.append(f"- Aircraft: {ef_check.aircraft}")
        if ef_check.business_seatmap_notes:
            L.append(f"- Business seat map: {ef_check.business_seatmap_notes}")
        if ef_check.fare_bucket_notes:
            L.append(f"- Fare bucket notes: {ef_check.fare_bucket_notes}")
        L.append(f"- Confidence clue: **{ef_check.confidence_clue}**")
        if ef_check.notes:
            L.append(f"- Notes: {ef_check.notes}")
        L.append("")
        L.append(f"> {ef_check.disclaimer}")
    L.append("")

    L.append("## Upgrade Confidence")
    if confidence is None:
        L.append("_No confidence assessment._")
    else:
        L.append(f"- Level: **{confidence.level}**")
        L.append(f"- Official EVA source: "
                 f"{'yes' if confidence.is_official else 'no'}")
        L.append(f"- {confidence.reasoning}")
    L.append("")

    L.append("## Risk Notes")
    L.append("- Aircraft type and seat map can change before departure.")
    L.append("- Seat-map availability is NOT mileage upgrade availability.")
    L.append("- Paid Business inventory is NOT mileage upgrade inventory.")
    L.append("- ExpertFlyer is third-party and never confirms EVA upgrade space.")
    L.append("- Premium Economy Basic P / Economy A/V/W/S are NOT upgradeable.")
    L.append("")
    L.append("## Action Checklist")
    L.append("- [ ] Confirm exact booking class before purchase.")
    L.append("- [ ] Verify mileage upgrade availability directly with EVA.")
    L.append("- [ ] Confirm enough Infinity MileageLands miles for all pax.")
    L.append("- [ ] Decide acceptable fallback cabin if upgrade does not clear.")
    L.append("")
    return "\n".join(L)


def save_report(content: str, filename: Optional[str] = None) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if filename is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"report_{stamp}.md"
    path = REPORTS_DIR / filename
    path.write_text(content)
    return path
