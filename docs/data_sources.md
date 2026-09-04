# Phase 1 — Data Source Inventory

> **Update (2026-09-04):** After the initial pass below, I found that the
> Berks County parcel/CAMA data is not just "bulk downloadable" but directly
> **scriptable** via a public ArcGIS REST/FeatureServer endpoint and a DCAT
> catalog that resolves straight to CSV/download URLs — no manual export
> needed. I pulled it programmatically; see the addendum at the bottom of
> this file for exactly what was fetched, the script that reproduces it, and
> what's still genuinely manual (code violations, delinquency pre-sale,
> sheriff sale, probate).

Reading, PA prospect scoring project. Prepared for a licensed agent (RS372287)
building a farming / direct-mail list under the constraints in the project
README: no MLS data, no paid skip-trace, free/public records only, nothing
scraped from behind a login or in violation of a site's terms of service.

**Geographic scope:** City of Reading, West Reading Borough, Wyomissing
Borough, Shillington Borough, Kenhorst Borough, Cumru Township.

**Property scope:** Single-family only.

Every source below was checked against a search engine and, where the page
would render, fetched directly on 2026-09-04. A few municipal pages are
JS-rendered and didn't yield fetchable content — those are marked
**(unverified, check by hand)** rather than described from memory.

---

## 1. Berks County parcel + assessment data

| Source | URL | Format | Bulk or manual | Refresh cadence |
|---|---|---|---|---|
| Berks County Data Hub — CAMA extracts | https://opendata.berkspa.gov/ (search "CAMA"; e.g. `Berks Assessment CAMA Master File` at https://opendata.berkspa.gov/maps/berks::berks-assessment-cama-master-file/explore) | Multiple export formats offered by the ArcGIS Hub download button (CSV, Shapefile, GeoJSON, File Geodatabase) | **Bulk download** — Master CAMA File, Residential CAMA File, Commercial CAMA File are full-county extracts | Each item page states an extract date; county doesn't publish a fixed cadence — check the extract date on each download before use |
| CAMA Data Dictionary | Linked from the CAMA dataset pages on opendata.berkspa.gov | PDF/XLSX | Manual download | Static, updated when field definitions change |
| Assessment ArcGIS REST services | `https://gis.co.berks.pa.us/arcgis/rest/services/Assess/ParcelBase4/MapServer`, `.../ParcelTable/MapServer`, `.../ParcelSearchTable/MapServer` | JSON via REST query (supports `resultOffset`/`resultRecordCount` paging) | **Scriptable/bulk** — this is a public ArcGIS REST endpoint, queryable programmatically (e.g. `?where=1=1&outFields=*&f=json`) without login | Live/real-time — reflects current assessment DB |
| Property Records Search application | https://propertyrecords.berkspa.gov/ | Web UI | Manual — search by owner, address, or parcel ID; one record at a time | Live |
| Legacy Assessment Parcel Search | https://gis.co.berks.pa.us/parcelsearch/ | Web UI | Manual | Live |
| Assessment Parcel Viewer (map) | https://gis.co.berks.pa.us/parcelviewer/ | Interactive map | Manual | Live |
| PASDA (PA Spatial Data Access) | https://www.pasda.psu.edu/ | Shapefile/GeoDatabase | Bulk, but PA-wide parcel coverage is described as incomplete/county-contributed | Irregular — Berks' own Data Hub is the more current source for Berks parcels |

**Recommendation:** use the CAMA Master + Residential extracts from the Data
Hub as the primary bulk source, and treat the `Assess/ParcelTable` REST
service as a live cross-check / delta-fill for fields that lag in the extract.
Owner mailing address, situs address, sale date, sale price, assessed value,
land use code, and year built are all standard CAMA fields — exact column
names are in the CAMA Data Dictionary and need to be confirmed against the
actual downloaded file before the pipeline maps them (I won't assume column
names until we have the file).

**Action needed from you:** download the CAMA Master + Residential CSV/Shapefile
extracts and the Data Dictionary, and drop them in `./data/raw`.

---

## 2. City of Reading code violations / rental registrations

| Source | URL | Format | Bulk or manual | Refresh cadence |
|---|---|---|---|---|
| Property & Codes Enforcement (info page) | https://www.readingpa.gov/property-and-codes-enforcement | HTML, informational | N/A — no data | N/A |
| Codes Enforcement Process (info page) | https://www.readingpa.gov/codes-enforcement-process | HTML, informational | N/A — no data | N/A |
| Housing Registration (rental/mixed-use registration requirement) | https://www.readingpa.gov/housing-registration | HTML + PDF instructions | N/A — describes the *requirement*, not a public registry search | N/A |
| Reading Self-Serve (permitting/licensing portal, Tyler EnerGov) | https://www.readingpa.gov/121-reading-self-serve | Web portal | **Unverified, check by hand** — could not confirm from the outside whether case/permit/rental-registration search is public without an account. Worth checking manually; many Tyler EnerGov instances expose a public "search records" view. | Live, if public search exists |
| Citizens Service Center (complaint intake, not a database) | Phone 1-877-727-3234 | N/A | N/A | N/A |
| Right-to-Know request (formal records request) | https://www.readingpa.gov/right-to-know | Whatever the City provides (likely CSV/PDF export from their code-enforcement system) | **Manual, must request by hand** | One-time per request; City can charge for requests estimated >$100 |

