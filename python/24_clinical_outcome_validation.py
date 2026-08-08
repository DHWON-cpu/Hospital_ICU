# 24_clinical_outcome_validation.py

from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from pathlib import Path
import math
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact


# ============================================================
# Project paths
# ============================================================

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

PRIMARY_LABELS_INPUT = (
    RESULTS_DIR
    / "22B_pure_trajectory_clustering"
    / "22B_primary_cluster_labels.csv"
)

COMPLETE_LABELS_INPUT = (
    RESULTS_DIR
    / "22B_pure_trajectory_clustering"
    / "22B_complete_cluster_labels.csv"
)

OUTCOMES_INPUT = RESULTS_DIR / "14_outcome_labels.csv"

OUTPUT_DIR = RESULTS_DIR / "24_clinical_outcome_validation"

OUTPUT_PRIMARY_PATIENT_LEVEL = (
    OUTPUT_DIR / "24_primary_cluster_outcomes_patient_level.csv"
)
OUTPUT_COMPLETE_PATIENT_LEVEL = (
    OUTPUT_DIR / "24_complete_cluster_outcomes_patient_level.csv"
)
OUTPUT_PRIMARY_RATES = OUTPUT_DIR / "24_primary_outcome_rates.csv"
OUTPUT_COMPLETE_RATES = OUTPUT_DIR / "24_complete_outcome_rates.csv"
OUTPUT_PRIMARY_EFFECTS = OUTPUT_DIR / "24_primary_risk_effects.csv"
OUTPUT_COMPLETE_EFFECTS = OUTPUT_DIR / "24_complete_risk_effects.csv"
OUTPUT_SENSITIVITY_COMPARISON = (
    OUTPUT_DIR / "24_primary_complete_effect_comparison.csv"
)
OUTPUT_RISK_PLOT = OUTPUT_DIR / "24_mortality_rates_by_cluster.png"
OUTPUT_EFFECT_PLOT = OUTPUT_DIR / "24_relative_risk_forest_plot.png"
OUTPUT_REPORT = OUTPUT_DIR / "24_clinical_outcome_validation_summary.txt"


# ============================================================
# Outcomes
# ============================================================

OUTCOME_COLUMNS = [
    "mortality_1d",
    "mortality_3d",
    "mortality_7d",
]

OUTCOME_LABELS = {
    "mortality_1d": "1-day mortality",
    "mortality_3d": "3-day mortality",
    "mortality_7d": "7-day mortality",
}

REFERENCE_CLUSTER = 0
EXPOSURE_CLUSTER = 1


# ============================================================
# Utilities
# ============================================================

