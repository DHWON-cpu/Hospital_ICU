# 21C_trajectory_sensitivity_cohort.py

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler


PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

TEMPORAL_INPUT = RESULTS_DIR / "13_temporal_features.csv"
ELIGIBILITY_INPUT = (
    RESULTS_DIR
    / "21B_trajectory_cohort_selection"
    / "21B_trajectory_eligibility_flags.csv"
)
OUTCOME_INPUT = RESULTS_DIR / "14_outcome_labels.csv"

OUTPUT_DIR = RESULTS_DIR / "21C_trajectory_sensitivity_cohort"

OUTPUT_FLAGS = OUTPUT_DIR / "21C_primary_and_complete_cohort_flags.csv"
OUTPUT_PATTERNS = OUTPUT_DIR / "21C_trajectory_availability_patterns.csv"
OUTPUT_COUNTS = OUTPUT_DIR / "21C_cohort_counts.csv"
OUTPUT_OUTCOMES = OUTPUT_DIR / "21C_primary_vs_complete_outcomes.csv"
OUTPUT_COMPLETE_RAW = OUTPUT_DIR / "21C_complete_trajectory_wide_raw.csv"
OUTPUT_COMPLETE_WINSORIZED = OUTPUT_DIR / "21C_complete_trajectory_winsorized.csv"
OUTPUT_COMPLETE_SCALED = OUTPUT_DIR / "21C_complete_trajectory_scaled.csv"
OUTPUT_BOUNDS = OUTPUT_DIR / "21C_complete_winsorization_bounds.csv"
OUTPUT_REPORT = OUTPUT_DIR / "21C_trajectory_sensitivity_cohort_report.txt"

PRIMARY_FEATURE_MAP = {
    "Lactate": ["first_value", "lactate_clearance_pct"],
    "Creatinine": ["first_value", "percent_change"],
    "White Blood Cells": ["first_value", "percent_change"],
    "Platelet Count": ["first_value", "percent_change"],
}

WINSOR_LOWER = 0.01
WINSOR_UPPER = 0.99


def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    if not TEMPORAL_INPUT.exists():
        raise FileNotFoundError(f"Missing input: {TEMPORAL_INPUT}")

    if not ELIGIBILITY_INPUT.exists():
        raise FileNotFoundError(
            f"Missing input: {ELIGIBILITY_INPUT}\nRun Step 21B first."
        )

    temporal = pd.read_csv(TEMPORAL_INPUT, low_memory=False)
    flags = pd.read_csv(ELIGIBILITY_INPUT, low_memory=False)

    outcomes = None
    if OUTCOME_INPUT.exists():
        outcomes = pd.read_csv(OUTCOME_INPUT, low_memory=False)
        outcomes = outcomes.drop_duplicates(subset=["stay_id"])

    return temporal, flags, outcomes


def add_complete_cohort_flag(flags: pd.DataFrame) -> pd.DataFrame:
    required = {
        "stay_id",
        "eligible_trajectory_cohort",
        "lactate_trajectory_available",
        "creatinine_trajectory_available",
        "wbc_trajectory_available",
        "platelet_trajectory_available",
    }

    missing = sorted(required.difference(flags.columns))
    if missing:
        raise ValueError(
            "Eligibility file is missing required columns:\n"
            + "\n".join(f"  - {column}" for column in missing)
        )

    result = flags.copy()

    result["complete_four_trajectory_cohort"] = (
        result["lactate_trajectory_available"].eq(1)
        & result["creatinine_trajectory_available"].eq(1)
        & result["wbc_trajectory_available"].eq(1)
        & result["platelet_trajectory_available"].eq(1)
    ).astype(int)

    result["trajectory_pattern"] = (
        "L"
        + result["lactate_trajectory_available"].astype(str)
        + "_C"
        + result["creatinine_trajectory_available"].astype(str)
        + "_W"
        + result["wbc_trajectory_available"].astype(str)
        + "_P"
        + result["platelet_trajectory_available"].astype(str)
    )

    result["cohort_group"] = np.select(
        [
            result["complete_four_trajectory_cohort"].eq(1),
            result["eligible_trajectory_cohort"].eq(1),
        ],
        [
            "Complete four-trajectory cohort",
            "Primary eligible only",
        ],
        default="Excluded from primary cohort",
    )

    return result


