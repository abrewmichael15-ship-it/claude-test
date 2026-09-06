#!/usr/bin/env python3
"""
Phase 4c: reshape data/processed/fub_import_ready.csv into a Click2Mail
mail-merge upload - alphanumeric/underscore-only headers (Click2Mail's
stated requirement) and address fields split the way USPS CASS
standardization expects (separate street/city/state/zip, not a combined
string).

Column names aren't a fixed Click2Mail spec (their upload screen maps
your headers to merge fields yourself, same as FUB) - these are just
clear, conventional names. Verify against the actual upload/mapping
screen before your first real print run.

Writes: data/processed/click2mail_mailmerge.csv
"""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
IN_CSV = PROCESSED_DIR / "fub_import_ready.csv"
OUT_CSV = PROCESSED_DIR / "click2mail_mailmerge.csv"


def main():
    if not IN_CSV.exists():
        raise SystemExit(f"Missing {IN_CSV} - run make_fub_import.py first.")

    df = pd.read_csv(IN_CSV, dtype=str)

    out = pd.DataFrame()
    out["Recipient_Name"] = df["Company"]  # see docs/fub_field_mapping.md re: not auto-splitting names
    out["Address_Line_1"] = df["Street Address"]
    out["City"] = df["City"]
    out["State"] = df["State"]
    out["Zip"] = df["Zip"].apply(lambda z: str(z).zfill(5) if pd.notna(z) else "")
    out["Tier"] = df["Tier"]
    out["Property_Address"] = df["Property Address"]
    out["Tax_Delinquent"] = df["Tax Delinquent"]

    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(out)} rows to {OUT_CSV}")
    print()
    print("Split by tier (mail cadence differs by tier - see README/marketing plan):")
    print(out["Tier"].value_counts())


if __name__ == "__main__":
    main()
