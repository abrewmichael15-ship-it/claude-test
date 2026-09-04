#!/usr/bin/env python3
"""
Phase 2 pipeline: turn the raw Berks County CAMA Residential extract into
a normalized, deduped, scored-ready prospect list.

Reads:
  data/raw/berks_cama_residential.csv          (required; scripts/fetch_parcels.py)
  data/raw/tax_sale_delinquent_parcels.csv      (optional; scripts/parse_tax_sale_pdf.py)
  reference/luc_single_family_codes.csv
  reference/target_municipalities.csv
  config/pipeline_config.json

Writes:
  data/processed/staging.db     (SQLite staging - filtered/deduped raw rows)
  data/processed/prospects.csv  (normalized + derived fields, NOT yet scored - see Phase 3)

Fields this pipeline deliberately leaves null (no data available / no
config value supplied) rather than estimate:
  - equity_proxy, estimated_current_value  (need config.appreciation_factor_annual)
  - open_violation_count, has_open_violation, is_registered_rental (no public
    violations/rental-registration data source found - see docs/data_sources.md)
"""
import csv
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import usaddress

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REFERENCE_DIR = REPO_ROOT / "reference"
CONFIG_PATH = REPO_ROOT / "config" / "pipeline_config.json"

CAMA_FILE = RAW_DIR / "berks_cama_residential.csv"
DELINQUENT_FILE = RAW_DIR / "tax_sale_delinquent_parcels.csv"
STAGING_DB = PROCESSED_DIR / "staging.db"
OUT_CSV = PROCESSED_DIR / "prospects.csv"

