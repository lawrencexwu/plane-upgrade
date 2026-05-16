# plane-upgrade

Local Python tool to compare EVA Air Economy vs Premium Economy when the goal
is to use **Infinity MileageLands** miles to upgrade to Business / Royal Laurel.

It constantly answers:

> "How much extra cash am I paying to save EVA miles by buying Premium Economy
> instead of Economy, and is that a good deal?"

## Constraints (deliberate guardrails — read this)

- **Does not buy tickets.** Ever.
- **No login automation, no scraping, no captcha/rate-limit/paywall bypass.**
  EVA fare prices and ExpertFlyer data are *not* fetched automatically — there
  is no compliant way to do that, and a logged-in scraper risks getting your
  EVA / ExpertFlyer accounts banned. Instead you **paste** text you already see
  in your own browser and the tool parses it.
- **No credentials stored.**
- **ExpertFlyer is a third-party clue only** — never official EVA upgrade
  confirmation. Seat-map availability ≠ mileage upgrade availability. Paid
  Business inventory ≠ mileage upgrade inventory.
- **No guessed mileage.** Only region pairs marked `verified: true` in
  `config/eva_upgrade_chart.yaml` return a number. Anything else reports
  "chart not verified — confirm with EVA" instead of inventing a value.

## Install & test

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Dashboard (recommended)

```bash
streamlit run src/dashboard.py
```

Workflow:

1. Sidebar: pick **One-way / Round-trip / Multi-city**, type the airport
   codes, passengers, currency, your mile value.
2. **Paste** the Economy quote and the Premium Economy quote you see on the
   EVA site into the two boxes. The tool extracts price, fare class, cabin and
   family. Parsed values are pre-filled so you only correct what's wrong.
3. Optionally **paste** ExpertFlyer text — it's parsed into a confidence clue
   (never treated as official).
4. Read the headline: **VERDICT + cash upcharge + miles saved + cost/saved
   mile** vs your mile value, plus per-leg mileage, eligibility and confidence.
5. Download or save the Markdown report.

## Universal upgrade chart

`config/eva_upgrade_chart.yaml` is region-based: `airport → region`, then
`region-pair → upgrade miles` by cabin/family. Verified today:

| Region pair          | Eco Std | Eco Up | PE Std | PE Up |
|----------------------|--------:|-------:|-------:|------:|
| TW ↔ NA_HIGH (TPE-ORD…) | 70,000 | 58,500 | 40,000 | 36,000 |
| TW ↔ NA_LOW (LAX-TPE…)  | 60,000 | 50,000 | 35,000 | 31,500 |

To extend: add the airport under `airports`, add the confirmed region pair
under `upgrade_award` with `verified: true`. It works immediately and the
"cannot give a verdict" block clears for that route.

Non-upgradeable everywhere: Economy A/V/W/S, Premium Economy P.

## CLI

```bash
# Decision for your open-jaw trip
python -m src.cli compare --legs TPE-ORD LAX-TPE --passengers 2 \
  --economy-price 110000 --premium-economy-price 160000 \
  --currency TWD --mile-value 0.8

# Fare class eligibility
python -m src.cli eligibility --fare-class L --leg TPE-ORD

# Parse a pasted quote / ExpertFlyer block
python -m src.cli parse-fare --text "EVA BR55 TPE-ORD Premium Economy (L) Standard TWD 80,000"
python -m src.cli parse-expertflyer --stdin < ef.txt

# Full Markdown report
python -m src.cli report --legs TPE-ORD LAX-TPE --passengers 2 \
  --economy-price 110000 --premium-economy-price 160000 \
  --currency TWD --mile-value 0.8 \
  --fare-class L --include-latest-expertflyer
```

`--legs`: 1 pair = one-way, 2 = round-trip, 3+ = multi-city. Prices are the
**total booking cost** (all passengers, all legs).

## Layout

```
config/eva_upgrade_chart.yaml  region-based chart (verified flags)
config/settings.yaml           defaults, mile valuations
src/upgrade_rules.py           airport→region→miles, fare-class classify
src/trip.py                    one-way / round-trip / multi-city model
src/parsers.py                 paste-and-parse (fare quote, ExpertFlyer)
src/fare_compare.py            verdict + cash-vs-miles math
src/confidence.py              confidence scoring
src/expertflyer_input.py       manual ExpertFlyer JSON+CSV history
src/report_generator.py        Markdown report
src/cli.py                     argparse CLI
src/dashboard.py               Streamlit UI
tests/                         pytest (37 tests)
```
