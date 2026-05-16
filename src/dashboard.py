"""Streamlit dashboard: paste-and-parse, universal trip, glanceable verdict.

    streamlit run src/dashboard.py

No fetching, no login, no credentials. You paste text you already see in your
own browser; the tool parses and decides.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from src import expertflyer_input
from src.confidence import assess
from src.fare_compare import ComparisonInput, compare
from src.models import ExpertFlyerCheck
from src.parsers import parse_expertflyer, parse_fare_quote
from src.report_generator import build_report, save_report
from src.trip import Leg, Trip
from src.upgrade_rules import classify_fare_class, load_chart, load_settings


def _families():
    return ["Standard", "Up"]


def main():
    st.set_page_config(page_title="EVA Upgrade Decision", page_icon="✈",
                       layout="wide")
    chart = load_chart()
    try:
        settings = load_settings()
    except FileNotFoundError:
        settings = {}

    st.title("EVA Air — Upgrade Decision")
    st.caption("Paste what you see in your own browser. No login, no scraping, "
               "no credentials stored. ExpertFlyer = third-party clue only.")

    # ---------------- Sidebar: trip + money ----------------
    sb = st.sidebar
    sb.header("Trip")
    trip_type = sb.radio("Type", ["Round-trip", "One-way", "Multi-city"])
    passengers = sb.number_input("Passengers", 1, 9,
                                 int(settings.get("default_passengers", 2)))

    legs = []
    if trip_type == "One-way":
        o = sb.text_input("From", "TPE").upper()
        d = sb.text_input("To", "ORD").upper()
        legs = [Leg(o, d)]
        trip = Trip("one_way", legs, passengers)
    elif trip_type == "Round-trip":
        o = sb.text_input("From", "TPE").upper()
        d = sb.text_input("To", "ORD").upper()
        legs = [Leg(o, d), Leg(d, o)]
        trip = Trip("round_trip", legs, passengers)
    else:
        n = sb.number_input("Number of legs", 2, 8, 2)
        for i in range(int(n)):
            c1, c2 = sb.columns(2)
            o = c1.text_input(f"Leg {i+1} from", "TPE" if i == 0 else "",
                              key=f"o{i}").upper()
            d = c2.text_input(f"Leg {i+1} to", "ORD" if i == 0 else "",
                              key=f"d{i}").upper()
            if o and d:
                legs.append(Leg(o, d))
        trip = Trip("multi_city", legs, passengers)

    sb.header("Money")
    currency = sb.selectbox("Currency", ["TWD", "USD"], 0)
    mv_default = settings.get("eva_mile_value", {}).get(
        currency, 0.8 if currency == "TWD" else 0.025)
    mile_value = sb.number_input(f"Your mile value ({currency}/mile)", 0.0,
                                 value=float(mv_default), step=0.01,
                                 format="%.4f")

    # ---------------- Paste boxes ----------------
    st.subheader("Paste your EVA quotes")
    cE, cP = st.columns(2)
    with cE:
        eco_text = st.text_area("Economy quote (copied from EVA site)",
                                height=140, key="eco_q")
        pe_eco = parse_fare_quote(eco_text)
        eco_family = st.selectbox(
            "Economy family", _families(),
            index=(1 if (pe_eco.fare_family or "").lower() == "up" else 0))
        eco_price = st.number_input(
            f"Economy total price ({currency})", 0.0,
            value=float(pe_eco.price or 0.0), step=1000.0)
        eco_fc = st.text_input("Economy fare class",
                               value=pe_eco.fare_class or "")
        for w in pe_eco.warnings:
            st.caption(f"⚠ {w}")
    with cP:
        pe_text = st.text_area("Premium Economy quote (copied from EVA site)",
                               height=140, key="pe_q")
        pe_pe = parse_fare_quote(pe_text)
        pe_family = st.selectbox(
            "Premium Economy family", _families(),
            index=(1 if (pe_pe.fare_family or "").lower() == "up" else 0))
        pe_price = st.number_input(
            f"Premium Economy total price ({currency})", 0.0,
            value=float(pe_pe.price or 0.0), step=1000.0)
        pe_fc = st.text_input("Premium Economy fare class",
                              value=pe_pe.fare_class or "")
        for w in pe_pe.warnings:
            st.caption(f"⚠ {w}")

    # ---------------- ExpertFlyer paste ----------------
    st.subheader("Paste ExpertFlyer text (optional)")
    ef_text = st.text_area("Copied ExpertFlyer flight / availability text",
                           height=120, key="ef_q")
    parsed_ef = parse_expertflyer(ef_text) if ef_text.strip() else None
    official_confirmed = st.checkbox(
        "I have OFFICIAL EVA upgrade confirmation (manual)")
    official_waitlist = st.checkbox(
        "EVA says upgrade is waitlistable (manual)")

    ef_clue = None
    if parsed_ef:
        ef_clue = parsed_ef.suggested_clue
        st.info(f"Parsed ExpertFlyer → flight {parsed_ef.flight_number}, "
                f"aircraft {parsed_ef.aircraft}, suggested clue "
                f"**{parsed_ef.suggested_clue}**. {parsed_ef.notes}")
        for w in parsed_ef.warnings:
            st.caption(f"⚠ {w}")
        if st.button("Save this ExpertFlyer check"):
            chk = ExpertFlyerCheck(
                route=legs[-1].code() if legs else "",
                date="", airline="BR",
                flight_number=parsed_ef.flight_number or "",
                aircraft=parsed_ef.aircraft or "",
                scheduled_departure=parsed_ef.departure or "",
                scheduled_arrival=parsed_ef.arrival or "",
                fare_bucket_notes=", ".join(parsed_ef.business_buckets),
                confidence_clue=parsed_ef.suggested_clue,
                notes=parsed_ef.notes, source="ExpertFlyer")
            p = expertflyer_input.save(chk)
            st.success(f"Saved {p}")

    # ---------------- Compute ----------------
    inp = ComparisonInput(
        trip=trip, economy_price=float(eco_price),
        premium_economy_price=float(pe_price), currency=currency,
        economy_family=eco_family, premium_family=pe_family,
        mile_value=float(mile_value))
    result = compare(inp, chart=chart)

    # Verdict + 3 numbers headline
    st.markdown("---")
    color = "red" if "Cannot" in result.recommendation or \
        "ECONOMY" in result.recommendation.upper() and "PREMIUM" not in \
        result.recommendation.upper() else \
        ("green" if "PREMIUM" in result.recommendation.upper() else "orange")
    st.markdown(f"# :{color}[{result.recommendation}]")
    st.write(result.reasoning)
    if not result.blocked:
        m1, m2, m3 = st.columns(3)
        m1.metric("Cash upcharge",
                  f"{result.cash_upcharge:,.0f} {currency}")
        m2.metric("Miles saved (total)",
                  f"{result.miles_saved_total:,}")
        m3.metric("Cost / saved mile",
                  "n/a" if result.implied_cost_per_saved_mile is None
                  else f"{result.implied_cost_per_saved_mile:.3f} {currency}",
                  delta=f"vs {mile_value} you value",
                  delta_color="off")
    st.markdown("---")

    # Eligibility check on the fare classes typed/parsed
    cc1, cc2 = st.columns(2)
    for col, label, fc_val in ((cc1, "Economy", eco_fc),
                               (cc2, "Premium Economy", pe_fc)):
        with col:
            if fc_val.strip():
                fc = classify_fare_class(chart, fc_val)
                (st.success if fc.upgradeable else st.error)(
                    f"{label} class {fc.fare_class}: {fc.reason}")

    # Confidence (use Premium Economy fare class as the upgrade target)
    confidence = None
    if pe_fc.strip():
        fcinfo = classify_fare_class(chart, pe_fc)
        confidence = assess(fcinfo, official_confirmed=official_confirmed,
                            official_waitlist=official_waitlist,
                            expertflyer_clue=ef_clue)
        cmap = {"High": "green", "Medium": "orange", "Low": "gray",
                "Do Not Buy": "red"}
        st.markdown(f"**Upgrade confidence:** "
                    f":{cmap.get(confidence.level,'gray')}[{confidence.level}]"
                    f" — {confidence.reasoning}")

    # Per-leg mileage table
    if result.economy.legs:
        rows = []
        for e, p in zip(result.economy.legs, result.premium.legs):
            rows.append({
                "Leg": f"{e.origin}-{e.destination}",
                "Region pair": f"{e.origin_region} ↔ {e.destination_region}"
                if e.origin_region and e.destination_region else "unknown",
                "Economy /pp": e.miles if e.status == "ok" else e.status,
                "Premium /pp": p.miles if p.status == "ok" else p.status,
            })
        st.table(rows)

    if result.blocked:
        st.error("Unverified chart legs — confirm with EVA and add to "
                 "config/eva_upgrade_chart.yaml:")
        for n in result.block_notes:
            st.write(f"- {n}")

    st.warning(
        "Aircraft & seat maps change. Seat-map ≠ upgrade availability. "
        "Paid Business ≠ mileage upgrade inventory. ExpertFlyer never "
        "confirms EVA upgrade space. P / A / V / W / S = not upgradeable.")

    md = build_report(result, ef_check=None, confidence=confidence)
    st.download_button("Download Markdown report", md,
                       file_name="eva_upgrade_report.md",
                       mime="text/markdown")
    if st.button("Save report to reports/"):
        st.success(f"Saved {save_report(md)}")


if __name__ == "__main__":
    main()
