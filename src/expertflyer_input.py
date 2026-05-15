"""Persist manual ExpertFlyer checks to JSON + CSV history."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from .models import ExpertFlyerCheck

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CHECKS_DIR = DATA_DIR / "checks"
CSV_PATH = DATA_DIR / "expertflyer_checks.csv"


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHECKS_DIR.mkdir(parents=True, exist_ok=True)


def save(check: ExpertFlyerCheck) -> Path:
    """Write the check as a timestamped JSON file and append to CSV history."""
    _ensure_dirs()
    stamp = check.checked_at.replace(":", "-")
    fname = f"ef_{check.flight_number}_{check.date}_{stamp}.json"
    json_path = CHECKS_DIR / fname
    json_path.write_text(json.dumps(asdict(check), indent=2))

    row = asdict(check)
    write_header = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return json_path


def load_all() -> List[ExpertFlyerCheck]:
    if not CHECKS_DIR.exists():
        return []
    checks: List[ExpertFlyerCheck] = []
    for p in sorted(CHECKS_DIR.glob("ef_*.json")):
        try:
            data = json.loads(p.read_text())
            checks.append(ExpertFlyerCheck(**data))
        except (json.JSONDecodeError, TypeError):
            continue
    return checks


def latest_for_route(route: str) -> Optional[ExpertFlyerCheck]:
    matches = [c for c in load_all() if c.route == route]
    if not matches:
        return None
    return max(matches, key=lambda c: c.checked_at)


def latest_any() -> Optional[ExpertFlyerCheck]:
    checks = load_all()
    if not checks:
        return None
    return max(checks, key=lambda c: c.checked_at)
