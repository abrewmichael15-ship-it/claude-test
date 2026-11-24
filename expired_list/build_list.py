#!/usr/bin/env python3
"""Build the weekly expired/canceled listing mail and call lists.

Reads a Bright MLS export (CSV), keeps only Expired and Canceled listings in
Berks, Lancaster and York counties, skips anything already mailed, and writes:

  mail_list.csv   every eligible owner, with the fields the "why it didn't
                  sell" letter needs (list price, price drop, DOM, photos)
  call_list.csv   only phone numbers that are NOT on any Do Not Call file
  dnc_removed.csv numbers that were suppressed, so you can audit the scrub

Withdrawn, Temp Off Market and every other status are excluded on purpose:
a withdrawn listing can still be under contract with the listing broker.

Stdlib only. Example:

  python expired_list/build_list.py hotsheet.csv \
      --phones skiptrace.csv \
      --dnc dnc/federal_610.txt --dnc dnc/federal_717.txt --dnc dnc/pa_dnc.txt \
      --dnc dnc/internal_optouts.txt \
      --history expired_list/mailed_history.csv \
      --max-days 30 --out out/2026-11-24
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

DEFAULT_COUNTIES = ("berks", "lancaster", "york")
DNC_MAX_AGE_DAYS = 31  # federal rule: scrub against a registry copy no older than 31 days

# Canonical field -> accepted header spellings (compared after normalizing:
# lowercase, letters and digits only). Override any of them with --map.
ALIASES: dict[str, tuple[str, ...]] = {
    "mls_id": ("mls", "mlsnumber", "mlsno", "mlsid", "listingid", "listingnumber", "mlsnum"),
    "status": ("status", "mlsstatus", "listingstatus", "standardstatus"),
    "county": ("county", "countyorparish", "countyname"),
    "address": ("address", "fulladdress", "streetaddress", "propertyaddress", "unparsedaddress"),
    "city": ("city", "postalcity", "municipality"),
    "state": ("state", "stateorprovince"),
    "zip": ("zip", "zipcode", "postalcode", "zip5"),
    "list_price": ("listprice", "currentprice", "lastlistprice", "price"),
    "original_list_price": ("originallistprice", "origlistprice", "originalprice"),
    "dom": ("dom", "daysonmarket", "cdom", "cumulativedaysonmarket"),
    "photo_count": ("photocount", "photoscount", "numberofphotos", "photos", "mediacount"),
    "off_market_date": (
        "offmarketdate", "statuschangedate", "statusdate", "expirationdate",
        "canceldate", "cancellationdate", "withdrawndate",
    ),
    "owner_name": ("ownername", "taxownername", "owner", "owners", "owner1name"),
    "owner_mail_address": ("ownermailingaddress", "taxmailingaddress", "mailingaddress", "owneraddress"),
    "owner_mail_city": ("ownermailingcity", "taxmailingcity", "mailingcity", "ownercity"),
    "owner_mail_state": ("ownermailingstate", "taxmailingstate", "mailingstate", "ownerstate"),
    "owner_mail_zip": ("ownermailingzip", "taxmailingzip", "mailingzip", "ownerzip"),
    "phone": ("phone", "ownerphone", "phone1", "phonenumber"),
}
REQUIRED = ("mls_id", "status", "county", "address")

SUFFIXES = {
    "STREET": "ST", "AVENUE": "AVE", "ROAD": "RD", "DRIVE": "DR", "LANE": "LN",
    "COURT": "CT", "BOULEVARD": "BLVD", "PLACE": "PL", "CIRCLE": "CIR",
    "TERRACE": "TER", "PIKE": "PK", "HIGHWAY": "HWY", "PARKWAY": "PKWY",
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
}

MAIL_FIELDS = [
    "mls_id", "status", "off_market_date", "owner_name",
    "mail_address", "mail_city", "mail_state", "mail_zip",
    "property_address", "city", "zip", "county",
    "list_price", "original_list_price", "price_drop", "dom", "photo_count",
]
CALL_FIELDS = ["mls_id", "owner_name", "property_address", "city", "phone"]


def norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())


def norm_address(a: str) -> str:
    words = re.sub(r"[^A-Z0-9 ]", " ", (a or "").upper()).split()
    return " ".join(SUFFIXES.get(w, w) for w in words)


def norm_phone(p: str) -> str | None:
    digits = re.sub(r"\D", "", p or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else None


def norm_county(c: str) -> str:
    c = (c or "").split(",")[0].strip().lower()
    return re.sub(r"\s+county$", "", c)


def classify_status(s: str) -> str | None:
    s = (s or "").strip().lower()
    if s.startswith("expired"):
        return "Expired"
    if s.startswith("cancel"):  # Canceled / Cancelled
        return "Canceled"
    return None


def to_number(v: str) -> float | None:
    v = re.sub(r"[^0-9.\-]", "", v or "")
    try:
        return float(v) if v else None
    except ValueError:
        return None


def parse_date(v: str) -> date | None:
    v = (v or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def money(v: float | None) -> str:
    return "" if v is None else f"{v:.0f}"


def resolve_columns(headers: list[str], overrides: dict[str, str]) -> dict[str, str]:
    """Map canonical field -> actual header in this file."""
    by_norm = {norm_header(h): h for h in headers}
    out: dict[str, str] = {}
    for fld, aliases in ALIASES.items():
        if fld in overrides:
            if overrides[fld] not in headers:
                raise SystemExit(f"--map {fld}={overrides[fld]!r}: no such column. Columns: {headers}")
            out[fld] = overrides[fld]
            continue
        for a in aliases:
            if a in by_norm:
                out[fld] = by_norm[a]
                break
    return out


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def load_dnc(paths: list[Path], today: date, warn) -> set[str]:
    numbers: set[str] = set()
    for p in paths:
        age = (today - date.fromtimestamp(p.stat().st_mtime)).days
        if age > DNC_MAX_AGE_DAYS:
            warn(f"DNC file {p} is {age} days old. Download a fresh copy (max {DNC_MAX_AGE_DAYS} days).")
        with p.open(encoding="utf-8-sig", errors="ignore") as f:
            for line in f:
                n = norm_phone(line)
                if n:
                    numbers.add(n)
    return numbers


def load_phones(path: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Skip-trace file -> (phones by mls_id, phones by normalized address+zip)."""
    headers, rows = read_csv(path)
    cols = resolve_columns(headers, {})
    phone_cols = [h for h in headers if "phone" in h.lower() or "mobile" in h.lower() or "cell" in h.lower()]
    if not phone_cols:
        raise SystemExit(f"{path}: no phone columns found (need a header containing 'phone', 'mobile' or 'cell').")
    by_id: dict[str, list[str]] = {}
    by_addr: dict[str, list[str]] = {}
    for r in rows:
        nums = [n for n in (norm_phone(r.get(c, "")) for c in phone_cols) if n]
        if not nums:
            continue
        if "mls_id" in cols and r.get(cols["mls_id"], "").strip():
            by_id.setdefault(r[cols["mls_id"]].strip(), []).extend(nums)
        if "address" in cols:
            key = norm_address(r.get(cols["address"], "")) + "|" + (r.get(cols.get("zip", ""), "") or "")[:5]
            by_addr.setdefault(key, []).extend(nums)
    return by_id, by_addr