def create_pattern_counts(flags: pd.DataFrame) -> pd.DataFrame:
    return (
        flags.groupby(
            [
                "trajectory_pattern",
                "lactate_trajectory_available",
                "creatinine_trajectory_available",
                "wbc_trajectory_available",
                "platelet_trajectory_available",
                "eligible_trajectory_cohort",
                "complete_four_trajectory_cohort",
            ],
            as_index=False,
        )
        .agg(n=("stay_id", "size"))
        .assign(pct=lambda x: x["n"] / len(flags) * 100)
        .sort_values("n", ascending=False)
        .reset_index(drop=True)
    )


def create_cohort_counts(flags: pd.DataFrame) -> pd.DataFrame:
    total = len(flags)
    primary_n = int(flags["eligible_trajectory_cohort"].sum())
    complete_n = int(flags["complete_four_trajectory_cohort"].sum())
    primary_only_n = primary_n - complete_n

    return pd.DataFrame(
        [
            {
                "cohort": "All evaluated stays",
                "n": total,
                "pct_of_all": 100.0,
                "pct_of_primary": np.nan,
            },
            {
                "cohort": "Primary eligible cohort",
                "n": primary_n,
                "pct_of_all": primary_n / total * 100,
                "pct_of_primary": 100.0,
            },
            {
                "cohort": "Complete four-trajectory cohort",
                "n": complete_n,
                "pct_of_all": complete_n / total * 100,
                "pct_of_primary": complete_n / primary_n * 100,
            },
            {
                "cohort": "Primary eligible only",
                "n": primary_only_n,
                "pct_of_all": primary_only_n / total * 100,
                "pct_of_primary": primary_only_n / primary_n * 100,
            },
        ]
    )


def compare_outcomes(
    flags: pd.DataFrame,
    outcomes: pd.DataFrame | None,
) -> pd.DataFrame:
    if outcomes is None:
        return pd.DataFrame()

    merged = flags.merge(outcomes, on="stay_id", how="left")
    mortality_columns = [
        column
        for column in ["mortality_1d", "mortality_3d", "mortality_7d"]
        if column in merged.columns
    ]

    groups = [
        ("Primary eligible cohort", merged["eligible_trajectory_cohort"].eq(1)),
        (
            "Complete four-trajectory cohort",
            merged["complete_four_trajectory_cohort"].eq(1),
        ),
        (
            "Primary eligible only",
            merged["eligible_trajectory_cohort"].eq(1)
            & merged["complete_four_trajectory_cohort"].eq(0),
        ),
        (
            "Excluded from primary cohort",
            merged["eligible_trajectory_cohort"].eq(0),
        ),
    ]

    rows = []

    for group_name, mask in groups:
        group = merged.loc[mask]
        row = {"group": group_name, "n": len(group)}

        for outcome in mortality_columns:
            row[f"{outcome}_n"] = int(group[outcome].fillna(0).sum())
            row[f"{outcome}_rate"] = float(group[outcome].mean())

        rows.append(row)

    return pd.DataFrame(rows)


def normalize_feature_name(label: str, feature: str) -> str:
    if label == "Lactate" and feature == "lactate_clearance_pct":
        return "lactate_clearance_pct"

    label_name = (
        label.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )
    return f"{label_name}_{feature}"


