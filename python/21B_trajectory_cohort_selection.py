# 21B_trajectory_cohort_selection.py

"""
input_content : results/13_temporal_features.csv (long trajectory features),
                results/14_outcome_labels.csv (optional, for eligible-vs-excluded comparison)
output_content : results/21B_trajectory_cohort_selection/ — eligibility flags, eligible long/wide matrices,
                 winsorized / median-imputed / robust-scaled 8-feature clustering matrix
                 (lactate first_value + clearance_pct; creatinine/WBC/platelet first_value + percent_change),
                 cohort counts, exclusion reasons, winsorization bounds, outcome comparison, text report
calls : pandas, numpy, sklearn SimpleImputer(median), sklearn RobustScaler
side effect : creates the 21B output directory, writes 10+ CSVs and a .txt report, prints cohort tables to stdout
responsibility : Step 21B — apply the eligibility rule (valid lactate trajectory required, plus >=2 valid
                 trajectories among creatinine/WBC/platelet), yielding 24,799 eligible stays, and emit the
                 audited, preprocessed feature matrix for K-means phenotyping while documenting the selection
                 bias toward repeatedly tested (more intensively monitored) patients.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler


# ============================================================
# Project paths
# ============================================================

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

INPUT_CSV = RESULTS_DIR / "13_temporal_features.csv"
OUTCOME_CSV = RESULTS_DIR / "14_outcome_labels.csv"

OUTPUT_DIR = RESULTS_DIR / "21B_trajectory_cohort_selection"

OUTPUT_FLAGS = OUTPUT_DIR / "21B_trajectory_eligibility_flags.csv"
OUTPUT_ELIGIBLE_LONG = OUTPUT_DIR / "21B_eligible_trajectory_long.csv"
OUTPUT_ELIGIBLE_WIDE_RAW = OUTPUT_DIR / "21B_eligible_trajectory_wide_raw.csv"
OUTPUT_ELIGIBLE_WINSORIZED = OUTPUT_DIR / "21B_eligible_trajectory_winsorized.csv"
OUTPUT_ELIGIBLE_IMPUTED = OUTPUT_DIR / "21B_eligible_trajectory_imputed.csv"
OUTPUT_ELIGIBLE_SCALED = OUTPUT_DIR / "21B_eligible_trajectory_scaled.csv"
OUTPUT_COUNTS = OUTPUT_DIR / "21B_cohort_counts.csv"
OUTPUT_EXCLUSION_REASONS = OUTPUT_DIR / "21B_exclusion_reasons.csv"
OUTPUT_AVAILABILITY = OUTPUT_DIR / "21B_biomarker_trajectory_availability.csv"
OUTPUT_OUTCOME_COMPARISON = OUTPUT_DIR / "21B_eligible_vs_excluded_outcomes.csv"
OUTPUT_WINSOR_BOUNDS = OUTPUT_DIR / "21B_winsorization_bounds.csv"
OUTPUT_REPORT = OUTPUT_DIR / "21B_trajectory_cohort_selection_report.txt"


# ============================================================
# Cohort definition
# ============================================================

PRIMARY_BIOMARKERS = [
    "Lactate",
    "Creatinine",
    "White Blood Cells",
    "Platelet Count",
]

SECONDARY_BIOMARKERS = [
    "Creatinine",
    "White Blood Cells",
    "Platelet Count",
]

MIN_SECONDARY_TRAJECTORIES = 2

# Final primary clustering features:
# initial state + normalized change
PRIMARY_FEATURE_MAP = {
    "Lactate": [
        "first_value",
        "lactate_clearance_pct",
    ],
    "Creatinine": [
        "first_value",
        "percent_change",
    ],
    "White Blood Cells": [
        "first_value",
        "percent_change",
    ],
    "Platelet Count": [
        "first_value",
        "percent_change",
    ],
}

WINSOR_LOWER = 0.01
WINSOR_UPPER = 0.99


# ============================================================
# Loading and validation
# ============================================================

def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_temporal_features() -> pd.DataFrame:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_CSV}\n"
            "Run Step 13 first."
        )

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    required = {
        "stay_id",
        "label",
        "first_value",
        "percent_change",
        "lactate_clearance_pct",
        "change_available",
    }

    missing = sorted(required.difference(df.columns))

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f"  - {column}" for column in missing)
        )

    return df


def load_outcomes() -> pd.DataFrame | None:
    if not OUTCOME_CSV.exists():
        return None

    outcomes = pd.read_csv(OUTCOME_CSV, low_memory=False)

    if "stay_id" not in outcomes.columns:
        return None

    return outcomes.drop_duplicates(subset=["stay_id"])


# ============================================================
# Eligibility logic
# ============================================================

def build_trajectory_availability(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build one row per stay with trajectory availability flags.

    A biomarker trajectory is considered available when:
    - change_available == 1
    - the normalized change feature is non-missing
    """
    selected = df.loc[df["label"].isin(PRIMARY_BIOMARKERS)].copy()

    selected["trajectory_available"] = 0

    lactate_mask = selected["label"].eq("Lactate")
    other_mask = ~lactate_mask

    selected.loc[
        lactate_mask
        & selected["change_available"].eq(1)
        & selected["lactate_clearance_pct"].notna(),
        "trajectory_available",
    ] = 1

    selected.loc[
        other_mask
        & selected["change_available"].eq(1)
        & selected["percent_change"].notna(),
        "trajectory_available",
    ] = 1

    availability = selected.pivot_table(
        index="stay_id",
        columns="label",
        values="trajectory_available",
        aggfunc="max",
        fill_value=0,
    ).reset_index()

    for biomarker in PRIMARY_BIOMARKERS:
        if biomarker not in availability.columns:
            availability[biomarker] = 0

    availability = availability[
        ["stay_id"] + PRIMARY_BIOMARKERS
    ].copy()

    availability = availability.rename(
        columns={
            "Lactate": "lactate_trajectory_available",
            "Creatinine": "creatinine_trajectory_available",
            "White Blood Cells": "wbc_trajectory_available",
            "Platelet Count": "platelet_trajectory_available",
        }
    )

    availability["secondary_trajectory_count"] = (
        availability["creatinine_trajectory_available"]
        + availability["wbc_trajectory_available"]
        + availability["platelet_trajectory_available"]
    )

    availability["total_trajectory_count"] = (
        availability["lactate_trajectory_available"]
        + availability["secondary_trajectory_count"]
    )

    availability["eligible_trajectory_cohort"] = (
        availability["lactate_trajectory_available"].eq(1)
        & availability["secondary_trajectory_count"].ge(
            MIN_SECONDARY_TRAJECTORIES
        )
    ).astype(int)

    availability["exclusion_reason"] = np.select(
        [
            availability["lactate_trajectory_available"].eq(0),
            availability["secondary_trajectory_count"].lt(
                MIN_SECONDARY_TRAJECTORIES
            ),
        ],
        [
            "No valid lactate trajectory",
            (
                "Fewer than 2 valid trajectories among "
                "creatinine, WBC, and platelet"
            ),
        ],
        default="Eligible",
    )

    return availability


