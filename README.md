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
- [ ] **Still needs you:** code violations / rental registrations (no public
  database found — needs a Right-to-Know request, or confirmation that
  Reading Self-Serve has a public case search), and the county appreciation
  factor for the equity-proxy calculation.
- [ ] **Phase 2 — Pipeline.** Normalize/dedupe parcels, flag absentee owners,
  compute tenure and equity proxy, join violations/delinquency.
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

1. `python3 scripts/fetch_parcels.py` — refreshes `data/raw/berks_cama_residential.csv`
   from the live county REST API (takes ~1-2 min, ~45k rows).
2. Manually re-download the current Upset Sale list and Repository list PDFs
   from `berkspa.gov/departments/tax-claim-bureau` into `data/raw/` (the file
   URL changes each cycle and isn't discoverable via an API).
3. If you've gotten violation/rental-registration data via a Right-to-Know
   request, drop the export into `data/raw/`.
4. (Once Phase 2 lands) re-run the pipeline script to regenerate
   `data/processed/prospects.csv`.
