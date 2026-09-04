# Follow Up Boss import field mapping

Source file: `data/processed/top_500.csv` (regenerate with
`scripts/build_pipeline.py` then `scripts/score_prospects.py`).

## Column → Follow Up Boss field

| CSV column | FUB import field | Notes |
|---|---|---|
| `owner_name_1` | **Company** (recommended) or manually split into First/Last | County records store owner names as `LAST FIRST MIDDLE` (or `LAST FIRST & LAST2 FIRST2` for joint owners) - not `First Last`. I deliberately did **not** auto-split this into First/Last name fields: a wrong split silently misdirects a mail-merge greeting line, and county name formatting is inconsistent enough (suffixes, "C/O", multiple owners joined with `&`) that a parser would guess wrong often enough to be worse than flagging it for a quick manual pass. Recommendation: import as **Company** (safe, no parsing needed), or spot-check/split in a spreadsheet before import if you want "Dear [First Name]" mail-merge to work. |
| `owner_name_2` | (append to Company, or second contact) | Second owner on the deed, when present. |
| `mailing_address_full` | **Street Address / City / State / Zip** | Already combined; FUB's import mapper can also take the components separately - see `mailing_address_normalized`, `CITYNAME`/`STATECODE`/`ZIP1` if you'd rather map those individually (not currently split out into their own top_500.csv columns - tell me if you want that). |
| `mailing_address_parse_confidence` | *(don't import - QA only)* | `Street Address` = usaddress parsed cleanly. `Ambiguous`/blank = spot-check before mailing. |
| `situs_address` + `municipality` | **Property Address** (custom field, or "Address 2" if FUB supports a second address) | The property being farmed - distinct from the owner's mailing address for absentee owners. |
| `fub_tags` | **Tags** | Pipe-delimited (e.g. `tier-A|absentee|tax-delinquent`) - split on `|` when importing, or import as one tag string and use FUB's tag search. Always includes tier (`tier-A/B/C`) and occupancy (`absentee`/`owner-occupant`); conditionally includes `tax-delinquent` and `recently-sold`. |
| `tier` | **Tag** or custom field | Also embedded in `fub_tags`; broken out separately here in case you want it as its own filterable field instead of a tag. |
| `propensity_score` | **Custom field** (e.g. "Propensity Score") | 0-100. See README "Phase 3 scoring methodology" - the practical ceiling is currently 65, not 100, until the equity-proxy and violations weights go live. |
| `rank` | **Custom field** (optional) | Rank within the full scored population, not just the top 500. |
| `parcel_id` | **Custom field** ("Parcel ID / PARID") | Keep this - it's your join key back to the county record if you ever need to re-pull a property. |
| `last_sale_date`, `tenure_years`, `last_sale_price` | Custom fields (optional) | Useful context in the contact record for outreach talking points. |
| `year_built`, `bedrooms`, `full_baths`, `half_baths`, `living_area_sqft` | Custom fields (optional) | Property characteristics, handy for a personalized mailer. |
| `assessed_total_value` | Custom field (optional) | County assessed value - not market value. |
| `equity_proxy`, `estimated_current_value` | *(currently blank for every row)* | Will populate once `config/pipeline_config.json` → `appreciation_factor_annual` is set - re-run the pipeline + scoring after that and re-import. |
| `open_violation_count`, `has_open_violation`, `is_registered_rental` | *(currently blank for every row)* | No public data source found yet (see `docs/data_sources.md`). |
| `homestead_enrolled`, `owner_name_is_entity` | *(not imported - scoring inputs)* | Kept in the CSV for transparency/audit; fold into Tags yourself if useful. |

## Suggested FUB tag routing

Use the `tier-*` tag to drive your outreach cadence (e.g. Tier A → phone-first
once you've skip-traced, Tier B/C → mail-only to start), and `absentee` /
`owner-occupant` to pick your letter template. `tax-delinquent` and
`recently-sold` are worth a distinct, softer-touch sequence given the
different owner situation each implies.

## What's not in this file

No phone numbers, no email addresses, no MLS data - per your constraints,
those stay out of this pipeline entirely. Skip-trace the FUB-imported list
separately through your compliant vendor.