ENTITY_KEYWORDS = [
    "LLC", "L L C", "INC", "L P", "LP", "TRUST", "TR ", " CO ", "CORP",
    "PARTNERS", "PROPERTIES", "REALTY", "HOLDINGS", "ASSOCIATES", "ESTATE",
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_single_family_codes():
    codes = set()
    with open(REFERENCE_DIR / "luc_single_family_codes.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row["include_as_single_family"].strip().upper() == "TRUE":
                base = row["luc_base_code"].strip()
                if "-" not in base:  # skip range placeholder rows (122-141, 2001-2713)
                    codes.add(base)
    return codes


def load_muni_names():
    names = {}
    with open(REFERENCE_DIR / "target_municipalities.csv", newline="") as f:
        for row in csv.DictReader(f):
            names[row["muni_code"].strip()] = row["municipality_name"].strip()
    return names


def luc_base(luc):
    if not luc:
        return None
    m = re.match(r"^(\d+)", str(luc))
    return m.group(1) if m else None


def is_entity_owner(name):
    if not name or (isinstance(name, float) and pd.isna(name)):
        return False
    name_u = name.upper()
    return any(kw in name_u for kw in ENTITY_KEYWORDS)


def normalize_mailing_address(mailing_str):
    """Parse the free-text MAILING street line with usaddress. Returns
    (normalized_street, parse_type) - parse_type is usaddress's tag
    ('Street Address' vs 'Ambiguous' etc.) so downstream users can see
    when normalization is low-confidence rather than trusting it blindly.
    """
    if not mailing_str or not str(mailing_str).strip():
        return None, None
    try:
        tagged, addr_type = usaddress.tag(str(mailing_str))
        parts = []
        for key in (
            "AddressNumber", "StreetNamePreDirectional", "StreetName",
            "StreetNamePostType", "StreetNamePostDirectional",
            "OccupancyType", "OccupancyIdentifier",
        ):
            if key in tagged:
                parts.append(tagged[key])
        normalized = " ".join(parts) if parts else str(mailing_str).strip()
        return normalized, addr_type
    except usaddress.RepeatedLabelError:
        return str(mailing_str).strip(), "Ambiguous"


def build_situs_address(row):
    parts = [row.get("ADRNO"), row.get("ADRDIR"), row.get("ADRSTR"), row.get("ADRSUF")]
    parts = [str(p).strip() for p in parts if p not in (None, "", "nan")]
    return " ".join(parts) if parts else None


def main():
    if not CAMA_FILE.exists():
        raise SystemExit(f"Missing {CAMA_FILE} - run scripts/fetch_parcels.py first.")

    config = load_config()
    sf_codes = load_single_family_codes()
    muni_names = load_muni_names()

    print("Loading CAMA extract...")
    df = pd.read_csv(CAMA_FILE, dtype=str, keep_default_na=False, na_values=[""])
    string_cols = [
        "OWN1", "OWN2", "MAILING", "CITYNAME", "STATECODE", "ZIP1", "ADRNO",
        "ADRDIR", "ADRSTR", "ADRSUF", "HOMESTEAD", "SALEDT", "LUC", "CARD",
    ]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna("")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # --- stage raw filtered rows in SQLite, before any Python-side dedup/derivation ---
    print("Staging raw filtered rows in SQLite...")
    conn = sqlite3.connect(STAGING_DB)
    df.to_sql("cama_raw", conn, if_exists="replace", index=False)

    # --- filter: residential class + single-family land use code ---
    df["luc_base"] = df["LUC"].apply(luc_base)
    is_single_family = (df["CLASS"] == "R") & (df["luc_base"].isin(sf_codes))
    sf_df = df[is_single_family].copy()
    print(f"  {len(df)} total rows -> {len(sf_df)} single-family rows (CLASS=R, LUC single-family)")

    # --- dedupe by parcel (PARID): prefer CARD == '1' (primary card) ---
    sf_df["_card_sort"] = sf_df["CARD"].apply(lambda c: 0 if c == "1" else (1 if c else 2))
    sf_df = sf_df.sort_values(["PARID", "_card_sort"])
    deduped = sf_df.drop_duplicates(subset=["PARID"], keep="first").drop(columns=["_card_sort"])
    print(f"  {len(sf_df)} rows -> {len(deduped)} after dedup by PARID (kept primary card)")

    deduped.to_sql("cama_single_family_deduped", conn, if_exists="replace", index=False)

    # --- normalize addresses ---
    print("Normalizing addresses...")
    deduped["situs_address"] = deduped.apply(build_situs_address, axis=1)
    deduped["municipality"] = deduped["MUNI"].map(muni_names)

    mailing_normalized = deduped["MAILING"].apply(normalize_mailing_address)
    deduped["mailing_address_normalized"] = mailing_normalized.apply(lambda t: t[0])
    deduped["mailing_address_parse_type"] = mailing_normalized.apply(lambda t: t[1])
    deduped["mailing_full"] = (
        deduped["mailing_address_normalized"].fillna(deduped["MAILING"]).fillna("") + ", "
        + deduped["CITYNAME"].fillna("") + ", "
        + deduped["STATECODE"].fillna("") + " "
        + deduped["ZIP1"].fillna("")
    ).str.strip(", ")

    # --- owner-occupancy / absentee signal ---
    # Primary signal: HOMESTEAD exclusion status - a legal certification of
    # primary residence under PA's Homestead Act, not a heuristic.
    # NOTE: this replaces the original mailing-ZIP-vs-situs-ZIP approach from
    # the spec - situs ZIP is not reliably populated in this county dataset,
    # while HOMESTEAD is a real, county-verified field. Flagged to the user
    # and approved before building this in.
    deduped["homestead_enrolled"] = deduped["HOMESTEAD"].fillna("").str.upper().str.startswith("ACCEPTED")
    deduped["mailing_out_of_state"] = deduped["STATECODE"].fillna("").str.upper() != "PA"
    deduped["owner_name_is_entity"] = deduped["OWN1"].apply(is_entity_owner)
    deduped["absentee_owner"] = (
        (~deduped["homestead_enrolled"]) | deduped["mailing_out_of_state"] | deduped["owner_name_is_entity"]
    )

    # --- tenure ---
    print("Computing tenure...")
    today = date.today()

    def parse_saledt(v):
        """scripts/fetch_parcels.py converts the source's epoch-millisecond
        Esri DATE field to an ISO date string at fetch time."""
        if not v:
            return None
        from datetime import datetime

        try:
            parsed = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            return None
        if parsed == date(1900, 1, 1):
            return None  # county's null-date sentinel value
        return parsed

    deduped["sale_date_parsed"] = deduped["SALEDT"].apply(parse_saledt)
    deduped["tenure_years"] = deduped["sale_date_parsed"].apply(
        lambda d: round((today - d).days / 365.25, 1) if d else None
    )
    recent_threshold = config.get("recent_sale_years_threshold", 3)
    deduped["recently_sold"] = deduped["tenure_years"].apply(
        lambda t: (t is not None) and (t < recent_threshold)
    )

    # --- equity proxy (requires config.appreciation_factor_annual - left null until supplied) ---
    appreciation_factor = config.get("appreciation_factor_annual")
    if appreciation_factor is not None:
        def equity_proxy(row):
            price = row.get("PRICE")
            tenure = row.get("tenure_years")
            total_value = row.get("TOTAL_VALUE")
            if not price or price in ("0", "") or tenure is None or not total_value:
                return None
            try:
                price = float(price)
                total_value = float(total_value)
            except (TypeError, ValueError):
                return None
            projected_value = price * ((1 + appreciation_factor) ** tenure)
            return round(projected_value - total_value, 2)

        deduped["estimated_current_value"] = deduped.apply(
            lambda r: round(float(r["PRICE"]) * ((1 + appreciation_factor) ** r["tenure_years"]), 2)
            if r.get("PRICE") and r.get("PRICE") not in ("0", "") and r.get("tenure_years") is not None
            else None,
            axis=1,
        )
        deduped["equity_proxy"] = deduped.apply(equity_proxy, axis=1)
    else:
        deduped["estimated_current_value"] = None
        deduped["equity_proxy"] = None
        print("  NOTE: config.appreciation_factor_annual is null - equity_proxy left null for all rows.")

    # --- tax delinquency / sheriff-sale join ---
    print("Joining tax delinquency / upset sale data...")
    if DELINQUENT_FILE.exists():
        delinq = pd.read_csv(DELINQUENT_FILE, dtype=str)
        delinq_parids = set(delinq["parid"])
        deduped["tax_delinquent_or_upset_sale"] = deduped["PARID"].isin(delinq_parids)
        matched = deduped["tax_delinquent_or_upset_sale"].sum()
        print(f"  matched {matched} of {len(delinq_parids)} delinquent-list parcels to CAMA parcels")
    else:
        deduped["tax_delinquent_or_upset_sale"] = None
        print(f"  {DELINQUENT_FILE} not found - run scripts/parse_tax_sale_pdf.py. Left null.")

    # --- violations / rental registration: no public data source found (see docs/data_sources.md) ---
    deduped["open_violation_count"] = None
    deduped["has_open_violation"] = None
    deduped["is_registered_rental"] = None

    # --- assemble output ---
    output_cols = {
        "PARID": "parcel_id",
        "OWN1": "owner_name_1",
        "OWN2": "owner_name_2",
        "situs_address": "situs_address",
        "municipality": "municipality",
        "mailing_address_normalized": "mailing_street",
        "CITYNAME": "mailing_city",
        "STATECODE": "mailing_state",
        "ZIP1": "mailing_zip",
        "mailing_full": "mailing_address_full",
        "mailing_address_parse_type": "mailing_address_parse_confidence",
        "homestead_enrolled": "homestead_enrolled",
        "absentee_owner": "absentee_owner",
        "owner_name_is_entity": "owner_name_is_entity",
        "sale_date_parsed": "last_sale_date",
        "PRICE": "last_sale_price",
        "tenure_years": "tenure_years",
        "recently_sold": "recently_sold",
        "LAND_VALUE": "assessed_land_value",
        "BLDG_VALUE": "assessed_building_value",
        "TOTAL_VALUE": "assessed_total_value",
        "estimated_current_value": "estimated_current_value",
        "equity_proxy": "equity_proxy",
        "LUC": "land_use_code",
        "YRBLT": "year_built",
        "BEDROOMS": "bedrooms",
        "FULLBATHS": "full_baths",
        "HALFBATHS": "half_baths",
        "SFLA": "living_area_sqft",
        "tax_delinquent_or_upset_sale": "tax_delinquent_or_upset_sale",
        "open_violation_count": "open_violation_count",
        "has_open_violation": "has_open_violation",
        "is_registered_rental": "is_registered_rental",
    }
    out = deduped[list(output_cols.keys())].rename(columns=output_cols)

    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(out)} rows to {OUT_CSV}")

    conn.close()


if __name__ == "__main__":
    main()
