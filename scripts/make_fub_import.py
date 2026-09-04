#!/usr/bin/env python3
"""
Phase 4b: turn data/processed/top_500.csv into a file that needs zero
manual spreadsheet work before uploading to Follow Up Boss - correct
column names, tags already comma-separated (FUB splits on commas itself
in the import mapper), one row per contact.

Writes: data/processed/fub_import_ready.csv
"""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
IN_CSV = PROCESSED_DIR / "top_500.csv"
OUT_CSV = PROCESSED_DIR / "fub_import_ready.csv"


def main():
    if not IN_CSV.exists():
        raise SystemExit(f"Missing {IN_CSV} - run build_pipeline.py then score_prospects.py first.")

    df = pd.read_csv(IN_CSV)

    out = pd.DataFrame()

    # FUB requires a name - county records aren't "First Last", so these go
    # in as Company (see docs/fub_field_mapping.md for why).
    def company_name(row):
        n1 = str(row["owner_name_1"]).strip() if pd.notna(row["owner_name_1"]) else ""
        n2 = str(row["owner_name_2"]).strip() if pd.notna(row["owner_name_2"]) else ""
        return f"{n1} & {n2}" if n2 else n1

    out["Company"] = df.apply(company_name, axis=1)
    out["Street Address"] = df["mailing_street"]
    out["City"] = df["mailing_city"]
    out["State"] = df["mailing_state"]
    out["Zip"] = df["mailing_zip"].apply(
        lambda z: str(int(z)).zfill(5) if pd.notna(z) else ""
    )

    # FUB import maps a single delimited "Tags" column - comma is its
    # native separator, so swap the pipe delimiter used inside the repo.
    out["Tags"] = df["fub_tags"].str.replace("|", ",", regex=False)

    out["Source"] = "Reading Farm - " + df["municipality"].astype(str)
    out["Property Address"] = df["situs_address"].astype(str) + ", " + df["municipality"].astype(str) + ", PA"
    out["Propensity Score"] = df["propensity_score"]
    out["Tier"] = df["tier"]
    out["Parcel ID"] = df["parcel_id"]
    out["Tenure (years)"] = df["tenure_years"]
    out["Last Sale Date"] = df["last_sale_date"]
    out["Assessed Value"] = df["assessed_total_value"]
    out["Tax Delinquent"] = df["tax_delinquent_or_upset_sale"]

    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(out)} rows to {OUT_CSV}")
    print()
    print("Rows missing a mailing street (spot-check before mailing):")
    missing = df[df["mailing_street"].isna()][["parcel_id", "owner_name_1", "municipality"]]
    print(missing.to_string(index=False) if len(missing) else "  none")


if __name__ == "__main__":
    main()