def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [
        PRIMARY_LABELS_INPUT,
        COMPLETE_LABELS_INPUT,
        OUTCOMES_INPUT,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    primary_labels = pd.read_csv(
        PRIMARY_LABELS_INPUT,
        low_memory=False,
    )
    complete_labels = pd.read_csv(
        COMPLETE_LABELS_INPUT,
        low_memory=False,
    )
    outcomes = pd.read_csv(
        OUTCOMES_INPUT,
        low_memory=False,
    )

    return primary_labels, complete_labels, outcomes


def validate_inputs(
    primary_labels: pd.DataFrame,
    complete_labels: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> None:
    for name, frame in [
        ("Primary labels", primary_labels),
        ("Complete labels", complete_labels),
    ]:
        required = {"stay_id", "trajectory_cluster"}
        missing = sorted(required.difference(frame.columns))

        if missing:
            raise ValueError(
                f"{name} is missing columns:\n"
                + "\n".join(f"  - {column}" for column in missing)
            )

        clusters = sorted(
            frame["trajectory_cluster"]
            .dropna()
            .unique()
            .tolist()
        )

        if clusters != [0, 1]:
            raise ValueError(
                f"{name} should contain clusters [0, 1], "
                f"but found {clusters}."
            )

    required_outcomes = {"stay_id", *OUTCOME_COLUMNS}
    missing_outcomes = sorted(
        required_outcomes.difference(outcomes.columns)
    )

    if missing_outcomes:
        raise ValueError(
            "Outcome file is missing columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing_outcomes
            )
        )


def merge_labels_outcomes(
    labels: pd.DataFrame,
    outcomes: pd.DataFrame,
    cohort_name: str,
) -> pd.DataFrame:
    merged = labels[
        ["stay_id", "trajectory_cluster"]
    ].merge(
        outcomes[["stay_id"] + OUTCOME_COLUMNS],
        on="stay_id",
        how="left",
        validate="one_to_one",
    )

    missing_outcomes = int(
        merged[OUTCOME_COLUMNS].isna().sum().sum()
    )

    if missing_outcomes:
        raise ValueError(
            f"{cohort_name} merge produced "
            f"{missing_outcomes:,} missing outcome values."
        )

    merged["cohort"] = cohort_name
    return merged


# ============================================================
# Statistical calculations
# ============================================================

def continuity_corrected_counts(
    a: int,
    b: int,
    c: int,
    d: int,
) -> tuple[float, float, float, float]:
    """
    Haldane-Anscombe correction only when any cell is zero.
    """
    if min(a, b, c, d) == 0:
        return (
            a + 0.5,
            b + 0.5,
            c + 0.5,
            d + 0.5,
        )

    return float(a), float(b), float(c), float(d)


def relative_risk_ci(
    a: int,
    b: int,
    c: int,
    d: int,
) -> tuple[float, float, float]:
    """
    a = events in cluster 1
    b = non-events in cluster 1
    c = events in cluster 0
    d = non-events in cluster 0
    """
    a2, b2, c2, d2 = continuity_corrected_counts(
        a, b, c, d
    )

    risk1 = a2 / (a2 + b2)
    risk0 = c2 / (c2 + d2)

    rr = risk1 / risk0

    se_log_rr = math.sqrt(
        (1 / a2)
        - (1 / (a2 + b2))
        + (1 / c2)
        - (1 / (c2 + d2))
    )

    lower = math.exp(math.log(rr) - 1.96 * se_log_rr)
    upper = math.exp(math.log(rr) + 1.96 * se_log_rr)

    return rr, lower, upper


def odds_ratio_ci(
    a: int,
    b: int,
    c: int,
    d: int,
) -> tuple[float, float, float]:
    a2, b2, c2, d2 = continuity_corrected_counts(
        a, b, c, d
    )

    odds_ratio = (a2 * d2) / (b2 * c2)
    se_log_or = math.sqrt(
        1 / a2 + 1 / b2 + 1 / c2 + 1 / d2
    )

    lower = math.exp(
        math.log(odds_ratio) - 1.96 * se_log_or
    )
    upper = math.exp(
        math.log(odds_ratio) + 1.96 * se_log_or
    )

    return odds_ratio, lower, upper


def risk_difference_ci(
    a: int,
    b: int,
    c: int,
    d: int,
) -> tuple[float, float, float]:
    n1 = a + b
    n0 = c + d

    risk1 = a / n1
    risk0 = c / n0
    rd = risk1 - risk0

    se = math.sqrt(
        risk1 * (1 - risk1) / n1
        + risk0 * (1 - risk0) / n0
    )

    lower = rd - 1.96 * se
    upper = rd + 1.96 * se

    return rd, lower, upper


def calculate_outcome_rates(
    merged: pd.DataFrame,
    cohort_name: str,
) -> pd.DataFrame:
    rows = []

    for cluster in [0, 1]:
        group = merged.loc[
            merged["trajectory_cluster"].eq(cluster)
        ]

        for outcome in OUTCOME_COLUMNS:
            events = int(group[outcome].sum())
            total = len(group)

            rows.append(
                {
                    "cohort": cohort_name,
                    "trajectory_cluster": cluster,
                    "outcome": outcome,
                    "outcome_label": OUTCOME_LABELS[outcome],
                    "n": total,
                    "events": events,
                    "non_events": total - events,
                    "rate": events / total,
                    "rate_pct": events / total * 100,
                }
            )

    return pd.DataFrame(rows)


def calculate_risk_effects(
    merged: pd.DataFrame,
    cohort_name: str,
) -> pd.DataFrame:
    rows = []

    for outcome in OUTCOME_COLUMNS:
        cluster1 = merged.loc[
            merged["trajectory_cluster"].eq(EXPOSURE_CLUSTER)
        ]
        cluster0 = merged.loc[
            merged["trajectory_cluster"].eq(REFERENCE_CLUSTER)
        ]

        a = int(cluster1[outcome].sum())
        b = len(cluster1) - a
        c = int(cluster0[outcome].sum())
        d = len(cluster0) - c

        risk1 = a / (a + b)
        risk0 = c / (c + d)

        rr, rr_lower, rr_upper = relative_risk_ci(
            a, b, c, d
        )
        odds_ratio, or_lower, or_upper = odds_ratio_ci(
            a, b, c, d
        )
        rd, rd_lower, rd_upper = risk_difference_ci(
            a, b, c, d
        )

        _, fisher_p = fisher_exact(
            [[a, b], [c, d]],
            alternative="two-sided",
        )

        rows.append(
            {
                "cohort": cohort_name,
                "outcome": outcome,
                "outcome_label": OUTCOME_LABELS[outcome],
                "reference_cluster": REFERENCE_CLUSTER,
                "exposure_cluster": EXPOSURE_CLUSTER,
                "cluster_0_n": len(cluster0),
                "cluster_0_events": c,
                "cluster_0_rate": risk0,
                "cluster_0_rate_pct": risk0 * 100,
                "cluster_1_n": len(cluster1),
                "cluster_1_events": a,
                "cluster_1_rate": risk1,
                "cluster_1_rate_pct": risk1 * 100,
                "risk_difference": rd,
                "risk_difference_pct_points": rd * 100,
                "risk_difference_ci_lower": rd_lower,
                "risk_difference_ci_upper": rd_upper,
                "relative_risk": rr,
                "relative_risk_ci_lower": rr_lower,
                "relative_risk_ci_upper": rr_upper,
                "odds_ratio": odds_ratio,
                "odds_ratio_ci_lower": or_lower,
                "odds_ratio_ci_upper": or_upper,
                "fisher_exact_p_value": float(fisher_p),
            }
        )

    return pd.DataFrame(rows)


def build_sensitivity_comparison(
    primary_effects: pd.DataFrame,
    complete_effects: pd.DataFrame,
) -> pd.DataFrame:
    primary = primary_effects[
        [
            "outcome",
            "cluster_0_rate_pct",
            "cluster_1_rate_pct",
            "risk_difference_pct_points",
            "relative_risk",
            "relative_risk_ci_lower",
            "relative_risk_ci_upper",
            "odds_ratio",
            "fisher_exact_p_value",
        ]
    ].copy()

    primary = primary.add_prefix("primary_").rename(
        columns={"primary_outcome": "outcome"}
    )

    complete = complete_effects[
        [
            "outcome",
            "cluster_0_rate_pct",
            "cluster_1_rate_pct",
            "risk_difference_pct_points",
            "relative_risk",
            "relative_risk_ci_lower",
            "relative_risk_ci_upper",
            "odds_ratio",
            "fisher_exact_p_value",
        ]
    ].copy()

    complete = complete.add_prefix("complete_").rename(
        columns={"complete_outcome": "outcome"}
    )

    comparison = primary.merge(
        complete,
        on="outcome",
        how="inner",
        validate="one_to_one",
    )

    comparison["relative_risk_difference"] = (
        comparison["complete_relative_risk"]
        - comparison["primary_relative_risk"]
    )

    comparison["risk_difference_pct_point_difference"] = (
        comparison[
            "complete_risk_difference_pct_points"
        ]
        - comparison[
            "primary_risk_difference_pct_points"
        ]
    )

    return comparison


# ============================================================
# Visualization
# ============================================================

def create_mortality_rate_plot(
    primary_rates: pd.DataFrame,
) -> None:
    pivot = primary_rates.pivot(
        index="outcome_label",
        columns="trajectory_cluster",
        values="rate_pct",
    )

    pivot = pivot.loc[
        [
            OUTCOME_LABELS["mortality_1d"],
            OUTCOME_LABELS["mortality_3d"],
            OUTCOME_LABELS["mortality_7d"],
        ]
    ]

    x = np.arange(len(pivot))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 6))

    bars0 = ax.bar(
        x - width / 2,
        pivot[0],
        width,
        label="Cluster 0",
    )
    bars1 = ax.bar(
        x + width / 2,
        pivot[1],
        width,
        label="Cluster 1",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index)
    ax.set_ylabel("Mortality rate (%)")
    ax.set_title(
        "Clinical Outcome Validation of Pure Trajectory Clusters"
    )
    ax.legend()

    for bars in [bars0, bars1]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.2f}%",
                (
                    bar.get_x() + bar.get_width() / 2,
                    height,
                ),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    fig.tight_layout()
    fig.savefig(OUTPUT_RISK_PLOT, dpi=300)
    plt.close(fig)


