"""Streamlit dashboard for the EVA Air fare/upgrade decision tool.

Run:
    streamlit run src/dashboard.py

This is a thin UI on top of the existing modules in src/. It does not scrape,
log in, or store credentials. ExpertFlyer data is entered manually and saved
through the same persistence layer as the CLI.
"""
from __future__ import annotations

import streamlit as st

from src import expertflyer_input
from src.confidence import assess
from src.fare_compare import ComparisonInput, compare
from src.models import ExpertFlyerCheck
from src.report_generator import build_report, save_report
from src.upgrade_rules import (
    check_eligibility,
    load_chart,
    load_settings,
    miles_for_bucket,
)

ROUTE_PAIRS = {
    "TPE-ORD + LAX-TPE (open-jaw target trip)": ["TPE-ORD", "LAX-TPE"],
    "TPE-ORD only": ["TPE-ORD"],
    "LAX-TPE only": ["LAX-TPE"],
}

FAMILY_OPTIONS = ["Standard", "Up"]


def _fmt_int(n) -> str:
    if n is None:
        return "n/a"
    return f"{int(n):,}"


def _confidence_color(level: str) -> str:
    return {
        "High": "green",
        "Medium": "orange",
        "Low": "gray",
        "Do Not Buy": "red",
    }.get(level, "gray")


