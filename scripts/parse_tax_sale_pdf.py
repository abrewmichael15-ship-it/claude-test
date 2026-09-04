#!/usr/bin/env python3
"""
Extract parcel IDs for the target Reading-metro municipalities from the
Berks County Tax Claim Bureau's Upset Sale list and Repository list PDFs
(both hand-downloaded into ./data/raw - the county doesn't publish a
stable/discoverable URL for these, so re-downloading them each cycle is a
manual step; see docs/data_sources.md).

We deliberately do NOT try to re-parse owner name / address / municipality
out of the PDF text - column boundaries are lost once extracted as plain
text, so free-form name and address fields are unreliable to split back
apart. Instead we pull just the parcel ID (which matches the CAMA PARID
format exactly) and the dollar figures, then join everything else back to
the authoritative CAMA extract by PARID in the main pipeline.

Output: data/raw/tax_sale_delinquent_parcels.csv
Columns: parid, source (upset_sale|repository), assessed_value, bid_amount
"""
import csv
import re
import sys
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_FILE = RAW_DIR / "tax_sale_delinquent_parcels.csv"

TARGET_MUNI_MATCHES = [
    "CITY OF READING",
    "CUMRU TWP",
    "CUMRU TOWNSHIP",
    "KENHORST BORO",
    "SHILLINGTON BORO",
    "WEST READING BORO",
    "WYOMISSING BORO",
]

PARID_RE = re.compile(r"^(\d{10,20}[A-Z]?\d{0,3})\s+(.*)$")
MONEY_RE = re.compile(r"\$\s*([\d,]+\.\d{2})")


def parse_pdf(path, source_label):
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                if not any(m in line for m in TARGET_MUNI_MATCHES):
                    continue
                m = PARID_RE.match(line.strip())
                if not m:
                    continue
                parid, rest = m.groups()
                amounts = MONEY_RE.findall(rest)
                if not amounts:
                    continue
                assessed_value = amounts[0].replace(",", "")
                bid_amount = amounts[-1].replace(",", "")
                rows.append(
                    {
                        "parid": parid,
                        "source": source_label,
                        "assessed_value": assessed_value,
                        "bid_amount": bid_amount,
                    }
                )
    return rows


def main():
    all_rows = []
    upset_pdfs = sorted(RAW_DIR.glob("tax_claim_upset_sale*.pdf"))
    repo_pdfs = sorted(RAW_DIR.glob("tax_claim_repository_list*.pdf"))

    for p in upset_pdfs:
        rows = parse_pdf(p, "upset_sale")
        print(f"  {p.name}: {len(rows)} target-municipality rows")
        all_rows.extend(rows)
    for p in repo_pdfs:
        rows = parse_pdf(p, "repository")
        print(f"  {p.name}: {len(rows)} target-municipality rows")
        all_rows.extend(rows)

    if not all_rows:
        print(
            "No tax sale PDFs found in data/raw (expected "
            "tax_claim_upset_sale*.pdf / tax_claim_repository_list*.pdf) "
            "or no target-municipality rows matched. Skipping.",
            file=sys.stderr,
        )
        return

    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["parid", "source", "assessed_value", "bid_amount"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()
