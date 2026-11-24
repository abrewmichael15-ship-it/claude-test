# Left-Behind Clients toolkit

Tools for the 90-day Left-Behind Clients plan (Berks, Lancaster, York).

## 1. Expired-listing list builder

`expired_list/build_list.py` turns a Bright MLS hot-sheet export into a weekly mail list and a DNC-scrubbed call list. Stdlib only, Python 3.9+.

```bash
python expired_list/build_list.py hotsheet.csv \
    --phones skiptrace.csv \
    --dnc dnc/federal_610.txt --dnc dnc/federal_484.txt --dnc dnc/federal_717.txt \
    --dnc dnc/pa_dnc.txt --dnc dnc/internal_optouts.txt \
    --history expired_list/mailed_history.csv \
    --max-days 30 --out out/2026-11-24
```

| Output | What it is |
| --- | --- |
| `mail_list.csv` | Every eligible owner, with the letter's comp fields (list price, price drop, DOM, photos). Mail-merge it into the "why it didn't sell" letter. |
| `call_list.csv` | Phones that are on **none** of the `--dnc` files. Only written when `--dnc` is given. |
| `dnc_removed.csv` | Numbers that were suppressed, for your records. |

What it does:

- Keeps **Expired** and **Canceled/Cancelled** only. Withdrawn, Temp Off Market and everything else are dropped.
- Keeps Berks, Lancaster and York (`--counties` to change). Handles `Berks`, `BERKS`, `Berks, PA` and `York County`.
- Skips MLS #s already in `--history`, then appends this run's listings to it (`--no-history-update` to skip that).
- Refuses to build a call list without at least one `--dnc` file, and warns if a DNC file is more than 31 days old.
- Uses the owner's tax mailing address when the export has one, otherwise the property address.
- Column names are matched loosely (`MLS #`, `Zip Code`, `Tax Owner Name`, etc.). If your export uses a different header, add `--map field="Your Header"`. Run `--help` to list the fields.

DNC files: one number per line in any format (`6105550101`, `(610) 555-0101`, or the federal registry's `610,5550101`). Download the federal area-code files and the PA list through your broker's registry access.

Sample files are in `expired_list/sample/`. Tests: `python -m pytest tests`.

## 2. KPI tracker

`kpi_tracker/LBC_KPI_Tracker.xlsx` is set to the 4-hour-a-week targets.

- **Weekly Log:** type each week's counts on Sunday (yellow cells).
- **Dashboard:** actual vs. target, the on-pace number for today, and Behind / On pace / Hit status. It also shows conversion rates for the day-30 target reset.

To regenerate it from scratch: `python kpi_tracker/build_tracker.py` (needs `openpyxl`). This overwrites the file, so copy your logged numbers out first.
