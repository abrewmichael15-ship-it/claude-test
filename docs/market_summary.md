# Reading-metro owner base — market summary

Based on `data/processed/prospects.csv` (30,616 single-family parcels
across Reading, West Reading, Wyomissing, Shillington, Kenhorst, and Cumru
Township), generated from the Berks County CAMA Residential extract on
2026-09-04. Re-run `scripts/build_pipeline.py` and regenerate this summary
each quarter for a fresh read.

## Tenure distribution

| Years owned | Parcels |
|---|---|
| 0-2 | 3,628 |
| 2-5 | 5,355 |
| 5-8 | 4,734 |
| 8-10 | 2,380 |
| 10-15 | 3,671 |
| 15-20 | 2,981 |
| 20-30 | 4,657 |
| 30-50 | 1,837 |
| 50+ | 326 |
| *(no sale on record)* | 1,043 |

**Median tenure: 8.9 years.** The 8-20yr "sweet spot" your scoring
hypothesis targets covers **9,032 parcels** (~30% of the footprint) - a
sizeable target list on its own. The next-largest band is 20-30 years
(4,657 parcels), which is why the scoring config tapers rather than
zeroes out tenure credit past 20 years, rather than treating the sweet
spot as a hard cutoff.

## Absentee rate by municipality

(Absentee here = not homestead-enrolled, or out-of-state mailing address,
or an entity-style owner name - see README methodology notes. "ZIP" wasn't
usable since situs ZIP isn't reliably populated in the county dataset,
so this is broken out by municipality instead.)

| Municipality | Parcels | Absentee rate | Homestead-enrolled rate | Entity-owner rate |
|---|---|---|---|---|
| Reading (city) | 19,215 | 62.0% | 38.6% | 11.5% |
| West Reading | 1,240 | 61.3% | 40.8% | 14.0% |
| Shillington | 1,879 | 48.2% | 52.6% | 4.4% |
| Kenhorst | 1,157 | 47.4% | 54.7% | 6.0% |
| Wyomissing | 3,077 | 40.8% | 61.2% | 5.5% |
| Cumru Township | 4,048 | 38.8% | 62.9% | 4.2% |

**Reading and West Reading run notably higher absentee and entity-owner
rates than the inner-ring boroughs/township** - consistent with denser,
older rental stock closer to the urban core. Overall absentee rate across
the full footprint: **55.4%**; overall entity-owner rate: **9.4%**.
Worth noting: this flag will include some genuine owner-occupants who
simply never filed for the homestead exclusion, so treat the municipality
gap as directional, not a precise absentee count.

## Violation concentration

**Not available.** No public database of open code violations or rental
registrations was found for the City of Reading or the target boroughs
(see `docs/data_sources.md`) - this section stays blank until that data
exists, via a Right-to-Know request or a confirmed public search endpoint.

## Other notable figures

- **Recently sold (<3 yrs):** 16.6% of the footprint (5,075 parcels) -
  these score low by design (strong negative signal) since a household
  that just moved in is unlikely to sell again within 12 months.
- **Tax delinquent / upset sale:** 44 parcels currently matched to the
  2025 upset-sale list within the target footprint - a small, high-signal
  distress pool worth prioritizing regardless of overall score.
- **Median year built: 1920** (mean 1927, range 1700-2025) - an old
  housing stock overall, consistent with Reading's rowhome-heavy core.
