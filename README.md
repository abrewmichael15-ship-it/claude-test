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
- [x] **Phase 3 — Scoring.** `scripts/score_prospects.py` applies a
  transparent, weighted 0–100 score from `config/scoring_config.json` — no
  black-box model, every component is plain arithmetic you can read and
  retune. See "Phase 3 scoring methodology" below for the reasoning behind
  each weight. **Ceiling is currently 65, not 100** — see the note there.
- [x] **Phase 4 — Output.** `data/processed/top_500.csv` (ranked, tiered
  A/B/C, tagged), [`docs/fub_field_mapping.md`](docs/fub_field_mapping.md)
  for the Follow Up Boss import, [`docs/market_summary.md`](docs/market_summary.md)
  for what the data shows about the owner base.
- [ ] **Still needs you:** code violations / rental registrations (no public
  database found — needs a Right-to-Know request, or confirmation that
  Reading Self-Serve has a public case search), and the county appreciation
  factor for the equity-proxy calculation (`config/pipeline_config.json` →
  `appreciation_factor_annual`, currently `null`). Both feed directly into
  the score once supplied — re-run `build_pipeline.py` then
  `score_prospects.py` after setting either.

## Layout

```
data/
  raw/         # fetched/dropped source files (CAMA extract, tax sale PDFs) — gitignored
  processed/   # pipeline + scoring output (prospects.csv, top_500.csv, etc.) — gitignored
reference/     # tracked: county data dictionary + code crosswalks the pipeline is built from
config/
  pipeline_config.json   # Phase 2 inputs (appreciation factor, tenure thresholds)
  scoring_config.json    # Phase 3 weights, tenure curve, tier cutoffs — tune freely
scripts/
  fetch_parcels.py       # pulls the CAMA Residential extract from the county's public REST API
  parse_tax_sale_pdf.py  # extracts target-municipality parcel IDs from the tax sale PDFs
  build_pipeline.py      # Phase 2: filter/dedupe/normalize/derive -> prospects.csv
  score_prospects.py     # Phase 3+4: weighted score, tiers, tags -> top_500.csv
docs/
  data_sources.md        # Phase 1 inventory + addendum on what's fetched automatically
  fub_field_mapping.md   # Phase 4: CSV column -> Follow Up Boss import field
  market_summary.md      # Phase 4: what the data shows about the owner base
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
6. `python3 scripts/score_prospects.py` — regenerates `data/processed/prospects_scored.csv`
   (everyone, scored) and `data/processed/top_500.csv` (Phase 4 deliverable:
   ranked, tiered, tagged).
7. Regenerate `docs/market_summary.md` off the new numbers if you want an
   updated read on the owner base (I'll do this on request, or you can ask
   me to automate it into the pipeline once the appreciation factor and
   violations data are both live and the numbers are worth re-narrating
   every quarter).

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
  Left as-is rather than silently "corrected" — they naturally score near
  the bottom of the tenure component either way.

## Phase 3 scoring methodology

All weights live in `config/scoring_config.json` — change a number, re-run
`score_prospects.py`, done. The formula is entirely transparent:

```
base_score = 35·tenure_component + 20·absentee_component
           + 25·equity_component + 20·violation_component
score      = clip(base_score − 30·recently_sold − (−10·tax_delinquent), 0, 100)
```

Each `_component` is a 0-1 value; `absentee`/`recently_sold`/`tax_delinquent`
are 0/1 booleans. Reasoning per input, and where I pushed back on the
starting hypothesis:

- **Tenure (weight 35, highest) — kept as your strongest signal, but not a
  hard 8-20yr cutoff.** The data backs the *direction*: 8-20yr owners are
  ~30% of the footprint (9,032 parcels), a real concentration. But 20-30yr
  tenure is nearly as large a band (4,657 parcels) and those owners are
  genuinely more likely to sell too (downsizing, estate transitions) — so
  the scoring curve ramps 0→1 from 2-8 years, holds at 1.0 through 20,
  then tapers to a 0.6 floor rather than dropping to 0. A hard cutoff at
  20 years would have thrown away a large, plausible chunk of your list
  for no evidence-based reason.
- **Absentee owner (weight 20) — kept as a strong positive, implemented via
  homestead status, not ZIP-matching** (see Phase 2 notes above for why).
  I did *not* raise this weight above 20 despite it being the single most
  common flag (55% of parcels): a signal present on the majority of your
  universe has less discriminating power than a rarer one, so weighting it
  higher would mostly just inflate everyone's score together rather than
  separate good prospects from average ones.
- **High equity proxy (weight 25) — currently inactive (contributes 0 to
  every row)** until you set `appreciation_factor_annual`. I kept the
  weight itself relatively high (second-highest) because equity is the
  most direct financial "can they afford to sell and buy again" signal of
  everything available — it's worth activating.
- **Open code violations (weight 20) — currently inactive**, same reason:
  no data source exists yet. Weighted on par with absentee since distress
  signals are typically strong sell predictors, but I can't back that with
  this dataset's numbers until the RTKL request (or a public search) comes
  through.
- **Tax delinquent — kept separate from the main weight budget, per your
  instruction**, as a flat `+10` bonus after the weighted score *and* its
  own `tax_delinquent_or_upset_sale` column/tag, so you can route it
  independently. Only 44 of 30,616 parcels currently match — small, but a
  genuinely high-signal distress pool given it means the county already
  scheduled a sale.
- **Recently sold <3yrs (weight −30, applied as a flat penalty, not a
  weighted component)** — a strong override rather than one input among
  several, because a household that just moved in is very unlikely to
  move again within your 12-month window regardless of how the other
  signals look. 16.6% of the footprint is currently in this band.

**Honest limitation:** none of this was backtested against actual outcomes
(there's no historical "which of these owners sold within 12 months" label
available from public records), so every weight above is *reasoned*, not
*validated*. Treat the ranking as a defensible starting prioritization, not
a calibrated probability — and once you've farmed a cycle or two and have
your own outcome data, that's the point where these weights could actually
be tuned against evidence rather than judgment.

**Score ceiling today is 65, not 100** (35 tenure + 20 absentee + 10
delinquent bonus, since equity and violations both contribute 0) — this
also means the top 500 has a lot of ties at the current maximum (55-65),
so today's ranking within a tie is arbitrary. Set the appreciation factor
and get violations data to unlock real score resolution.
