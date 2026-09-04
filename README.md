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
  needs a manual export / Right-to-Know request. **Waiting on raw files** to
  be dropped in `./data/raw` before Phase 2 starts.
- [ ] **Phase 2 — Pipeline.** Normalize/dedupe parcels, flag absentee owners,
  compute tenure and equity proxy, join violations/delinquency.
- [ ] **Phase 3 — Scoring.** Transparent, weighted 0–100 propensity score,
  fully configurable.
- [ ] **Phase 4 — Output.** Top 500 ranked + tiered CSV, Follow Up Boss field
  mapping, market summary.

## Layout

```
data/
  raw/         # source files you drop in (CAMA extracts, tax sale lists, etc.) — gitignored
  processed/   # pipeline output (prospects.csv, etc.) — gitignored
docs/
  data_sources.md   # Phase 1 inventory
```

## Re-running this quarterly

Once Phase 2+ lands, this section will document: which raw files to
re-download each quarter, how to refresh the REST-sourced parcel data, and
how to re-run the pipeline and scoring config. Left as a placeholder until
there's a pipeline to describe.
