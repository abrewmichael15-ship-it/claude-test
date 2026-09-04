# Outreach plan — top 500 (2026-09-04 run)

Full designed version: published artifact "The Reading Farm" (link shared in
chat — republish via `Artifact` from this repo's scratch copy if you need to
regenerate it; the source numbers below are what it's built from).

## Read this first

**Every property in the current top 500 is flagged absentee owner — zero
owner-occupants.** That's a byproduct of the current scoring composition, not
a targeting choice: only tenure (35pts) and absentee (20pts) are live; equity
proxy and violations (45pts combined) are still 0 for every row. An absentee
property with decent tenure always outscores an identical owner-occupied one
under today's weights. This plan is written for a **landlord/investor
audience** as a result — treat it as wave one, and expect the list to
rebalance once `appreciation_factor_annual` and violations data go live.

## Composition

- Tier A: 100 · Tier B: 200 · Tier C: 200
- 100% absentee-owned · 7 tax-delinquent (matched to the 2025 upset-sale list)
- Avg. tenure 12.5 years · Avg. assessed value $55.4k
- Municipality mix: Reading 377 · Kenhorst 87 · Shillington 35 · Wyomissing 1
  (West Reading and Cumru have no representation today — lower absentee
  rates there mean fewer parcels clear the combined tenure+absentee bar)

## Cadence by tier

| Tier | Touches/12mo | Format | Lead angle |
|---|---|---|---|
| A (100) | 9 | Letter-heavy, 2 handwritten-style | Direct off-market inquiry |
| B (200) | 5 | Postcard-led, 1 letter | Equity-awareness |
| C (200) | 3 | Postcard only | Brand/farm awareness |
| Tax-delinquent (7) | +2 | Discreet letter only, no postcards | Sensitive-situation outreach — see compliance note |

Drop schedule (months from campaign start): A = 1,3,5,7,9,11,12 (heaviest);
B = 1,4,7,10; C = 1,7,12.

## Budget (12 months, ballpark)

| Item | Qty | Unit | Total |
|---|---|---|---|
| Tier A letters | 900 | $1.35 | $1,215 |
| Tier B postcards | 800 | $0.65 | $520 |
| Tier B letter | 200 | $1.35 | $270 |
| Tier C postcards | 600 | $0.60 | $360 |
| Discreet letters | 14 | $1.60 | $22 |
| **Total** | | | **≈ $2,387** |

Get real quotes before committing — these are typical vendor ballparks.
CASS-certify the mailing list first (addresses come straight from the
county's MAILING field, not through USPS validation).

## Follow Up Boss setup

1. Import `top_500.csv`; split `fub_tags` on `|` into individual tags.
2. Build Smart Lists per tier tag, plus one off `tax-delinquent` that
   overrides those 7 onto the discreet-letter track regardless of tier.
3. Action Plan per tier matching the cadence above, triggered off "date
   added" so each property's sequence starts on import, not a fixed date.
4. Add a response-outcome custom field (no response / called / listed /
   declined) — this is how you start building real outcome data. The
   scoring weights are reasoned, not backtested; this is the feedback loop
   that would let you actually validate or retune them.

## Compliance checklist

- **PA RELRA**: every piece needs your name, license number (RS372287), and
  your employing broker's name — license number alone isn't sufficient.
- **Fair Housing**: list is built from ownership/tenure/financial signals,
  not protected class — keep copy free of steering language or assumptions
  about occupants.
- **Tax-delinquent subset (7 parcels)**: plain envelopes, letter only, never
  reference delinquency anywhere a third party could read it off a postcard.
- **Do-not-mail**: log opt-outs and suppress from every future cadence.
- **No phone/text in this plan** — mail-only, matching current data scope.
  Layer in calls/texts only after skip-tracing through a compliant vendor,
  mind TCPA consent when you do.

Sample copy for each mail piece (off-market inquiry letter, equity-awareness
postcard, discreet sensitive-situation letter) is in the published artifact —
ask me to drop it into this file too if you'd rather have it in the repo
verbatim.
