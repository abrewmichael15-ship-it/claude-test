#!/usr/bin/env python3
"""
Phase 3: apply a transparent, weighted 0-100 propensity score to
data/processed/prospects.csv, using config/scoring_config.json for every
weight and threshold (no black-box model - each component below is a
plain arithmetic function you can read, argue with, and retune).

Writes:
  data/processed/prospects_scored.csv   (every prospect, scored)
  data/processed/top_500.csv            (Phase 4: top N, tiered A/B/C)
"""
import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CONFIG_PATH = REPO_ROOT / "config" / "scoring_config.json"

IN_CSV = PROCESSED_DIR / "prospects.csv"
SCORED_CSV = PROCESSED_DIR / "prospects_scored.csv"
TOP_CSV = PROCESSED_DIR / "top_500.csv"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def tenure_score(tenure_years, curve):
    if pd.isna(tenure_years):
        return 0.0
    t = float(tenure_years)
    if t < curve["zero_below_years"]:
        return 0.0
    if t < curve["ramp_to_full_by_years"]:
        span = curve["ramp_to_full_by_years"] - curve["zero_below_years"]
        return (t - curve["zero_below_years"]) / span
    if t <= curve["full_credit_until_years"]:
        return 1.0
    if t < curve["taper_to_years"]:
        span = curve["taper_to_years"] - curve["full_credit_until_years"]
        progress = (t - curve["full_credit_until_years"]) / span
        return 1.0 - progress * (1.0 - curve["taper_floor_score"])
    return curve["taper_floor_score"]


def percentile_rank(series):
    """0-1 rank, NaNs excluded from ranking and scored 0 (no data = no credit,
    not a guess at where they'd fall)."""
    ranked = series.rank(pct=True, na_option="keep")
    return ranked.fillna(0.0)


def main():
    if not IN_CSV.exists():
        raise SystemExit(f"Missing {IN_CSV} - run scripts/build_pipeline.py first.")

    config = load_config()
    df = pd.read_csv(IN_CSV)

    weights = config["weights"]
    curve = config["tenure_curve"]

    df["_tenure_component"] = df["tenure_years"].apply(lambda t: tenure_score(t, curve))
    df["_absentee_component"] = df["absentee_owner"].fillna(False).astype(bool).astype(float)

    if df["equity_proxy"].notna().any():
        df["_equity_component"] = percentile_rank(df["equity_proxy"])
    else:
        df["_equity_component"] = 0.0

    if df["open_violation_count"].notna().any():
        df["_violation_component"] = percentile_rank(df["open_violation_count"])
    else:
        df["_violation_component"] = 0.0

    base_score = (
        weights["tenure"] * df["_tenure_component"]
        + weights["absentee_owner"] * df["_absentee_component"]
        + weights["equity_proxy"] * df["_equity_component"]
        + weights["open_violations"] * df["_violation_component"]
    )

    recently_sold_penalty = df["recently_sold"].fillna(False).astype(bool).astype(int) * config[
        "recently_sold_penalty_points"
    ]
    tax_delinquent_bonus = df["tax_delinquent_or_upset_sale"].fillna(False).astype(bool).astype(
        int
    ) * config["tax_delinquent_bonus_points"]

    df["propensity_score"] = (base_score - recently_sold_penalty + tax_delinquent_bonus).clip(
        lower=0, upper=100
    ).round(1)

    df = df.drop(
        columns=[
            "_tenure_component",
            "_absentee_component",
            "_equity_component",
            "_violation_component",
        ]
    )

    df = df.sort_values("propensity_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    df.to_csv(SCORED_CSV, index=False)
    print(f"Wrote {len(df)} scored rows to {SCORED_CSV}")

    top_n = config["top_n"]
    a_cut = config["tier_cutoffs"]["A_top_n"]
    b_cut = config["tier_cutoffs"]["B_top_n"]

    top = df.head(top_n).copy()

    def tier_for_rank(rank):
        if rank <= a_cut:
            return "A"
        if rank <= b_cut:
            return "B"
        return "C"

    top["tier"] = top["rank"].apply(tier_for_rank)

    def build_tag(row):
        tags = [f"tier-{row['tier']}"]
        tags.append("absentee" if row["absentee_owner"] else "owner-occupant")
        if row["tax_delinquent_or_upset_sale"]:
            tags.append("tax-delinquent")
        if row["recently_sold"]:
            tags.append("recently-sold")
        return "|".join(tags)

    top["fub_tags"] = top.apply(build_tag, axis=1)

    top.to_csv(TOP_CSV, index=False)
    print(f"Wrote top {len(top)} to {TOP_CSV}")
    print()
    print("Tier counts:", top["tier"].value_counts().to_dict())
    print("Score range in top 500:", top["propensity_score"].min(), "-", top["propensity_score"].max())


if __name__ == "__main__":
    main()