def create_availability_summary(flags: pd.DataFrame) -> pd.DataFrame:
    total = len(flags)

    rows = [
        {
            "criterion": "Any stay evaluated",
            "n": total,
            "pct": 100.0,
        },
        {
            "criterion": "Lactate trajectory available",
            "n": int(flags["lactate_trajectory_available"].sum()),
            "pct": float(
                flags["lactate_trajectory_available"].mean() * 100
            ),
        },
        {
            "criterion": "Creatinine trajectory available",
            "n": int(flags["creatinine_trajectory_available"].sum()),
            "pct": float(
                flags["creatinine_trajectory_available"].mean() * 100
            ),
        },
        {
            "criterion": "WBC trajectory available",
            "n": int(flags["wbc_trajectory_available"].sum()),
            "pct": float(flags["wbc_trajectory_available"].mean() * 100),
        },
        {
            "criterion": "Platelet trajectory available",
            "n": int(flags["platelet_trajectory_available"].sum()),
            "pct": float(
                flags["platelet_trajectory_available"].mean() * 100
            ),
        },
        {
            "criterion": (
                "At least 2 secondary trajectories available"
            ),
            "n": int(
                flags["secondary_trajectory_count"]
                .ge(MIN_SECONDARY_TRAJECTORIES)
                .sum()
            ),
            "pct": float(
                flags["secondary_trajectory_count"]
                .ge(MIN_SECONDARY_TRAJECTORIES)
                .mean()
                * 100
            ),
        },
        {
            "criterion": "Final trajectory-eligible cohort",
            "n": int(flags["eligible_trajectory_cohort"].sum()),
            "pct": float(
                flags["eligible_trajectory_cohort"].mean() * 100
            ),
        },
    ]

    return pd.DataFrame(rows)


