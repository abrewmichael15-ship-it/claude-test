import csv
import os
import sys
import time
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "expired_list"))
import build_list as bl  # noqa: E402

SAMPLE = ROOT / "expired_list" / "sample"
TODAY = date(2026, 11, 24)


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fresh(path, tmp_path):
    """Copy a DNC sample so its mtime is today (the age check reads mtime)."""
    dst = tmp_path / path.name
    dst.write_bytes(path.read_bytes())
    return dst


def run(tmp_path, **kw):
    kw.setdefault("today", TODAY)
    kw.setdefault("warn", lambda m: None)
    return bl.build(SAMPLE / "hotsheet_sample.csv", tmp_path / "out", **kw)


def test_filters_status_county_and_age(tmp_path):
    s = run(tmp_path, max_days=30)
    mail = rows(tmp_path / "out" / "mail_list.csv")
    assert [m["mls_id"] for m in mail] == ["PABK2000101", "PALA2000202", "PABK2000606"]
    assert s.skipped["status Withdrawn"] == 1
    assert s.skipped["outside target counties"] == 1
    assert s.skipped["off market > 30 days"] == 1
    assert {m["status"] for m in mail} == {"Expired", "Canceled"}


def test_letter_fields(tmp_path):
    run(tmp_path)
    m = {r["mls_id"]: r for r in rows(tmp_path / "out" / "mail_list.csv")}
    jane = m["PABK2000101"]
    assert jane["list_price"] == "189900"
    assert jane["price_drop"] == "25000"
    assert jane["dom"] == "96" and jane["photo_count"] == "14"
    assert jane["off_market_date"] == "2026-11-20"
    # owner mailing address used when present (PO Box), property address otherwise
    assert m["PALA2000202"]["mail_address"] == "PO Box 88"
    assert m["PABK2000606"]["mail_address"] == "500 Hill Road"
    assert m["PABK2000606"]["owner_name"] == "Current Owner"
    assert m["PAYK2000505"]["county"] == "York"


def test_dnc_scrub(tmp_path):
    dnc = fresh(SAMPLE / "dnc_sample.txt", tmp_path)
    s = run(tmp_path, phones_path=SAMPLE / "skiptrace_sample.csv", dnc_paths=[dnc])
    call = {r["phone"] for r in rows(tmp_path / "out" / "call_list.csv")}
    removed = {r["phone"] for r in rows(tmp_path / "out" / "dnc_removed.csv")}
    assert call == {"6105550101", "4845550601"}
    assert removed == {"6105550102", "7175550201"}
    assert (s.phones_ok, s.phones_dnc) == (2, 2)


def test_phones_require_dnc(tmp_path):
    with pytest.raises(SystemExit):
        run(tmp_path, phones_path=SAMPLE / "skiptrace_sample.csv")


def test_stale_dnc_warns(tmp_path):
    dnc = fresh(SAMPLE / "dnc_sample.txt", tmp_path)
    old = time.time() - 40 * 86400
    os.utime(dnc, (old, old))
    warnings = []
    bl.build(SAMPLE / "hotsheet_sample.csv", tmp_path / "out", dnc_paths=[dnc],
             today=date.today(), warn=warnings.append)
    assert warnings and "days old" in warnings[0]


def test_history_skips_already_mailed(tmp_path):
    hist = tmp_path / "mailed_history.csv"
    first = run(tmp_path, history_path=hist)
    assert first.kept == 4
    second = run(tmp_path, history_path=hist)
    assert second.kept == 0
    assert second.skipped["already mailed"] == 4


def test_missing_required_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Foo,Bar\n1,2\n")
    with pytest.raises(SystemExit):
        bl.build(bad, tmp_path / "out", today=TODAY)


def test_map_override(tmp_path):
    src = tmp_path / "custom.csv"
    src.write_text("Listing Key,Stat,Cnty,Location\nX1,Expired,Berks,1 A St\n")
    s = bl.build(src, tmp_path / "out", today=TODAY,
                 overrides={"mls_id": "Listing Key", "status": "Stat", "county": "Cnty", "address": "Location"})
    assert s.kept == 1


@pytest.mark.parametrize("raw,expected", [
    ("(610) 555-0101", "6105550101"),
    ("1-717-555-0201", "7175550201"),
    ("610,5550102", "6105550102"),
    ("555-0101", None),
])
def test_norm_phone(raw, expected):
    assert bl.norm_phone(raw) == expected
