"""Generate a Markdown decision report."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .fare_compare import ComparisonResult
from .models import ExpertFlyerCheck
from .confidence import ConfidenceAssessment

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"


def _fmt_money(amount: float, currency: str) -> str:
    return f"{amount:,.2f} {currency}"


def _fmt_int(n) -> str:
    if n is None:
        return "n/a"
    return f"{int(n):,}"


def build_report(
    result: ComparisonResult,
    ef_check: Optional[ExpertFlyerCheck] = None,
    confidence: Optional[ConfidenceAssessment] = None,
    per_leg_breakdown: Optional[List[dict]] = None,
) -> str:
    lines: List[str] = []
    lines.append("# EVA Air Fare & Upgrade Decision Report")
    lines.append("")
    lines.append(
        f"_Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_"
    )
    lines.append("")
    lines.append(f"- Routes: `{' + '.join(result.routes)}`")
    lines.append(f"- Passengers: {result.passengers}")
    lines.append(
        f"- Comparison: Economy **{result.economy_family}** vs "
        f"Premium Economy **{result.premium_family}**"
    )
    lines.append(f"- Currency: {result.currency}")
    lines.append(f"- Your mile valuation: {result.mile_value} {result.currency}/mile")
    lines.append("")

    # Summary recommendation
    lines.append("## Summary Recommendation")
    lines.append(f"**{result.recommendation}**")
    lines.append("")
    lines.append(result.reasoning)
    lines.append("")
    lines.append(
        "> Note: Premium Economy Standard is likely better if the fare class "
        "is L/T AND the mileage upgrade is available or waitlistable. "
        "This tool cannot confirm EVA internal upgrade inventory."
    )
    lines.append("")

    # Upgrade Mileage Table
    lines.append("## Upgrade Mileage")
    lines.append("")
    if per_leg_breakdown:
        lines.append("| Route | Economy " + result.economy_family +
                     "/pp | Premium Economy " + result.premium_family + "/pp |")
        lines.append("|---|---:|---:|")
        for row in per_leg_breakdown:
            lines.append(
                f"| {row['route']} | {_fmt_int(row['economy_pp'])} | "
                f"{_fmt_int(row['premium_pp'])} |"
            )
        lines.append("")

    lines.append("| Metric | Economy | Premium Economy | Saved |")
    lines.append("|---|---:|---:|---:|")
    lines.append(
        f"| Per person total | {_fmt_int(result.economy_miles_per_person)} | "
        f"{_fmt_int(result.premium_miles_per_person)} | "
        f"{_fmt_int(result.miles_saved_per_person)} |"
    )
    lines.append(
        f"| All {result.passengers} passengers | "
        f"{_fmt_int(result.economy_miles_total)} | "
        f"{_fmt_int(result.premium_miles_total)} | "
        f"{_fmt_int(result.miles_saved_total)} |"
    )
    lines.append("")

    # Cash comparison
    lines.append("## Cash Comparison")
    lines.append("")
    lines.append("> Prices are interpreted as TOTAL trip cost for the whole booking "
                 "(all passengers, all legs).")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---:|")
    lines.append(
        f"| Economy {result.economy_family} price | "
        f"{_fmt_money(result.economy_price, result.currency)} |"
    )
    lines.append(
        f"| Premium Economy {result.premium_family} price | "
        f"{_fmt_money(result.premium_economy_price, result.currency)} |"
    )
    lines.append(
        f"| Cash upcharge for Premium Economy | "
        f"{_fmt_money(result.cash_upcharge, result.currency)} |"
    )
    lines.append(f"| Miles saved (total) | {_fmt_int(result.miles_saved_total)} |")
    if result.implied_cost_per_saved_mile is None:
        lines.append("| Implied cost per saved mile | n/a |")
    else:
        lines.append(
            f"| Implied cost per saved mile | "
            f"{result.implied_cost_per_saved_mile:.4f} {result.currency} / mile |"
        )
    lines.append(
        f"| Your mile valuation | {result.mile_value} {result.currency} / mile |"
    )
    lines.append("")

    # ExpertFlyer
    lines.append("## ExpertFlyer Observations")
    lines.append("")
    if ef_check is None:
        lines.append("_No ExpertFlyer check recorded for this report._")
    else:
        lines.append(f"- Checked at: {ef_check.checked_at}")
        lines.append(f"- Route: {ef_check.route}")
        fn = ef_check.flight_number
        if not fn.upper().startswith(ef_check.airline.upper()):
            fn = f"{ef_check.airline}{fn}"
        lines.append(f"- Flight: {fn} on {ef_check.date}")
        lines.append(f"- Aircraft: {ef_check.aircraft}")
        lines.append(f"- Scheduled: {ef_check.scheduled_departure} → "
                     f"{ef_check.scheduled_arrival}")
        if ef_check.business_seatmap_notes:
            lines.append(f"- Business seat map: {ef_check.business_seatmap_notes}")
        if ef_check.premium_seatmap_notes:
            lines.append(f"- Premium Economy seat map: "
                         f"{ef_check.premium_seatmap_notes}")
        if ef_check.economy_seatmap_notes:
            lines.append(f"- Economy seat map: {ef_check.economy_seatmap_notes}")
        if ef_check.fare_bucket_notes:
            lines.append(f"- Fare bucket / inventory notes: "
                         f"{ef_check.fare_bucket_notes}")
        if ef_check.business_availability_clue:
            lines.append(f"- Business availability clue: "
                         f"{ef_check.business_availability_clue}")
        if ef_check.premium_availability_clue:
            lines.append(f"- Premium Economy availability clue: "
                         f"{ef_check.premium_availability_clue}")
        lines.append(f"- Confidence clue: **{ef_check.confidence_clue}**")
        if ef_check.notes:
            lines.append(f"- Notes: {ef_check.notes}")
        if ef_check.screenshot_path:
            lines.append(f"- Screenshot: `{ef_check.screenshot_path}`")
        lines.append("")
        lines.append(f"> {ef_check.disclaimer}")
    lines.append("")

    # Confidence
    lines.append("## Upgrade Confidence")
    if confidence is None:
        lines.append("_No confidence assessment provided._")
    else:
        lines.append(f"- Level: **{confidence.level}**")
        lines.append(f"- Official EVA source: "
                     f"{'yes' if confidence.is_official else 'no'}")
        lines.append(f"- Reasoning: {confidence.reasoning}")
    lines.append("")

    # Risks
    lines.append("## Risk Notes")
    lines.append("")
    lines.append("- Aircraft type and seat map can change before departure.")
    lines.append("- Seat map availability is NOT the same as upgrade availability.")
    lines.append("- Paid Business inventory is NOT the same as mileage upgrade inventory.")
    lines.append("- ExpertFlyer is third-party and does not confirm EVA upgrade space.")
    lines.append("- Premium Economy Basic P is NOT upgradeable.")
    lines.append("- Economy Discount/Basic A/V/W/S are NOT upgradeable.")
    lines.append("")

    # Action checklist
    lines.append("## Action Checklist")
    lines.append("")
    lines.append("- [ ] Confirm exact fare class (e.g. L vs T vs P) before purchase.")
    lines.append("- [ ] Verify mileage upgrade availability with EVA "
                 "(website, agent, or waitlist).")
    lines.append("- [ ] Re-check ExpertFlyer closer to departure if upgrade has not cleared.")
    lines.append("- [ ] Confirm aircraft type and Royal Laurel cabin layout.")
    lines.append("- [ ] Confirm you have enough Infinity MileageLands miles for both passengers.")
    lines.append("- [ ] Decide acceptable fallback cabin if upgrade does NOT clear.")
    lines.append("")
    return "\n".join(lines)


def save_report(content: str, filename: Optional[str] = None) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if filename is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"report_{stamp}.md"
    path = REPORTS_DIR / filename
    path.write_text(content)
    return path