def create_exclusion_summary(flags: pd.DataFrame) -> pd.DataFrame:
    return (
        flags.groupby("exclusion_reason", as_index=False)
        .agg(n=("stay_id", "size"))
        .assign(
            pct=lambda x: x["n"] / len(flags) * 100
        )
        .sort_values("n", ascending=False)
        .reset_index(drop=True)
    )


# ============================================================
# Eligible feature matrix
# ============================================================

def normalize_feature_name(label: str, feature: str) -> str:
    label_name = (
        label.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )

    if label == "Lactate" and feature == "lactate_clearance_pct":
        return "lactate_clearance_pct"

    return f"{label_name}_{feature}"


def build_eligible_long(
    df: pd.DataFrame,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    eligible_ids = set(
        flags.loc[
            flags["eligible_trajectory_cohort"].eq(1),
            "stay_id",
        ]
    )

    selected = df.loc[
        df["stay_id"].isin(eligible_ids)
        & df["label"].isin(PRIMARY_BIOMARKERS)
    ].copy()

    rows = []

    for biomarker, features in PRIMARY_FEATURE_MAP.items():
        biomarker_df = selected.loc[
            selected["label"].eq(biomarker)
        ].copy()

        for feature in features:
            frame = biomarker_df[
                ["stay_id", "label", feature]
            ].copy()

            frame = frame.rename(
                columns={feature: "feature_value"}
            )

            frame["feature"] = feature
            frame["feature_name"] = normalize_feature_name(
                biomarker,
                feature,
            )

            rows.append(frame)

    result = pd.concat(rows, ignore_index=True)

    return result


def build_wide_matrix(eligible_long: pd.DataFrame) -> pd.DataFrame:
    wide = eligible_long.pivot(
        index="stay_id",
        columns="feature_name",
        values="feature_value",
    ).reset_index()

    wide.columns.name = None

    expected_features = [
        normalize_feature_name(biomarker, feature)
        for biomarker, features in PRIMARY_FEATURE_MAP.items()
        for feature in features
    ]

    for feature in expected_features:
        if feature not in wide.columns:
            wide[feature] = np.nan

    return wide[["stay_id"] + expected_features]


def winsorize(
    wide: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = wide.copy()
    rows = []

    for column in result.columns:
        if column == "stay_id":
            continue

        series = pd.to_numeric(result[column], errors="coerce")
        lower = float(series.quantile(WINSOR_LOWER))
        upper = float(series.quantile(WINSOR_UPPER))

        n_low = int((series < lower).sum())
        n_high = int((series > upper).sum())

        result[column] = series.clip(lower=lower, upper=upper)

        rows.append(
            {
                "feature": column,
                "lower_bound": lower,
                "upper_bound": upper,
                "n_clipped_low": n_low,
                "n_clipped_high": n_high,
            }
        )

    return result, pd.DataFrame(rows)


def impute_and_scale(
    winsorized: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_columns = [
        col for col in winsorized.columns if col != "stay_id"
    ]

    imputer = SimpleImputer(strategy="median")
    imputed_array = imputer.fit_transform(
        winsorized[feature_columns]
    )

    imputed = pd.DataFrame(
        imputed_array,
        columns=feature_columns,
        index=winsorized.index,
    )
    imputed.insert(0, "stay_id", winsorized["stay_id"].values)

    scaler = RobustScaler()
    scaled_array = scaler.fit_transform(imputed[feature_columns])

    scaled = pd.DataFrame(
        scaled_array,
        columns=feature_columns,
        index=imputed.index,
    )
    scaled.insert(0, "stay_id", imputed["stay_id"].values)

    return imputed, scaled


# ============================================================
# Eligible vs excluded outcome comparison
# ============================================================

def compare_outcomes(
    flags: pd.DataFrame,
    outcomes: pd.DataFrame | None,
) -> pd.DataFrame:
    if outcomes is None:
        return pd.DataFrame()

    merged = flags.merge(
        outcomes,
        on="stay_id",
        how="left",
    )

    outcome_columns = [
        column
        for column in [
            "mortality_1d",
            "mortality_3d",
            "mortality_7d",
        ]
        if column in merged.columns
    ]

    rows = []

    for eligible_value, group_name in [
        (1, "Trajectory eligible"),
        (0, "Excluded"),
    ]:
        group = merged.loc[
            merged["eligible_trajectory_cohort"].eq(
                eligible_value
            )
        ]

        row = {
            "group": group_name,
            "n": len(group),
        }

        for outcome in outcome_columns:
            row[f"{outcome}_n"] = int(group[outcome].sum())
            row[f"{outcome}_rate"] = float(group[outcome].mean())

        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# Report
# ============================================================

def build_report(
    temporal_df: pd.DataFrame,
    flags: pd.DataFrame,
    counts: pd.DataFrame,
    exclusions: pd.DataFrame,
    wide: pd.DataFrame,
) -> str:
    eligible_n = int(flags["eligible_trajectory_cohort"].sum())
    excluded_n = len(flags) - eligible_n

    lines = [
        "=" * 68,
        "STEP 21B. TRAJECTORY-ELIGIBLE COHORT SELECTION",
        "=" * 68,
        "",
        f"Input file: {INPUT_CSV}",
        f"Input temporal rows: {len(temporal_df):,}",
        f"ICU stays evaluated: {len(flags):,}",
        "",
        "Primary eligibility rule:",
        "1. Valid lactate trajectory is mandatory.",
        (
            "2. At least two valid trajectories must also be available "
            "among creatinine, white blood cells, and platelet count."
        ),
        "3. Therefore, each included patient has at least three valid "
        "biochemical trajectories.",
        "",
        f"Trajectory-eligible cohort: {eligible_n:,}",
        f"Excluded cohort: {excluded_n:,}",
        f"Eligibility rate: {eligible_n / len(flags) * 100:.2f}%",
        "",
        "Criterion counts:",
    ]

    for row in counts.itertuples(index=False):
        lines.append(
            f"- {row.criterion}: {row.n:,} ({row.pct:.2f}%)"
        )

    lines.extend(["", "Exclusion reasons:"])

    for row in exclusions.itertuples(index=False):
        lines.append(
            f"- {row.exclusion_reason}: "
            f"{row.n:,} ({row.pct:.2f}%)"
        )

    lines.extend(
        [
            "",
            f"Eligible clustering matrix shape: {wide.shape}",
            "",
            "Final primary clustering features:",
            "- lactate_first_value",
            "- lactate_clearance_pct",
            "- creatinine_first_value",
            "- creatinine_percent_change",
            "- white_blood_cells_first_value",
            "- white_blood_cells_percent_change",
            "- platelet_count_first_value",
            "- platelet_count_percent_change",
            "",
            "Important methodological note:",
            (
                "The trajectory-eligible cohort is not the full ICU "
                "population. It preferentially includes patients with "
                "repeated biochemical testing. This may enrich for more "
                "severely ill or more intensively monitored patients."
            ),
            (
                "Eligibility selection must therefore be reported explicitly, "
                "and eligible versus excluded patients should be compared "
                "before phenotype clustering."
            ),
            "",
            "=" * 68,
        ]
    )

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 68)
    print("Step 21B. Trajectory-Eligible Cohort Selection")
    print("=" * 68)

    ensure_output_directory()

    print(f"Loading: {INPUT_CSV}")
    temporal_df = load_temporal_features()
    print(f"Loaded: {temporal_df.shape}")

    print("Building biomarker trajectory availability flags...")
    flags = build_trajectory_availability(temporal_df)

    counts = create_availability_summary(flags)
    exclusions = create_exclusion_summary(flags)

    eligible_n = int(flags["eligible_trajectory_cohort"].sum())
    print(f"ICU stays evaluated: {len(flags):,}")
    print(f"Trajectory-eligible stays: {eligible_n:,}")
    print(
        f"Eligibility rate: "
        f"{eligible_n / len(flags) * 100:.2f}%"
    )

    print("Creating eligible trajectory feature matrix...")
    eligible_long = build_eligible_long(
        temporal_df,
        flags,
    )
    wide = build_wide_matrix(eligible_long)

    print(f"Eligible wide matrix: {wide.shape}")

    print("Winsorizing eligible cohort features...")
    winsorized, winsor_bounds = winsorize(wide)

    print("Median-imputing residual missing values...")
    imputed, scaled = impute_and_scale(winsorized)

    outcomes = load_outcomes()
    outcome_comparison = compare_outcomes(flags, outcomes)

    flags.to_csv(OUTPUT_FLAGS, index=False)
    eligible_long.to_csv(OUTPUT_ELIGIBLE_LONG, index=False)
    wide.to_csv(OUTPUT_ELIGIBLE_WIDE_RAW, index=False)
    winsorized.to_csv(OUTPUT_ELIGIBLE_WINSORIZED, index=False)
    imputed.to_csv(OUTPUT_ELIGIBLE_IMPUTED, index=False)
    scaled.to_csv(OUTPUT_ELIGIBLE_SCALED, index=False)
    counts.to_csv(OUTPUT_COUNTS, index=False)
    exclusions.to_csv(OUTPUT_EXCLUSION_REASONS, index=False)
    counts.to_csv(OUTPUT_AVAILABILITY, index=False)
    winsor_bounds.to_csv(OUTPUT_WINSOR_BOUNDS, index=False)

    if not outcome_comparison.empty:
        outcome_comparison.to_csv(
            OUTPUT_OUTCOME_COMPARISON,
            index=False,
        )

    report = build_report(
        temporal_df=temporal_df,
        flags=flags,
        counts=counts,
        exclusions=exclusions,
        wide=wide,
    )
    OUTPUT_REPORT.write_text(report, encoding="utf-8")

    print("")
    print("Eligibility criteria:")
    print("- Lactate trajectory required")
    print(
        "- At least 2 trajectories required among "
        "Creatinine, WBC, and Platelet"
    )

    print("")
    print("Cohort counts:")
    print(counts.to_string(index=False))

    print("")
    print("Exclusion reasons:")
    print(exclusions.to_string(index=False))

    if not outcome_comparison.empty:
        print("")
        print("Eligible vs excluded outcomes:")
        print(outcome_comparison.to_string(index=False))

    print("")
    print("Saved:")
    for path in [
        OUTPUT_FLAGS,
        OUTPUT_ELIGIBLE_LONG,
        OUTPUT_ELIGIBLE_WIDE_RAW,
        OUTPUT_ELIGIBLE_WINSORIZED,
        OUTPUT_ELIGIBLE_IMPUTED,
        OUTPUT_ELIGIBLE_SCALED,
        OUTPUT_COUNTS,
        OUTPUT_EXCLUSION_REASONS,
        OUTPUT_REPORT,
    ]:
        print(path)

    print("")
    print("Completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        sys.exit(1)
