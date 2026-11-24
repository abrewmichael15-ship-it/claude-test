#!/usr/bin/env python3
"""Generate the Left-Behind Clients 90-day KPI tracker (Excel).

  python kpi_tracker/build_tracker.py            # writes kpi_tracker/LBC_KPI_Tracker.xlsx

Targets match the 4-hour-a-week plan. Change them on the Dashboard tab
(yellow cells), not here, once the workbook is in use.
"""
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).with_name("LBC_KPI_Tracker.xlsx")
START = date(2026, 11, 24)
WEEKS = 13
# (metric, 90-day target, how it's counted)
METRICS = [
    ("Packets mailed", 35, "Expired/canceled \"why it didn't sell\" packets that went in the mail"),
    ("Doors knocked", 65, "Doors you knocked, answered or not"),
    ("FSBO reports", 12, "FSBO pricing reports delivered in person"),
    ("Buyer conversations", 15, "Two-way conversations with stalled buyers (not texts sent)"),
    ("Partners signed", 4, "Agent referral partners with a signed referral agreement"),
    ("Appointments", 5, "Listing or buyer appointments held"),
    ("Signed clients", 2, "Signed listing or buyer agreements"),
]
HOURS_TARGET = 4

ARIAL = "Arial"
F = Font(name=ARIAL, size=10)
FB = Font(name=ARIAL, size=10, bold=True)
F_TITLE = Font(name=ARIAL, size=14, bold=True)
F_NOTE = Font(name=ARIAL, size=9, italic=True, color="595959")
F_INPUT = Font(name=ARIAL, size=10, color="0000FF")
F_LINK = Font(name=ARIAL, size=10, color="008000")
F_HDR = Font(name=ARIAL, size=10, bold=True, color="FFFFFF")
FILL_HDR = PatternFill("solid", fgColor="1F3864")
FILL_INPUT = PatternFill("solid", fgColor="FFFF00")
FILL_TOTAL = PatternFill("solid", fgColor="D9E1F2")
FILL_GOOD = PatternFill("solid", fgColor="C6EFCE")
FILL_BAD = PatternFill("solid", fgColor="FFC7CE")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def style_row(ws, row, c1, c2, font=F, fill=None, border=BOX, align=None):
    for c in range(c1, c2 + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = font
        if fill:
            cell.fill = fill
        if border:
            cell.border = border
        if align:
            cell.alignment = align


def build():
    wb = Workbook()

    # ---------------- Dashboard ----------------
    d = wb.active
    d.title = "Dashboard"
    d["A1"] = "Left-Behind Clients: 90-Day KPI Dashboard"
    d["A1"].font = F_TITLE
    d["A2"] = "Yellow cells with blue text are inputs. Everything else is a formula. Log your numbers on the Weekly Log tab."
    d["A2"].font = F_NOTE

    settings = [
        ("Plan start", START, "date"),
        ("Plan length (days)", 90, "input"),
        ("Target hours per week", HOURS_TARGET, "input"),
        ("As of", "=MIN(TODAY(),B4+B5)", "dateformula"),
        ("Days elapsed", "=MAX(0,MIN(B5,B7-B4+1))", "formula"),
        ("% of plan elapsed", "=B8/B5", "pct"),
    ]
    for i, (label, val, kind) in enumerate(settings, start=4):
        d.cell(row=i, column=1, value=label).font = FB
        c = d.cell(row=i, column=2, value=val)
        c.border = BOX
        if kind in ("date", "input"):
            c.font, c.fill = F_INPUT, FILL_INPUT
        else:
            c.font = F
        if kind in ("date", "dateformula"):
            c.number_format = "mmm d, yyyy"
        if kind == "pct":
            c.number_format = "0%"
    d["C4"] = "Source: plan doc, Setup phase starts Nov 24, 2026"
    d["C5"] = "Ends Feb 22, 2027"
    d["C6"] = "4-hour routine, chosen Nov 24, 2026"
    d["C7"] = "Stops at the plan end date"
    for r in range(4, 8):
        d.cell(row=r, column=3).font = F_NOTE

    hdr_row = 11
    d.cell(row=10, column=1, value="Progress vs. target").font = FB
    headers = ["Metric", "90-day target", "Actual to date", "% of target", "On-pace number today",
               "Ahead (+) / behind (-)", "Status", "Weekly target", "How it's counted"]
    for j, h in enumerate(headers, start=1):
        d.cell(row=hdr_row, column=j, value=h)
    style_row(d, hdr_row, 1, len(headers), font=F_HDR, fill=FILL_HDR, align=CENTER)

    first = hdr_row + 1
    for i, (name, target, how) in enumerate(METRICS):
        r = first + i
        col = get_column_letter(4 + i)  # Weekly Log column D.. for this metric
        d.cell(row=r, column=1, value=name)
        d.cell(row=r, column=2, value=target)
        d.cell(row=r, column=3, value=f"='Weekly Log'!{col}{5 + WEEKS}")
        d.cell(row=r, column=4, value=f"=IF(B{r}=0,0,C{r}/B{r})")
        d.cell(row=r, column=5, value=f"=ROUND(B{r}*$B$9,1)")
        d.cell(row=r, column=6, value=f"=C{r}-E{r}")
        d.cell(row=r, column=7, value=f'=IF(C{r}>=B{r},"Hit",IF(C{r}>=E{r},"On pace","Behind"))')
        d.cell(row=r, column=8, value=f"=B{r}/($B$5/7)")
        d.cell(row=r, column=9, value=how)
        style_row(d, r, 1, 9)
        d.cell(row=r, column=2).font = F_INPUT
        d.cell(row=r, column=2).fill = FILL_INPUT
        d.cell(row=r, column=3).font = F_LINK
        d.cell(row=r, column=4).number_format = "0%"
        d.cell(row=r, column=5).number_format = "0.0"
        d.cell(row=r, column=6).number_format = "+0.0;-0.0;0.0"
        d.cell(row=r, column=8).number_format = "0.0"
        d.cell(row=r, column=9).alignment = WRAP
        d.cell(row=r, column=9).font = F_NOTE
    last = first + len(METRICS) - 1
    d.cell(row=first, column=2).comment = Comment(
        "Targets from the plan doc, scaled to the 4-hour week on Nov 24, 2026. Reset them at day 30 "
        "using the conversion rates below.", "Plan")
    status_rng = f"G{first}:G{last}"
    d.conditional_formatting.add(status_rng, FormulaRule(formula=[f'G{first}="Behind"'], fill=FILL_BAD))
    d.conditional_formatting.add(status_rng, FormulaRule(formula=[f'OR(G{first}="On pace",G{first}="Hit")'], fill=FILL_GOOD))

    # Conversion rates
    cr = last + 3
    d.cell(row=cr - 1, column=1, value="Conversion rates (use these to reset targets at day 30)").font = FB
    for j, h in enumerate(["Measure", "Value", "", "How it's calculated"], start=1):
        d.cell(row=cr, column=j, value=h)
    style_row(d, cr, 1, 4, font=F_HDR, fill=FILL_HDR, align=CENTER)
    P, K, FS, BC, PS, AP, SC = (f"C{first + i}" for i in range(7))
    hours_total = f"'Weekly Log'!K{5 + WEEKS}"
    conv = [
        ("Outreach touches", f"={P}+{K}+{FS}+{BC}", "0", "Packets + doors + FSBO reports + buyer conversations"),
        ("Appointments per 100 touches", f"=IF(B{cr+1}=0,0,{AP}/B{cr+1}*100)", "0.0", "Appointments / touches x 100"),
        ("Signed clients per appointment", f"=IF({AP}=0,0,{SC}/{AP})", "0%", "Signed clients / appointments"),
        ("Touches needed per signed client", f'=IF({SC}=0,"n/a yet",B{cr+1}/{SC})', "0", "Touches / signed clients"),
        ("Hours logged", f"={hours_total}", "0.0", "Sum of the Hours column on the Weekly Log"),
        ("Average hours per week", f"=IF($B$8=0,0,B{cr+5}/($B$8/7))", "0.0", "Hours logged / weeks elapsed (compare to target hours)"),
        ("Hours per appointment", f'=IF({AP}=0,"n/a yet",B{cr+5}/{AP})', "0.0", "Hours logged / appointments"),
        ("Projected signed clients at day 90", f"=IF($B$9=0,0,{SC}/$B$9)", "0.0", "Signed so far / % of plan elapsed (straight-line)"),
    ]
    for i, (label, formula, fmt, how) in enumerate(conv, start=1):
        r = cr + i
        d.cell(row=r, column=1, value=label)
        c = d.cell(row=r, column=2, value=formula)
        c.number_format = fmt
        d.cell(row=r, column=4, value=how)
        style_row(d, r, 1, 4)
        d.cell(row=r, column=4).font = F_NOTE

    widths = {"A": 34, "B": 15, "C": 15, "D": 13, "E": 15, "F": 15, "G": 11, "H": 12, "I": 48}
    for k, v in widths.items():
        d.column_dimensions[k].width = v
    d.row_dimensions[hdr_row].height = 30
    d.freeze_panes = "A4"

    # ---------------- Weekly Log ----------------
    w = wb.create_sheet("Weekly Log")
    w["A1"] = "Weekly Log"
    w["A1"].font = F_TITLE
    w["A2"] = "Every Sunday, type last week's counts in the yellow cells. Totals and the Dashboard update on their own."
    w["A2"].font = F_NOTE
    cols = ["Week", "Week starting", "Phase"] + [m[0] for m in METRICS] + ["Hours worked", "Notes"]
    for j, h in enumerate(cols, start=1):
        w.cell(row=4, column=j, value=h)
    style_row(w, 4, 1, len(cols), font=F_HDR, fill=FILL_HDR, align=CENTER)
    w.row_dimensions[4].height = 30

    for i in range(WEEKS):
        r = 5 + i
        w.cell(row=r, column=1, value=i + 1)
        if i == 0:
            w.cell(row=r, column=2, value="=Dashboard!B4")
        else:
            w.cell(row=r, column=2, value=f"=B{r-1}+7")
        # Setup = days 0-29, Volume = 30-59, Convert = 60-90 (Nov 24-Dec 23, Dec 24-Jan 22, Jan 23-Feb 22)
        w.cell(row=r, column=3, value=f'=IF(B{r}-Dashboard!$B$4<30,"Setup",IF(B{r}-Dashboard!$B$4<60,"Volume","Convert"))')
        style_row(w, r, 1, len(cols))
        w.cell(row=r, column=2).number_format = "mmm d"
        w.cell(row=r, column=2).font = F_LINK if i == 0 else F
        for c in range(4, 4 + len(METRICS) + 1):
            cell = w.cell(row=r, column=c)
            cell.font, cell.fill = F_INPUT, FILL_INPUT
            cell.alignment = Alignment(horizontal="center")
        w.cell(row=r, column=len(cols)).font = F_INPUT

    tot = 5 + WEEKS
    w.cell(row=tot, column=1, value="Total")
    for c in range(4, 4 + len(METRICS) + 1):
        L = get_column_letter(c)
        w.cell(row=tot, column=c, value=f"=SUM({L}5:{L}{tot-1})")
    style_row(w, tot, 1, len(cols), font=FB, fill=FILL_TOTAL)
    tgt = tot + 1
    w.cell(row=tgt, column=1, value="Weekly target")
    for i in range(len(METRICS)):
        c = 4 + i
        w.cell(row=tgt, column=c, value=f"=Dashboard!H{first + i}")
        w.cell(row=tgt, column=c).number_format = "0.0"
        w.cell(row=tgt, column=c).font = F_LINK
    w.cell(row=tgt, column=4 + len(METRICS), value="=Dashboard!B6").font = F_LINK
    style_row(w, tgt, 1, 3, font=FB)
    for c in range(4, len(cols) + 1):
        w.cell(row=tgt, column=c).border = BOX
    for r in (tot, tgt):
        for c in range(4, len(cols)):
            w.cell(row=r, column=c).alignment = Alignment(horizontal="center")

    dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                        error="Enter a number, 0 or more.", showErrorMessage=True)
    w.add_data_validation(dv)
    dv.add(f"D5:{get_column_letter(3 + len(METRICS) + 1)}{tot-1}")

    for c, width in zip(range(1, len(cols) + 1), [7, 13, 10] + [12] * len(METRICS) + [10, 40]):
        w.column_dimensions[get_column_letter(c)].width = width
    w.freeze_panes = "D5"

    # ---------------- How to use ----------------
    h = wb.create_sheet("How to use")
    h["A1"] = "How to use this tracker"
    h["A1"].font = F_TITLE
    lines = [
        "1. Every Sunday (15 min block), open Weekly Log and type last week's counts in the yellow cells for that week.",
        "2. Count only what happened: a packet counts when it's mailed, a conversation when the buyer answered back.",
        "3. Check the Dashboard. Status turns red (Behind) when you're under the on-pace number for today.",
        "4. At day 30 (about Dec 23), use the conversion rates to reset the 90-day targets in the yellow cells on the Dashboard.",
        "5. In the Convert phase, cut the segment with no appointments and move its hours to the best one.",
        "",
        "Color key: yellow fill + blue text = you type here. Black = formula. Green = pulled from another tab.",
        "",
        "Example week (format only; this row isn't counted):",
    ]
    for i, t in enumerate(lines, start=3):
        h.cell(row=i, column=1, value=t).font = F
    ex_hdr = 3 + len(lines)
    ex_cols = ["Week", "Week starting"] + [m[0] for m in METRICS] + ["Hours worked", "Notes"]
    ex_vals = [3, "Dec 8"] + [3, 6, 1, 1, 0, 1, 0] + [4.25, "Met R. at open house; listing appt Dec 15"]
    for j, (hd, v) in enumerate(zip(ex_cols, ex_vals), start=1):
        h.cell(row=ex_hdr, column=j, value=hd)
        h.cell(row=ex_hdr + 1, column=j, value=v)
    style_row(h, ex_hdr, 1, len(ex_cols), font=F_HDR, fill=FILL_HDR, align=CENTER)
    style_row(h, ex_hdr + 1, 1, len(ex_cols), font=Font(name=ARIAL, size=10, italic=True, color="808080"))
    h.column_dimensions["A"].width = 12
    for c in range(2, len(ex_cols) + 1):
        h.column_dimensions[get_column_letter(c)].width = 13
    h.column_dimensions[get_column_letter(len(ex_cols))].width = 40
    h.row_dimensions[ex_hdr].height = 30
    for i in range(3, 3 + len(lines)):
        h.cell(row=i, column=1).alignment = Alignment(wrap_text=False)

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
