# Reading, PA Prospect Scoring

A scored real-estate prospect list for Reading, PA (Berks County) and its
inner-ring boroughs, for owner-occupant and absentee-owner farming /
direct-mail outreach. Built for a licensed PA agent (RS372287), for personal
use — not a product for redistribution.

**Scope:** City of Reading, West Reading, Wyomissing, Shillington, Kenhorst,
and Cumru Township. Single-family properties only.

**Constraints:** free/public records only — no MLS data, no paid skip-trace,
no data invented or estimated in place of a missing field, nothing scraped
from behind a login or against a site's terms. Phone numbers are out of
scope; skip-tracing happens separately through a compliant vendor.

## Status

- [x] **Phase 1 — Data inventory.** See [`docs/data_sources.md`](docs/data_sources.md)
  for every source found, its format, and whether it's bulk-downloadable or
  needs a manual export / Right-to-Know request.
- [x] **Parcel data acquired.** Berks County's CAMA Residential extract turned
  out to be scriptable (public ArcGIS REST API, no login) — `scripts/fetch_parcels.py`
  pulls it directly into `./data/raw`. See the addendum at the bottom of
  `docs/data_sources.md`.
- [x] **Phase 2 — Pipeline.** `scripts/build_pipeline.py` filters to
  single-family (CLASS=R + single-family LUC), dedupes by parcel (keeps the
  primary CAMA "card"), normalizes addresses (`usaddress` for the mailing
  street), computes tenure from sale date, flags absentee owners, and joins
  the tax-delinquency/upset-sale list. Run it after `fetch_parcels.py` (and
  optionally `parse_tax_sale_pdf.py`) to produce `data/processed/prospects.csv`
  — currently **30,616 single-family parcels** across the 6 target
  municipalities. Read the "Phase 2 methodology notes" section below before
  trusting the absentee-owner and equity-proxy columns.
- [ ] **Still needs you:** code violations / rental registrations (no public
  database found — needs a Right-to-Know request, or confirmation that
  Reading Self-Serve has a public case search), and the county appreciation
  factor for the equity-proxy calculation (`config/pipeline_config.json` →
  `appreciation_factor_annual`, currently `null`).
- [ ] **Phase 3 — Scoring.** Transparent, weighted 0–100 propensity score,
  fully configurable.
- [ ] **Phase 4 — Output.** Top 500 ranked + tiered CSV, Follow Up Boss field
  mapping, market summary.

## Layout

```
data/
  raw/         # fetched/dropped source files (CAMA extract, tax sale PDFs) — gitignored
  processed/   # pipeline output (prospects.csv, etc.) — gitignored
reference/     # tracked: county data dictionary + code crosswalks the pipeline is built from
scripts/
  fetch_parcels.py   # re-pulls the CAMA Residential extract from the county's public REST API
docs/
  data_sources.md   # Phase 1 inventory + addendum on what's now fetched automatically
```

## Re-running this quarterly

1. `pip install -r requirements.txt` (pandas, usaddress, pdfplumber).
2. `python3 scripts/fetch_parcels.py` — refreshes `data/raw/berks_cama_residential.csv`
   from the live county REST API (takes ~1-2 min, ~45k rows).
3. Manually re-download the current Upset Sale list and Repository list PDFs
   from `berkspa.gov/departments/tax-claim-bureau` into `data/raw/` as
   `tax_claim_upset_sale_<year>.pdf` / `tax_claim_repository_list.pdf` (the
   file URL changes each cycle and isn't discoverable via an API), then run
   `python3 scripts/parse_tax_sale_pdf.py`.
4. If you've gotten violation/rental-registration data via a Right-to-Know
   request, drop the export into `data/raw/` (not yet wired into the
   pipeline — tell me the file's shape and I'll add the join).
5. `python3 scripts/build_pipeline.py` — regenerates `data/processed/prospects.csv`.

## Phase 2 methodology notes (read before trusting the output)

- **Single-family filter**: `CLASS='R'` and the land-use code's numeric
  prefix is in `reference/luc_single_family_codes.csv` (`include_as_single_family=TRUE`).
  Row homes are included (fee-simple attached, common in Reading); condos and
  true multi-family (2-4 unit) are excluded. Edit that CSV and re-run if you
  disagree with a call.
- **Absentee-owner flag deviates from the original spec.** Mailing-ZIP vs.
  situs-ZIP isn't usable — situs ZIP isn't reliably populated in this county
  dataset. Instead, `absentee_owner` is `NOT homestead_enrolled OR mailing
  address is out-of-state OR owner name looks like an entity (LLC/Inc/Trust)`.
  `homestead_enrolled` reflects PA's Homestead Exclusion, a real
  county-verified certification of primary residence — but the flip side is
  real too: some eligible owner-occupants never file for it, so
  `absentee_owner=True` will include some false positives. Treat it as a
  signal, not a certainty, when tuning Phase 3 weights.
- **Equity proxy is null for every row** until you set
  `appreciation_factor_annual` in `config/pipeline_config.json`.
- **Tax delinquency / upset-sale flag** only reflects parcels that already
  reached a scheduled county sale (44 of 30,616 rows currently) — it is
  *not* a general delinquency roster (none exists publicly; see
  `docs/data_sources.md`).
- **Violation / rental-registration columns are null for every row** — no
  public data source exists yet (see `docs/data_sources.md`).
- **Known data quirk**: 3 of 30,616 rows have a sale date recorded in the
  future (a county data-entry artifact), producing a negative `tenure_years`.
  Left as-is rather than silently "corrected" — they'll naturally score low
  in Phase 3 once that band-based tenure scoring exists.