def create_relative_risk_plot(
    primary_effects: pd.DataFrame,
) -> None:
    plot_df = primary_effects.copy()
    y = np.arange(len(plot_df))

    rr = plot_df["relative_risk"].to_numpy()
    lower = plot_df["relative_risk_ci_lower"].to_numpy()
    upper = plot_df["relative_risk_ci_upper"].to_numpy()

    xerr = np.vstack([rr - lower, upper - rr])

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.errorbar(
        rr,
        y,
        xerr=xerr,
        fmt="o",
        capsize=5,
    )

    ax.axvline(1.0, linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["outcome_label"])
    ax.set_xlabel("Relative risk: Cluster 1 vs Cluster 0")
    ax.set_title("Relative Risk of Mortality by Trajectory Cluster")

    fig.tight_layout()
    fig.savefig(OUTPUT_EFFECT_PLOT, dpi=300)
    plt.close(fig)


# ============================================================
# Reporting
# ============================================================

def determine_risk_interpretation(
    primary_effects: pd.DataFrame,
) -> str:
    seven_day = primary_effects.loc[
        primary_effects["outcome"].eq("mortality_7d")
    ].iloc[0]

    rr = seven_day["relative_risk"]
    lower = seven_day["relative_risk_ci_lower"]

    if rr > 1 and lower > 1:
        return (
            "Cluster 1 has significantly higher 7-day mortality "
            "than Cluster 0."
        )

    if rr < 1 and seven_day["relative_risk_ci_upper"] < 1:
        return (
            "Cluster 1 has significantly lower 7-day mortality "
            "than Cluster 0."
        )

    return (
        "The 7-day mortality difference is not statistically "
        "conclusive."
    )