**Bottom line:** I could not find a public, bulk, or self-service database of
open code violations or the rental-registration roster for the City of
Reading. The only path to violation counts and rental-registration status by
parcel that I can verify is a **Right-to-Know Law (RTKL) request** to the
City's Law Department (815 Washington St, Room 2-54), asking for an export of
open/active code violation notices and active rental/housing registrations,
ideally with parcel ID or address so it can be joined to the assessment data.
This needs to be filed in writing and signed — I can draft the request text
for you, but it needs to go out under your name.

**Action needed from you:** (1) manually check whether Reading Self-Serve has
a public case-search view; (2) file (or have me draft) an RTKL request for
violation/registration data if no public search exists; drop whatever comes
back into `./data/raw`.

The boroughs in scope (West Reading, Wyomissing, Shillington, Kenhorst) and
Cumru Township each run their own code enforcement — West Reading's is at
https://www.westreadingborough.com/code-enforcement/ (also informational, no
public database found). The same RTKL approach applies to each; I have not
individually verified their codified-ordinance/violation search tools and
will not assume they mirror Reading's.

---

## 3. Berks County tax delinquency and sheriff sales

| Source | URL | Format | Bulk or manual | Refresh cadence |
|---|---|---|---|---|
| Tax Claim Bureau — Upset Sale current list | e.g. https://www.berkspa.gov/getmedia/c01d92da-72df-426a-ac1f-9ee7f8c767ce/2025-Upset-Sale-Current-List.pdf (a new PDF is posted each cycle under berkspa.gov/departments/tax-claim-bureau) | PDF | Manual download | Annual — upset sale held each September; list posted ahead of the sale |
| Tax Claim Bureau — Repository (unsold) list | https://www.berkspa.gov/departments/tax-claim-bureau/repository-list | PDF/HTML | Manual | Updated as judicial sales complete |
| Tax Claim Bureau — Sale FAQs / timeline | https://www.berkspa.gov/departments/tax-claim-bureau | PDF | Manual | Static reference |
| Sheriff Sale Listing (Real Estate Executions) | https://sheriffsale.countyofberks.com/ | HTML table, browsable by sale date (monthly) | **Manual** — no CSV/PDF export found; fields shown are case number, plaintiff/defendant, attorney, property address, UPI parcel number, judgment amount, and status. No bulk export button. | Rolling — sales generally scheduled monthly (Fri, occasionally Thu) |
| Bid4Assets (Berks Sheriff auction platform) | https://www.bid4assets.com/berkscountysheriffsales | HTML listings | Manual; third-party auction platform, not a county open-data source | Per auction cycle |

**Important limitation:** neither the upset-sale list nor the sheriff-sale
listing is a full "who is currently tax-delinquent" roster — they only show
properties that have progressed to a scheduled sale. I found no public bulk
file of all currently-delinquent parcels short of that. If you want
delinquency status *before* a property reaches sale, that likely requires a
direct request to the Tax Claim Bureau (taxclaim@countyofberks.com,
610-478-6625 area) — I'd flag that as a manual/by-hand item rather than
assume it exists as a downloadable file.

Because the sheriff-sale site has no export function and I was asked not to
scrape against a site's terms, treat that page as **copy-by-hand** (or check
its terms of use before any automated pull) rather than something the
pipeline reads directly.

**Action needed from you:** download the current Upset Sale PDF and
Repository list, and export/copy whatever sheriff-sale rows fall in the
Reading + inner-ring footprint into `./data/raw`. Confirm with the Tax Claim
Bureau whether a pre-sale delinquency list is available on request.

---

## 4. Berks County probate / estate filings

| Source | URL | Format | Bulk or manual | Refresh cadence |
|---|---|---|---|---|
| Register of Wills — Estates Search | http://rwills.co.berks.pa.us/geneology/Estates.aspx | Web UI, search by name | Manual — one name at a time, no bulk export or API | Records "date from 1752 to present"; no stated refresh cadence, no e-filing (paper-only submissions) |
| Register of Wills dept. page | https://www.berkspa.gov/departments/register-of-wills | HTML, informational | N/A | N/A |
| Orphans' Court | https://www.berkspa.gov/departments/register-of-wills/orphans-court | HTML, informational | N/A | N/A |

**Limitation:** estate records are indexed by decedent name, not by property
address or parcel ID, and there's no bulk export. Turning this into
"probate flag" on a parcel would require manually searching decedent names
against the CAMA owner-name field — not something to automate against a
name-search web form. I'd treat probate as a **manual, low-volume enrichment**
(e.g., you periodically pull recent estate filings and I match names against
the owner list) rather than a pipeline input, unless you find it worth the
by-hand effort.

**Action needed from you:** if you want this signal, periodically export/copy
recent estate filings by hand; I can join by owner name if you provide them.

---