def load_history(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    _, rows = read_csv(path)
    return {r["mls_id"].strip() for r in rows if r.get("mls_id")}


@dataclass
class Summary:
    read: int = 0
    kept: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    by_county: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    phones_checked: int = 0
    phones_ok: int = 0
    phones_dnc: int = 0

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1


def build(
    mls_path: Path,
    out_dir: Path,
    *,
    phones_path: Path | None = None,
    dnc_paths: list[Path] | None = None,
    history_path: Path | None = None,
    counties: tuple[str, ...] = DEFAULT_COUNTIES,
    max_days: int | None = None,
    overrides: dict[str, str] | None = None,
    update_history: bool = True,
    today: date | None = None,
    warn=lambda m: print(f"WARNING: {m}", file=sys.stderr),
) -> Summary:
    today = today or date.today()
    headers, rows = read_csv(mls_path)
    cols = resolve_columns(headers, overrides or {})
    missing = [f for f in REQUIRED if f not in cols]
    if missing:
        raise SystemExit(
            f"{mls_path}: can't find column(s) for {missing}. Use --map field=\"Header\". Columns: {headers}"
        )
    if phones_path and not dnc_paths:
        raise SystemExit("--phones needs at least one --dnc file. Never build a call list without a scrub.")

    dnc = load_dnc(dnc_paths or [], today, warn)
    phones_by_id, phones_by_addr = load_phones(phones_path) if phones_path else ({}, {})
    history = load_history(history_path)
    wanted = {c.lower() for c in counties}

    def get(r: dict[str, str], fld: str) -> str:
        return (r.get(cols[fld], "") or "").strip() if fld in cols else ""

    s = Summary()
    mail_rows: list[dict[str, str]] = []
    call_rows: list[dict[str, str]] = []
    dnc_rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for r in rows:
        s.read += 1
        mls_id = get(r, "mls_id")
        status = classify_status(get(r, "status"))
        county = norm_county(get(r, "county"))
        if not status:
            s.skip(f"status {get(r, 'status') or '(blank)'}")
            continue
        if county not in wanted:
            s.skip("outside target counties")
            continue
        if mls_id in seen:
            s.skip("duplicate row")
            continue
        if mls_id in history:
            s.skip("already mailed")
            continue
        off = parse_date(get(r, "off_market_date"))
        if max_days is not None and off and (today - off).days > max_days:
            s.skip(f"off market > {max_days} days")
            continue
        seen.add(mls_id)

        lp = to_number(get(r, "list_price"))
        olp = to_number(get(r, "original_list_price"))
        drop = (olp - lp) if (lp is not None and olp is not None and olp > lp) else (0.0 if lp is not None and olp is not None else None)
        has_mail = bool(get(r, "owner_mail_address"))
        row = {
            "mls_id": mls_id,
            "status": status,
            "off_market_date": off.isoformat() if off else get(r, "off_market_date"),
            "owner_name": get(r, "owner_name") or "Current Owner",
            "mail_address": get(r, "owner_mail_address") if has_mail else get(r, "address"),
            "mail_city": get(r, "owner_mail_city") if has_mail else get(r, "city"),
            "mail_state": get(r, "owner_mail_state") if has_mail else (get(r, "state") or "PA"),
            "mail_zip": get(r, "owner_mail_zip") if has_mail else get(r, "zip"),
            "property_address": get(r, "address"),
            "city": get(r, "city"),
            "zip": get(r, "zip"),
            "county": county.title(),
            "list_price": money(lp),
            "original_list_price": money(olp),
            "price_drop": money(drop),
            "dom": get(r, "dom"),
            "photo_count": get(r, "photo_count"),
        }
        mail_rows.append(row)
        s.kept += 1
        s.by_county[row["county"]] = s.by_county.get(row["county"], 0) + 1
        s.by_status[status] = s.by_status.get(status, 0) + 1

        nums: list[str] = []
        if mls_id in phones_by_id:
            nums += phones_by_id[mls_id]
        akey = norm_address(row["property_address"]) + "|" + row["zip"][:5]
        nums += phones_by_addr.get(akey, [])
        if n := norm_phone(get(r, "phone")):
            nums.append(n)
        for n in dict.fromkeys(nums):  # dedupe, keep order
            s.phones_checked += 1
            base = {"mls_id": mls_id, "owner_name": row["owner_name"],
                    "property_address": row["property_address"], "city": row["city"], "phone": n}
            if not dnc_paths:
                continue  # no scrub, no call list
            if n in dnc:
                s.phones_dnc += 1
                dnc_rows.append(base)
            else:
                s.phones_ok += 1
                call_rows.append(base)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "mail_list.csv", MAIL_FIELDS, mail_rows)
    if dnc_paths:
        write_csv(out_dir / "call_list.csv", CALL_FIELDS, call_rows)
        write_csv(out_dir / "dnc_removed.csv", CALL_FIELDS, dnc_rows)

    if history_path and update_history and mail_rows:
        new_file = not history_path.exists()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["mls_id", "added", "status", "property_address"])
            if new_file:
                w.writeheader()
            for m in mail_rows:
                w.writerow({"mls_id": m["mls_id"], "added": today.isoformat(),
                            "status": m["status"], "property_address": m["property_address"]})
    return s


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mls_csv", type=Path, help="Bright MLS hot-sheet export (CSV)")
    ap.add_argument("--out", type=Path, default=Path("out") / time.strftime("%Y-%m-%d"), help="output folder")
    ap.add_argument("--phones", type=Path, help="skip-trace CSV (MLS # or address + any 'phone' columns)")
    ap.add_argument("--dnc", type=Path, action="append", default=[],
                    help="Do Not Call file, one number per line (repeat for federal area codes, PA list, internal opt-outs)")
    ap.add_argument("--history", type=Path, help="CSV of MLS #s already mailed; new ones are appended")
    ap.add_argument("--no-history-update", action="store_true", help="read history but don't append to it")
    ap.add_argument("--counties", default=",".join(DEFAULT_COUNTIES), help="comma-separated (default: %(default)s)")
    ap.add_argument("--max-days", type=int, help="skip listings off market longer than this")
    ap.add_argument("--map", action="append", default=[], metavar='FIELD="Header"',
                    help=f"override a column mapping; fields: {', '.join(ALIASES)}")
    a = ap.parse_args(argv)

    overrides = {}
    for m in a.map:
        k, _, v = m.partition("=")
        if k not in ALIASES or not v:
            ap.error(f"bad --map {m!r}")
        overrides[k] = v

    s = build(
        a.mls_csv, a.out, phones_path=a.phones, dnc_paths=a.dnc, history_path=a.history,
        counties=tuple(c.strip().lower() for c in a.counties.split(",") if c.strip()),
        max_days=a.max_days, overrides=overrides, update_history=not a.no_history_update,
    )
    print(f"Read {s.read} rows -> {s.kept} to mail ({a.out / 'mail_list.csv'})")
    for k, v in sorted(s.by_county.items()):
        print(f"  {k}: {v}")
    for k, v in sorted(s.by_status.items()):
        print(f"  {k}: {v}")
    if s.skipped:
        print("Skipped:")
        for k, v in sorted(s.skipped.items(), key=lambda kv: -kv[1]):
            print(f"  {k}: {v}")
    if a.dnc:
        print(f"Phones: {s.phones_checked} checked, {s.phones_ok} OK to call, {s.phones_dnc} removed (DNC)")
    else:
        print("No --dnc files given: mail list only, no call list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
