# plane-upgrade

Local Python tool to compare EVA Air Economy vs Premium Economy when the goal
is to use **Infinity MileageLands** miles to upgrade to Business / Royal Laurel.

The tool constantly answers:

> "How much extra cash am I paying to save EVA miles by buying Premium Economy
> instead of Economy, and is that a good deal?"

## Constraints (read before using)

- This tool **does not buy tickets** and never will.
- No login automation, no captcha bypass, no rate-limit evasion.
- ExpertFlyer is treated as a **third-party clue** only — never as official
  EVA upgrade confirmation. Manual entry only in v1.
- Seat map availability is **not** the same as mileage upgrade availability.
- Paid Business inventory is **not** the same as mileage upgrade inventory.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run tests

```bash
pytest
```

## CLI

All commands are run as `python -m src.cli <command>`.

### 1. Compare Economy Standard vs Premium Economy Standard

```bash
python -m src.cli compare \
  --routes TPE-ORD LAX-TPE \
  --passengers 2 \
  --economy-price 55000 \
  --premium-economy-price 80000 \
  --currency TWD \
  --economy-family standard \
  --premium-family standard \
  --mile-value 0.8
```

Prices are interpreted as **total booking cost** (all passengers, all legs)
in the same currency as `--mile-value`.

### 2. Compare Up fares

```bash
python -m src.cli compare \
  --routes TPE-ORD LAX-TPE \
  --passengers 2 \
  --economy-price 70000 \
  --premium-economy-price 95000 \
  --currency TWD \
  --economy-family up \
  --premium-family up \
  --mile-value 0.8
```

### 3. Check fare class eligibility

```bash
python -m src.cli eligibility --route TPE-ORD --fare-class L
```

### 4. Add manual ExpertFlyer check

```bash
python -m src.cli add-expertflyer-check \
  --route LAX-TPE \
  --date 2026-06-23 \
  --airline BR \
  --flight-number BR15 \
  --aircraft "Boeing 777-300ER" \
  --departure "00:50" \
  --arrival "05:20+1" \
  --business-seatmap-notes "Several unassigned Royal Laurel seats visible" \
  --premium-seatmap-notes "Premium Economy has multiple unassigned seats" \
  --fare-bucket-notes "Manual ExpertFlyer fare-bucket notes entered by user" \
  --confidence-clue strong \
  --screenshot-path "data/screenshots/br15_expertflyer.png" \
  --notes "Seat map only. Not official EVA upgrade inventory."
```

### 5. Generate report

```bash
python -m src.cli report \
  --routes TPE-ORD LAX-TPE \
  --passengers 2 \
  --economy-price 55000 \
  --premium-economy-price 80000 \
  --currency TWD \
  --economy-family standard \
  --premium-family standard \
  --mile-value 0.8 \
  --include-latest-expertflyer
```

Add `--fare-class L` to drive confidence scoring, and any of
`--official-confirmed`, `--official-waitlist`, `--seatmap-only` for manual
inputs.

## EVA upgrade chart (v1)

| Route   | Fare family             | Fare classes | Miles to Business |
|---------|-------------------------|--------------|------------------:|
| TPE-ORD | Economy Standard        | Q / H / M    | 70,000            |
| TPE-ORD | Economy Up              | B / Y        | 58,500            |
| TPE-ORD | Premium Economy Standard| L / T        | 40,000            |
| TPE-ORD | Premium Economy Up      | K            | 36,000            |
| LAX-TPE | Economy Standard        | Q / H / M    | 60,000            |
| LAX-TPE | Economy Up              | B / Y        | 50,000            |
| LAX-TPE | Premium Economy Standard| L / T        | 35,000            |
| LAX-TPE | Premium Economy Up      | K            | 31,500            |

**Non-upgradeable:** Economy Discount/Basic A/V/W/S; Premium Economy Basic P.

## Folder layout

```
config/eva_upgrade_chart.yaml   upgrade chart by route + bucket
config/settings.yaml            defaults, mile valuations, confidence rules
src/upgrade_rules.py            eligibility + miles lookup
src/fare_compare.py             cash-vs-miles comparison
src/confidence.py               confidence scoring
src/expertflyer_input.py        manual ExpertFlyer persistence
src/report_generator.py         Markdown report
src/cli.py                      argparse CLI
data/                           fare_checks.csv, expertflyer_checks.csv, checks/
reports/                        Markdown reports
tests/                          pytest tests
```

## Future (not built yet)

A Streamlit dashboard could later wrap the same `src/` modules to provide
sliders for mile valuation, a side-by-side comparison view, and ExpertFlyer
log browsing. It is intentionally **not** implemented in v1 — the CLI works
first.