## 5. Bulk/open-data portal endpoints — summary

- **Berks County Data Hub** (ArcGIS Hub): https://opendata.berkspa.gov/ — primary bulk source for parcels/CAMA, tax maps, and various county layers.
- **Berks County ArcGIS REST services**: https://gis.co.berks.pa.us/arcgis/rest/services/ — scriptable, no login, good for live pulls (rate-limit-friendly paging via `resultOffset`).
- **PASDA**: https://www.pasda.psu.edu/ — statewide, secondary to the county's own hub for Berks parcels.
- **PA Open Data Portal**: https://data.pa.gov/ — statewide datasets; nothing Reading/Berks-specific and property-relevant surfaced in this pass.

No source above requires a login or appears to be behind a paywall except
where explicitly marked (RTKL requests, which are a formal public-records
process, not a bypass of any restriction).

---

## 6. Explicitly out of scope

- **MLS / Bright MLS** — you confirmed you have access, but per your
  constraints this will **not** be used for the prospect list or pipeline.
- **Paid skip-trace / PropStream / ListSource** — not used; phone numbers and
  skip-trace are handled by you separately through a compliant vendor.
- Nothing behind a login was scraped or will be scraped for this project.

---

## Summary: what's ready to script vs. what needs you

**Scriptable now (once files are dropped in `./data/raw`, or pulled live via REST):**
- Berks County parcel/CAMA data (bulk extract or REST API)

**Needs a manual download from you:**
- Tax Claim Bureau upset-sale PDF + repository list
- Sheriff-sale rows for the target municipalities (no export button)

**Needs a Right-to-Know request or direct call before it can be used at all:**
- City of Reading (and each borough) open code violations / rental registration roster
- Pre-sale tax delinquency roster (beyond what's already on the upset-sale list)

**Manual, low-volume enrichment only (not a pipeline feed):**
- Register of Wills estate filings — name-matched by hand

Stopping here per your instructions. Once you've dropped what you can get
into `./data/raw` (and let me know the outcome of the Reading Self-Serve
check and any RTKL requests), I'll start Phase 2.

---

## Addendum (2026-09-04) — parcel data fetched programmatically

The Berks County Data Hub (opendata.berkspa.gov) publishes a standard DCAT
catalog (`/api/feed/dcat-us/1.1.json`) that resolves every dataset — CAMA
Master/Residential/Commercial files included — to direct CSV/Shapefile/
GeoJSON/XLSX download URLs *and* to the underlying ArcGIS FeatureServer
REST endpoints. Those endpoints are public, unauthenticated, and queryable
with a `where` clause and pagination (`resultOffset`/`resultRecordCount`),
which means the CAMA Residential extract can be pulled directly instead of
requiring a manual export.

**What I fetched, and how it maps to what Phase 1 called "manual":**

- `data/raw/berks_cama_residential.csv` — the full CAMA Residential File
  (45,017 rows) filtered server-side to the 24 target municipality codes
  (Reading's 19 wards + West Reading, Wyomissing, Shillington, Kenhorst,
  Cumru Township), via
  `scripts/fetch_parcels.py`. Contains owner name, mailing address, situs
  address (componentized), sale date/price, land/building/total assessed
  value, land use code (LUC), year built, homestead flag, bedrooms/baths/
  square footage, and more. Re-run the script anytime to refresh.
- `reference/CAMA_Data_Dictionary.pdf` — the county's own field dictionary
  (municipality codes, class codes, land-use codes) fetched from the ArcGIS
  item's raw-file endpoint. This is what Phase 2's single-family filter and
  column mapping are built from — nothing was guessed.
- `reference/target_municipalities.csv` and
  `reference/luc_single_family_codes.csv` — the municipality-code and
  land-use-code crosswalks I derived from that dictionary, with every
  judgment call (e.g. whether row homes, mobile-homes-on-owned-land, or
  fee-simple condos count as "single-family") written down and flagged for
  you to override in `reference/luc_single_family_codes.csv` if you
  disagree.
- `data/raw/tax_claim_upset_sale_2025.pdf` and
  `data/raw/tax_claim_repository_list.pdf` — downloaded directly (still
  PDFs, still manual to refresh each cycle since the file URL changes and
  isn't discoverable via an API — check
  `berkspa.gov/departments/tax-claim-bureau` for the current link each
  quarter).

**License note:** the county's GIS Data General Agreement (attached to
every dataset, full text in `reference/CAMA_Data_Dictionary.pdf`'s source
item) permits use of this data but states it "may NOT be copied,
redistributed, resold, transferred, leased, or provided in whole or part to
any other entity or person." That's fine for your own farming/outreach use;
it means the raw extract itself shouldn't be handed off or resold as a
dataset.

**Still genuinely manual / not scriptable** (confirmed, not just assumed):
sheriff-sale listings (no export button on `sheriffsale.countyofberks.com`),
pre-sale tax delinquency status (only the upset-sale list is public),
City of Reading / borough code violations and rental-registration rosters
(no public search found — RTKL request still the only path), and Register
of Wills estate filings (name-search only, no bulk export).
