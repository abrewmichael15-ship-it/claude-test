#!/usr/bin/env python3
"""
Pull the Berks County CAMA Residential File for the target Reading-metro
municipalities directly from the county's public ArcGIS REST service
(no login, no scraping - documented bulk API) and write it to
./data/raw/berks_cama_residential.csv.

Source: https://opendata.berkspa.gov/ (Berks County Data Hub)
Service: Berks_Assessment_CAMA_Residential_File/FeatureServer/15
License: County of Berks GIS data - public, internal/personal use;
         not for redistribution/resale (see reference/CAMA_Data_Dictionary.pdf).

Re-run this quarterly to refresh data/raw/berks_cama_residential.csv.
"""
import csv
import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

SERVICE_URL = (
    "https://services3.arcgis.com/dGYe1jDYrTw1wwpc/arcgis/rest/services/"
    "Berks_Assessment_CAMA_Residential_File/FeatureServer/15/query"
)
PAGE_SIZE = 2000

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = REPO_ROOT / "reference"
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_FILE = RAW_DIR / "berks_cama_residential.csv"


def load_target_muni_codes():
    codes = []
    with open(REFERENCE_DIR / "target_municipalities.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row["in_scope"].strip().upper() == "TRUE":
                codes.append(row["muni_code"].strip())
    return codes


def fetch_page(where_clause, offset):
    params = {
        "where": where_clause,
        "outFields": "*",
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
    }
    url = f"{SERVICE_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.load(resp)


def main():
    import datetime

    muni_codes = load_target_muni_codes()
    quoted = ",".join(f"'{c}'" for c in muni_codes)
    where_clause = f"MUNI IN ({quoted})"

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = []
    fieldnames = None
    date_fields = set()
    offset = 0
    while True:
        data = fetch_page(where_clause, offset)
        if "error" in data:
            print(f"ArcGIS error: {data['error']}", file=sys.stderr)
            sys.exit(1)
        features = data.get("features", [])
        if not features:
            break
        if fieldnames is None:
            fieldnames = [f["name"] for f in data["fields"]]
            date_fields = {
                f["name"] for f in data["fields"] if f["type"] == "esriFieldTypeDate"
            }
        for feat in features:
            attrs = feat["attributes"]
            for field in date_fields:
                millis = attrs.get(field)
                if millis is not None:
                    attrs[field] = datetime.datetime.fromtimestamp(
                        millis / 1000, tz=datetime.timezone.utc
                    ).date().isoformat()
            all_rows.append(attrs)
        print(f"  fetched {len(all_rows)} rows so far (offset {offset})")
        if not data.get("exceededTransferLimit") and len(features) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if not all_rows:
        print("No rows returned - check MUNI codes / service availability.", file=sys.stderr)
        sys.exit(1)

    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()