def build_report(
    primary_merged: pd.DataFrame,
    complete_merged: pd.DataFrame,
    primary_effects: pd.DataFrame,
    complete_effects: pd.DataFrame,
) -> str:
    interpretation = determine_risk_interpretation(
        primary_effects
    )

    lines = [
        "=" * 80,
        "STEP 24. CLINICAL OUTCOME VALIDATION OF PURE TRAJECTORY PHENOTYPES",
        "=" * 80,
        "",
        f"Primary cohort rows: {len(primary_merged):,}",
        f"Complete sensitivity cohort rows: {len(complete_merged):,}",
        "",
        "Reference definition:",
        "- Cluster 0 is the reference group",
        "- Cluster 1 is the exposure group",
        "",
        "Primary cohort mortality comparison:",
    ]

    for row in primary_effects.itertuples(index=False):
        lines.append(
            f"- {row.outcome_label}: "
            f"C0={row.cluster_0_rate_pct:.2f}% "
            f"({row.cluster_0_events}/{row.cluster_0_n}), "
            f"C1={row.cluster_1_rate_pct:.2f}% "
            f"({row.cluster_1_events}/{row.cluster_1_n}), "
            f"RR={row.relative_risk:.3f} "
            f"(95% CI {row.relative_risk_ci_lower:.3f}–"
            f"{row.relative_risk_ci_upper:.3f}), "
            f"RD={row.risk_difference_pct_points:.2f} percentage points, "
            f"OR={row.odds_ratio:.3f}, "
            f"p={row.fisher_exact_p_value:.3e}"
        )

    lines.extend(
        [
            "",
            "Complete-cohort sensitivity comparison:",
        ]
    )

    for row in complete_effects.itertuples(index=False):
        lines.append(
            f"- {row.outcome_label}: "
            f"C0={row.cluster_0_rate_pct:.2f}%, "
            f"C1={row.cluster_1_rate_pct:.2f}%, "
            f"RR={row.relative_risk:.3f} "
            f"(95% CI {row.relative_risk_ci_lower:.3f}–"
            f"{row.relative_risk_ci_upper:.3f})"
        )

    lines.extend(
        [
            "",
            "Primary clinical interpretation:",
            f"- {interpretation}",
            "",
            "Naming rule:",
            (
                "Recovery-like, worsening, low-risk, or high-risk "
                "phenotype names should be assigned only when the "
                "trajectory direction and outcome gradient agree."
            ),
            (
                "This step validates association, not causation. "
                "Cluster membership should not be interpreted as a "
                "treatment recommendation."
            ),
            "",
            "=" * 80,
        ]
    )

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 80)
    print(
        "Step 24. Clinical Outcome Validation of "
        "Pure Trajectory Phenotypes"
    )
    print("=" * 80)

    ensure_output_directory()

    print("Loading cluster labels and outcomes...")
    primary_labels, complete_labels, outcomes = load_inputs()
    validate_inputs(
        primary_labels,
        complete_labels,
        outcomes,
    )

    print("Merging primary cluster labels with outcomes...")
    primary_merged = merge_labels_outcomes(
        primary_labels,
        outcomes,
        "Primary",
    )

    print("Merging complete-cohort labels with outcomes...")
    complete_merged = merge_labels_outcomes(
        complete_labels,
        outcomes,
        "Complete",
    )

    print("Calculating cluster-specific outcome rates...")
    primary_rates = calculate_outcome_rates(
        primary_merged,
        "Primary",
    )
    complete_rates = calculate_outcome_rates(
        complete_merged,
        "Complete",
    )

    print("Calculating risk differences, relative risks, and odds ratios...")
    primary_effects = calculate_risk_effects(
        primary_merged,
        "Primary",
    )
    complete_effects = calculate_risk_effects(
        complete_merged,
        "Complete",
    )

    sensitivity_comparison = build_sensitivity_comparison(
        primary_effects,
        complete_effects,
    )

    print("Creating figures...")
    create_mortality_rate_plot(primary_rates)
    create_relative_risk_plot(primary_effects)

    report = build_report(
        primary_merged,
        complete_merged,
        primary_effects,
        complete_effects,
    )

    primary_merged.to_csv(
        OUTPUT_PRIMARY_PATIENT_LEVEL,
        index=False,
    )
    complete_merged.to_csv(
        OUTPUT_COMPLETE_PATIENT_LEVEL,
        index=False,
    )
    primary_rates.to_csv(
        OUTPUT_PRIMARY_RATES,
        index=False,
    )
    complete_rates.to_csv(
        OUTPUT_COMPLETE_RATES,
        index=False,
    )
    primary_effects.to_csv(
        OUTPUT_PRIMARY_EFFECTS,
        index=False,
    )
    complete_effects.to_csv(
        OUTPUT_COMPLETE_EFFECTS,
        index=False,
    )
    sensitivity_comparison.to_csv(
        OUTPUT_SENSITIVITY_COMPARISON,
        index=False,
    )
    OUTPUT_REPORT.write_text(report, encoding="utf-8")

    print("")
    print("Primary cohort risk effects:")
    print(
        primary_effects[
            [
                "outcome_label",
                "cluster_0_rate_pct",
                "cluster_1_rate_pct",
                "risk_difference_pct_points",
                "relative_risk",
                "relative_risk_ci_lower",
                "relative_risk_ci_upper",
                "odds_ratio",
                "fisher_exact_p_value",
            ]
        ].to_string(index=False)
    )

    print("")
    print("Complete-cohort sensitivity effects:")
    print(
        complete_effects[
            [
                "outcome_label",
                "cluster_0_rate_pct",
                "cluster_1_rate_pct",
                "relative_risk",
                "relative_risk_ci_lower",
                "relative_risk_ci_upper",
            ]
        ].to_string(index=False)
    )

    print("")
    print("Saved:")
    for path in [
        OUTPUT_PRIMARY_PATIENT_LEVEL,
        OUTPUT_COMPLETE_PATIENT_LEVEL,
        OUTPUT_PRIMARY_RATES,
        OUTPUT_COMPLETE_RATES,
        OUTPUT_PRIMARY_EFFECTS,
        OUTPUT_COMPLETE_EFFECTS,
        OUTPUT_SENSITIVITY_COMPARISON,
        OUTPUT_RISK_PLOT,
        OUTPUT_EFFECT_PLOT,
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