def build_complete_wide(
    temporal: pd.DataFrame,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    complete_ids = set(
        flags.loc[
            flags["complete_four_trajectory_cohort"].eq(1),
            "stay_id",
        ]
    )

    selected = temporal.loc[
        temporal["stay_id"].isin(complete_ids)
        & temporal["label"].isin(PRIMARY_FEATURE_MAP)
    ].copy()

    frames = []

    for biomarker, features in PRIMARY_FEATURE_MAP.items():
        biomarker_df = selected.loc[selected["label"].eq(biomarker)]

        for feature in features:
            frame = biomarker_df[["stay_id", feature]].copy()
            frame = frame.rename(columns={feature: "feature_value"})
            frame["feature_name"] = normalize_feature_name(
                biomarker,
                feature,
            )
            frames.append(frame)

    long_df = pd.concat(frames, ignore_index=True)

    duplicates = long_df.duplicated(
        subset=["stay_id", "feature_name"]
    ).sum()

    if duplicates:
        raise ValueError(
            f"Found {duplicates:,} duplicated stay-feature rows."
        )

    wide = long_df.pivot(
        index="stay_id",
        columns="feature_name",
        values="feature_value",
    ).reset_index()

    wide.columns.name = None

    expected = [
        normalize_feature_name(biomarker, feature)
        for biomarker, features in PRIMARY_FEATURE_MAP.items()
        for feature in features
    ]

    for feature in expected:
        if feature not in wide.columns:
            wide[feature] = np.nan

    wide = wide[["stay_id"] + expected]

    missing_total = int(wide[expected].isna().sum().sum())
    if missing_total:
        raise ValueError(
            "Complete four-trajectory cohort contains residual missing "
            f"primary features: {missing_total:,}"
        )

    return wide


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

        rows.append(
            {
                "feature": column,
                "lower_bound": lower,
                "upper_bound": upper,
                "n_clipped_low": int((series < lower).sum()),
                "n_clipped_high": int((series > upper).sum()),
            }
        )

        result[column] = series.clip(lower=lower, upper=upper)

    return result, pd.DataFrame(rows)


def scale_complete(winsorized: pd.DataFrame) -> pd.DataFrame:
    feature_columns = [
        column for column in winsorized.columns if column != "stay_id"
    ]

    scaler = RobustScaler()
    scaled_values = scaler.fit_transform(winsorized[feature_columns])

    scaled = pd.DataFrame(
        scaled_values,
        columns=feature_columns,
        index=winsorized.index,
    )
    scaled.insert(0, "stay_id", winsorized["stay_id"].values)

    return scaled


def build_report(
    flags: pd.DataFrame,
    counts: pd.DataFrame,
    patterns: pd.DataFrame,
    outcomes: pd.DataFrame,
    complete_wide: pd.DataFrame,
) -> str:
    primary_n = int(flags["eligible_trajectory_cohort"].sum())
    complete_n = int(flags["complete_four_trajectory_cohort"].sum())
    primary_only_n = primary_n - complete_n

    lines = [
        "=" * 70,
        "STEP 21C. PRIMARY AND COMPLETE TRAJECTORY COHORTS",
        "=" * 70,
        "",
        "Primary cohort definition:",
        "- Valid lactate trajectory required",
        "- At least two valid trajectories among creatinine, WBC, platelet",
        "",
        "Sensitivity cohort definition:",
        "- Valid trajectories required for all four biomarkers",
        "- Lactate, creatinine, WBC, and platelet all complete",
        "",
        f"Primary eligible cohort: {primary_n:,}",
        f"Complete four-trajectory cohort: {complete_n:,}",
        f"Primary eligible only: {primary_only_n:,}",
        (
            "Complete cohort as percentage of primary cohort: "
            f"{complete_n / primary_n * 100:.2f}%"
        ),
        "",
        f"Complete clustering matrix shape: {complete_wide.shape}",
        "",
        "Cohort counts:",
    ]

    for row in counts.itertuples(index=False):
        lines.append(
            f"- {row.cohort}: {row.n:,} "
            f"({row.pct_of_all:.2f}% of all)"
        )

    lines.extend(["", "Most common availability patterns:"])

    for row in patterns.head(10).itertuples(index=False):
        lines.append(
            f"- {row.trajectory_pattern}: "
            f"{row.n:,} ({row.pct:.2f}%)"
        )

    if not outcomes.empty:
        lines.extend(["", "Outcome comparison:"])

        for _, row in outcomes.iterrows():
            parts = [f"- {row['group']}: n={int(row['n']):,}"]
            for outcome in [
                "mortality_1d_rate",
                "mortality_3d_rate",
                "mortality_7d_rate",
            ]:
                if outcome in row and pd.notna(row[outcome]):
                    parts.append(
                        f"{outcome.replace('_rate', '')}="
                        f"{row[outcome] * 100:.2f}%"
                    )
            lines.append(", ".join(parts))

    lines.extend(
        [
            "",
            "Analysis role:",
            (
                "The primary eligible cohort is used for the main "
                "trajectory clustering analysis."
            ),
            (
                "The complete four-trajectory cohort is used for "
                "sensitivity analysis without trajectory-feature imputation."
            ),
            (
                "Robust phenotypes should show similar centroid directions "
                "and outcome gradients in both cohorts."
            ),
            "",
            "=" * 70,
        ]
    )

    return "\n".join(lines)


def main() -> None:
    print("=" * 70)
    print("Step 21C. Primary and Complete Trajectory Cohorts")
    print("=" * 70)

    ensure_output_directory()

    temporal, flags, outcomes = load_inputs()
    flags = add_complete_cohort_flag(flags)

    patterns = create_pattern_counts(flags)
    counts = create_cohort_counts(flags)
    outcome_comparison = compare_outcomes(flags, outcomes)

    primary_n = int(flags["eligible_trajectory_cohort"].sum())
    complete_n = int(flags["complete_four_trajectory_cohort"].sum())

    print(f"Primary eligible cohort: {primary_n:,}")
    print(f"Complete four-trajectory cohort: {complete_n:,}")
    print(
        "Complete cohort share of primary: "
        f"{complete_n / primary_n * 100:.2f}%"
    )

    print("Building complete-cohort feature matrix...")
    complete_wide = build_complete_wide(temporal, flags)
    print(f"Complete wide matrix: {complete_wide.shape}")

    print("Winsorizing complete-cohort features...")
    complete_winsorized, winsor_bounds = winsorize(complete_wide)

    print("Robust-scaling complete-cohort features...")
    complete_scaled = scale_complete(complete_winsorized)

    flags.to_csv(OUTPUT_FLAGS, index=False)
    patterns.to_csv(OUTPUT_PATTERNS, index=False)
    counts.to_csv(OUTPUT_COUNTS, index=False)
    complete_wide.to_csv(OUTPUT_COMPLETE_RAW, index=False)
    complete_winsorized.to_csv(
        OUTPUT_COMPLETE_WINSORIZED,
        index=False,
    )
    complete_scaled.to_csv(OUTPUT_COMPLETE_SCALED, index=False)
    winsor_bounds.to_csv(OUTPUT_BOUNDS, index=False)

    if not outcome_comparison.empty:
        outcome_comparison.to_csv(OUTPUT_OUTCOMES, index=False)

    report = build_report(
        flags=flags,
        counts=counts,
        patterns=patterns,
        outcomes=outcome_comparison,
        complete_wide=complete_wide,
    )
    OUTPUT_REPORT.write_text(report, encoding="utf-8")

    print("")
    print("Cohort counts:")
    print(counts.to_string(index=False))

    print("")
    print("Top trajectory availability patterns:")
    print(patterns.head(10).to_string(index=False))

    if not outcome_comparison.empty:
        print("")
        print("Outcome comparison:")
        print(outcome_comparison.to_string(index=False))

    print("")
    print("Saved:")
    for path in [
        OUTPUT_FLAGS,
        OUTPUT_PATTERNS,
        OUTPUT_COUNTS,
        OUTPUT_COMPLETE_RAW,
        OUTPUT_COMPLETE_WINSORIZED,
        OUTPUT_COMPLETE_SCALED,
        OUTPUT_BOUNDS,
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