def main():
    st.set_page_config(
        page_title="EVA Fare & Upgrade Decision",
        page_icon="✈",
        layout="wide",
    )
    st.title("EVA Air Fare & Upgrade Decision Assistant")
    st.caption(
        "Local tool. No ticket purchase. No login automation. "
        "No credentials stored. ExpertFlyer data is manual and treated as a "
        "third-party clue only."
    )

    chart = load_chart()
    try:
        settings = load_settings()
    except FileNotFoundError:
        settings = {}

    # ---- Sidebar: inputs ----
    st.sidebar.header("Inputs")

    pair_label = st.sidebar.selectbox(
        "Route pair", list(ROUTE_PAIRS.keys()), index=0
    )
    routes = ROUTE_PAIRS[pair_label]

    passengers = st.sidebar.number_input(
        "Passengers", min_value=1, max_value=9,
        value=int(settings.get("default_passengers", 2)), step=1,
    )

    currency_default = settings.get("default_currency", "TWD")
    currency = st.sidebar.selectbox(
        "Currency", ["TWD", "USD"],
        index=0 if currency_default == "TWD" else 1,
    )

    mile_value_default = (
        settings.get("eva_mile_value", {}).get(currency, 0.8 if currency == "TWD" else 0.025)
    )
    mile_value = st.sidebar.number_input(
        f"Your EVA mile valuation ({currency} / mile)",
        min_value=0.0, value=float(mile_value_default), step=0.01, format="%.4f",
    )

    economy_family = st.sidebar.selectbox("Economy fare family", FAMILY_OPTIONS, index=0)
    premium_family = st.sidebar.selectbox(
        "Premium Economy fare family", FAMILY_OPTIONS, index=0
    )

    st.sidebar.markdown("**Prices (booking total, all passengers, all legs)**")
    economy_price = st.sidebar.number_input(
        f"Economy {economy_family} price ({currency})",
        min_value=0.0, value=110000.0, step=1000.0,
    )
    premium_economy_price = st.sidebar.number_input(
        f"Premium Economy {premium_family} price ({currency})",
        min_value=0.0, value=160000.0, step=1000.0,
    )

    st.sidebar.markdown("**Eligibility / confidence inputs**")
    fare_class = st.sidebar.text_input(
        "Premium Economy fare class to evaluate (e.g. L, T, K, P)", value="L"
    ).strip().upper()
    official_confirmed = st.sidebar.checkbox(
        "Official EVA upgrade confirmed (manual)", value=False
    )
    official_waitlist = st.sidebar.checkbox(
        "Official EVA waitlist confirmed (manual)", value=False
    )
    seatmap_only = st.sidebar.checkbox(
        "Only seat map evidence available", value=False
    )

    # ---- Main: comparison ----
    inp = ComparisonInput(
        routes=routes,
        passengers=int(passengers),
        economy_price=float(economy_price),
        premium_economy_price=float(premium_economy_price),
        currency=currency,
        economy_family=economy_family,
        premium_family=premium_family,
        mile_value=float(mile_value),
    )
    result = compare(inp, chart=chart)

    st.subheader("Recommendation")
    rec_color = {
        "Premium Economy": "green",
        "Economy": "gray",
    }.get(result.recommendation, "orange")
    if "Do Not Buy" in result.recommendation:
        rec_color = "red"
    st.markdown(
        f"### :{rec_color}[{result.recommendation}]"
    )
    st.write(result.reasoning)

    # Top metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash upcharge",
              f"{result.cash_upcharge:,.0f} {currency}")
    c2.metric("Miles saved (total)",
              _fmt_int(result.miles_saved_total))
    c3.metric("Implied cost / saved mile",
              "n/a" if result.implied_cost_per_saved_mile is None
              else f"{result.implied_cost_per_saved_mile:.4f} {currency}")
    c4.metric("Your mile valuation",
              f"{mile_value} {currency}")

    # ---- Mileage table ----
    st.subheader("Upgrade Mileage")

    per_leg_rows = []
    for r in routes:
        per_leg_rows.append({
            "Route": r,
            f"Economy {economy_family} / pp":
                miles_for_bucket(chart, r, "Economy", economy_family),
            f"Premium Economy {premium_family} / pp":
                miles_for_bucket(chart, r, "Premium Economy", premium_family),
        })
    st.table(per_leg_rows)

    totals_rows = [
        {
            "Metric": "Per person total",
            "Economy": _fmt_int(result.economy_miles_per_person),
            "Premium Economy": _fmt_int(result.premium_miles_per_person),
            "Saved": _fmt_int(result.miles_saved_per_person),
        },
        {
            "Metric": f"All {result.passengers} passengers",
            "Economy": _fmt_int(result.economy_miles_total),
            "Premium Economy": _fmt_int(result.premium_miles_total),
            "Saved": _fmt_int(result.miles_saved_total),
        },
    ]
    st.table(totals_rows)

    # ---- Eligibility + Confidence ----
    st.subheader("Fare Class Eligibility & Confidence")
    elig_col, conf_col = st.columns(2)

    eligibility = None
    if fare_class:
        eligibility = check_eligibility(chart, routes[0], fare_class)
        with elig_col:
            st.markdown(f"**Route:** `{eligibility.route}`")
            st.markdown(f"**Fare class:** `{eligibility.fare_class}`")
            if eligibility.upgradeable:
                st.success(
                    f"Upgradeable — {eligibility.cabin} {eligibility.fare_family} "
                    f"→ Business for {eligibility.miles_to_business:,} miles/pp"
                )
            else:
                st.error(eligibility.reason)

    # Pull latest ExpertFlyer for confidence boost
    ef_latest = expertflyer_input.latest_any()
    ef_clue = ef_latest.confidence_clue if ef_latest else None

    if eligibility is not None:
        confidence = assess(
            eligibility,
            official_confirmed=official_confirmed,
            official_waitlist=official_waitlist,
            expertflyer_clue=ef_clue,
            seatmap_only=seatmap_only,
        )
        with conf_col:
            color = _confidence_color(confidence.level)
            st.markdown(f"**Confidence level:** :{color}[{confidence.level}]")
            st.markdown(
                f"**Source officiality:** "
                f"{'official EVA input' if confidence.is_official else 'NOT official EVA'}"
            )
            st.write(confidence.reasoning)
    else:
        confidence = None

    # ---- ExpertFlyer manual entry ----
    st.subheader("ExpertFlyer — Manual Entry")
    st.caption(
        "ExpertFlyer data is treated as a third-party clue only. It is NOT "
        "official EVA upgrade confirmation. Seat map availability is not the "
        "same as mileage upgrade availability."
    )

    with st.form("ef_form"):
        ef_route = st.selectbox("Route", routes, index=len(routes) - 1)
        ef_date = st.text_input("Date (YYYY-MM-DD)", value="2026-06-23")
        ef_airline = st.text_input("Airline code", value="BR")
        ef_flight = st.text_input("Flight number", value="BR15")
        ef_aircraft = st.text_input("Aircraft", value="Boeing 777-300ER")
        c_dep, c_arr = st.columns(2)
        ef_departure = c_dep.text_input("Scheduled departure", value="00:50")
        ef_arrival = c_arr.text_input("Scheduled arrival", value="05:20+1")

        ef_business_notes = st.text_area("Business cabin seat-map notes", value="")
        ef_premium_notes = st.text_area("Premium Economy seat-map notes", value="")
        ef_economy_notes = st.text_area("Economy seat-map notes", value="")
        ef_fare_bucket = st.text_area("Fare bucket / inventory notes", value="")
        ef_seat_count = st.text_input("Seat count / observations", value="")

        ef_biz_clue = st.text_input("Business availability clue (free text)", value="")
        ef_pe_clue = st.text_input(
            "Premium Economy availability clue (free text)", value=""
        )

        ef_clue_choice = st.selectbox(
            "Overall confidence clue",
            ["unknown", "strong", "weak", "none"], index=0,
        )
        ef_notes = st.text_area(
            "Notes",
            value="Seat map only. Not official EVA upgrade inventory.",
        )
        ef_screenshot = st.text_input("Screenshot path (optional)", value="")
        submit = st.form_submit_button("Save ExpertFlyer check")

    if submit:
        check = ExpertFlyerCheck(
            route=ef_route,
            date=ef_date,
            airline=ef_airline,
            flight_number=ef_flight,
            aircraft=ef_aircraft,
            scheduled_departure=ef_departure,
            scheduled_arrival=ef_arrival,
            business_seatmap_notes=ef_business_notes,
            premium_seatmap_notes=ef_premium_notes,
            economy_seatmap_notes=ef_economy_notes,
            seat_count_observations=ef_seat_count,
            fare_bucket_notes=ef_fare_bucket,
            business_availability_clue=ef_biz_clue,
            premium_availability_clue=ef_pe_clue,
            confidence_clue=ef_clue_choice,
            notes=ef_notes,
            screenshot_path=ef_screenshot,
        )
        path = expertflyer_input.save(check)
        st.success(f"Saved to {path}")
        st.warning(
            "Reminder: ExpertFlyer is a third-party clue, not official EVA "
            "upgrade confirmation."
        )
        ef_latest = check  # show it below right away

    # ---- Latest ExpertFlyer summary ----
    st.subheader("Latest ExpertFlyer Observations")
    if ef_latest is None:
        st.info("No ExpertFlyer checks recorded yet.")
    else:
        st.markdown(
            f"- Checked at: `{ef_latest.checked_at}`\n"
            f"- Route: `{ef_latest.route}`\n"
            f"- Flight: `{ef_latest.airline}{ef_latest.flight_number}` "
            f"on `{ef_latest.date}`\n"
            f"- Aircraft: {ef_latest.aircraft or '_n/a_'}\n"
            f"- Scheduled: {ef_latest.scheduled_departure} → "
            f"{ef_latest.scheduled_arrival}\n"
            f"- Confidence clue: **{ef_latest.confidence_clue}**"
        )
        if ef_latest.business_seatmap_notes:
            st.markdown(f"- Business seat map: {ef_latest.business_seatmap_notes}")
        if ef_latest.premium_seatmap_notes:
            st.markdown(
                f"- Premium Economy seat map: {ef_latest.premium_seatmap_notes}"
            )
        if ef_latest.fare_bucket_notes:
            st.markdown(f"- Fare bucket notes: {ef_latest.fare_bucket_notes}")
        if ef_latest.notes:
            st.markdown(f"- Notes: {ef_latest.notes}")
        st.caption(ef_latest.disclaimer)

    # ---- Warnings ----
    st.subheader("Warnings")
    st.warning(
        "- Aircraft type and seat map can change before departure.\n"
        "- Seat map availability is NOT the same as mileage upgrade availability.\n"
        "- Paid Business inventory is NOT the same as mileage upgrade inventory.\n"
        "- ExpertFlyer is third-party and does not confirm EVA upgrade space.\n"
        "- Premium Economy Basic P is NOT upgradeable.\n"
        "- Economy Discount/Basic A/V/W/S are NOT upgradeable."
    )

    # ---- Report download ----
    st.subheader("Export Report")
    per_leg_breakdown = [
        {
            "route": r,
            "economy_pp": miles_for_bucket(chart, r, "Economy", economy_family),
            "premium_pp": miles_for_bucket(chart, r, "Premium Economy", premium_family),
        }
        for r in routes
    ]
    md = build_report(result, ef_check=ef_latest, confidence=confidence,
                      per_leg_breakdown=per_leg_breakdown)
    st.download_button(
        "Download Markdown report",
        data=md,
        file_name="eva_upgrade_report.md",
        mime="text/markdown",
    )
    if st.button("Save report to reports/"):
        path = save_report(md)
        st.success(f"Report saved to {path}")


if __name__ == "__main__":
    main()
