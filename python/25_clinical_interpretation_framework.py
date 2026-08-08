# 25_clinical_interpretation_framework.py

from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ============================================================
# Project paths
# ============================================================

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

SIGNATURE_INPUT = (
    RESULTS_DIR
    / "23B_pure_trajectory_characterization"
    / "23B_pure_trajectory_signature.csv"
)

PROFILE_INPUT = (
    RESULTS_DIR
    / "23B_pure_trajectory_characterization"
    / "23B_cluster_profile_table.csv"
)

RISK_EFFECTS_INPUT = (
    RESULTS_DIR
    / "24_clinical_outcome_validation"
    / "24_primary_risk_effects.csv"
)

SENSITIVITY_EFFECTS_INPUT = (
    RESULTS_DIR
    / "24_clinical_outcome_validation"
    / "24_complete_risk_effects.csv"
)

OUTPUT_DIR = RESULTS_DIR / "25_clinical_interpretation_framework"

OUTPUT_FRAMEWORK = OUTPUT_DIR / "25_trajectory_phenotype_framework.csv"
OUTPUT_DASHBOARD = OUTPUT_DIR / "25_dashboard_display_table.csv"
OUTPUT_CLINICAL_SUMMARY = OUTPUT_DIR / "25_clinical_interpretation_summary.csv"
OUTPUT_ZONE_RULES = OUTPUT_DIR / "25_risk_zone_rules.csv"
OUTPUT_FIGURE = OUTPUT_DIR / "25_clinical_trajectory_framework.png"
OUTPUT_REPORT = OUTPUT_DIR / "25_clinical_interpretation_framework_report.txt"


# ============================================================
# Final phenotype naming
# ============================================================

PHENOTYPE_NAMES = {
    0: "Recovery-like biochemical trajectory",
    1: "Renal-inflammatory worsening trajectory",
}

PHENOTYPE_CODES = {
    0: "RBT",
    1: "RIWT",
}

RISK_ZONES = {
    0: "Lower-risk trajectory zone",
    1: "Higher-risk trajectory zone",
}

CLINICAL_MESSAGES = {
    0: (
        "Lactate clearance with stable creatinine and decreasing WBC. "
        "Platelet count shows a modest decline. This pattern was associated "
        "with lower short-term mortality than Cluster 1."
    ),
    1: (
        "Absent median lactate clearance with increasing creatinine and WBC. "
        "Platelet count also increased. This pattern was associated with "
        "higher 1-day, 3-day, and 7-day mortality."
    ),
}

CAUTION_MESSAGES = {
    0: (
        "Lower risk does not mean clinically safe. Continue interpretation "
        "with the patient's diagnosis, treatment response, and organ-support needs."
    ),
    1: (
        "This is an observational high-risk trajectory signal, not a diagnosis "
        "or treatment instruction. It should prompt clinical review rather than "
        "automatic intervention."
    ),
}


# ============================================================
# Utility functions
# ============================================================

def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [
        SIGNATURE_INPUT,
        PROFILE_INPUT,
        RISK_EFFECTS_INPUT,
        SENSITIVITY_EFFECTS_INPUT,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    signature = pd.read_csv(SIGNATURE_INPUT, low_memory=False)
    profile = pd.read_csv(PROFILE_INPUT, low_memory=False)
    risks = pd.read_csv(RISK_EFFECTS_INPUT, low_memory=False)
    sensitivity = pd.read_csv(
        SENSITIVITY_EFFECTS_INPUT,
        low_memory=False,
    )

    return signature, profile, risks, sensitivity


def validate_inputs(
    signature: pd.DataFrame,
    profile: pd.DataFrame,
    risks: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> None:
    required_signature = {
        "feature",
        "display_name",
        "cluster_0_median",
        "cluster_1_median",
        "cluster_0_direction",
        "cluster_1_direction",
    }

    required_profile = {
        "trajectory_cluster",
        "cluster_n",
        "cluster_pct",
    }

    required_risk = {
        "outcome",
        "outcome_label",
        "cluster_0_rate_pct",
        "cluster_1_rate_pct",
        "relative_risk",
        "relative_risk_ci_lower",
        "relative_risk_ci_upper",
        "risk_difference_pct_points",
    }

    for name, frame, required in [
        ("Signature", signature, required_signature),
        ("Profile", profile, required_profile),
        ("Primary risk effects", risks, required_risk),
        ("Sensitivity risk effects", sensitivity, required_risk),
    ]:
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                f"{name} input is missing columns:\n"
                + "\n".join(f"  - {column}" for column in missing)
            )

    clusters = sorted(profile["trajectory_cluster"].tolist())
    if clusters != [0, 1]:
        raise ValueError(
            f"Expected trajectory clusters [0, 1], found {clusters}."
        )


def value_for_cluster(
    signature: pd.DataFrame,
    feature: str,
    cluster: int,
) -> float:
    row = signature.loc[signature["feature"].eq(feature)]

    if row.empty:
        return np.nan

    return float(row.iloc[0][f"cluster_{cluster}_median"])


def direction_for_cluster(
    signature: pd.DataFrame,
    feature: str,
    cluster: int,
) -> str:
    row = signature.loc[signature["feature"].eq(feature)]

    if row.empty:
        return "Unknown"

    return str(row.iloc[0][f"cluster_{cluster}_direction"])


# ============================================================
# Framework construction
# ============================================================

def build_framework(
    signature: pd.DataFrame,
    profile: pd.DataFrame,
    risks: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for cluster in [0, 1]:
        profile_row = profile.loc[
            profile["trajectory_cluster"].eq(cluster)
        ].iloc[0]

        row = {
            "trajectory_cluster": cluster,
            "phenotype_code": PHENOTYPE_CODES[cluster],
            "phenotype_name": PHENOTYPE_NAMES[cluster],
            "risk_zone": RISK_ZONES[cluster],
            "cluster_n": int(profile_row["cluster_n"]),
            "cluster_pct": float(profile_row["cluster_pct"]),
            "lactate_clearance_pct": value_for_cluster(
                signature,
                "lactate_clearance_pct",
                cluster,
            ),
            "lactate_direction": direction_for_cluster(
                signature,
                "lactate_clearance_pct",
                cluster,
            ),
            "creatinine_percent_change": value_for_cluster(
                signature,
                "creatinine_percent_change",
                cluster,
            ),
            "creatinine_direction": direction_for_cluster(
                signature,
                "creatinine_percent_change",
                cluster,
            ),
            "wbc_percent_change": value_for_cluster(
                signature,
                "white_blood_cells_percent_change",
                cluster,
            ),
            "wbc_direction": direction_for_cluster(
                signature,
                "white_blood_cells_percent_change",
                cluster,
            ),
            "platelet_percent_change": value_for_cluster(
                signature,
                "platelet_count_percent_change",
                cluster,
            ),
            "platelet_direction": direction_for_cluster(
                signature,
                "platelet_count_percent_change",
                cluster,
            ),
            "clinical_interpretation": CLINICAL_MESSAGES[cluster],
            "clinical_caution": CAUTION_MESSAGES[cluster],
        }

        for outcome in ["mortality_1d", "mortality_3d", "mortality_7d"]:
            risk_row = risks.loc[risks["outcome"].eq(outcome)].iloc[0]

            row[f"{outcome}_rate_pct"] = float(
                risk_row[f"cluster_{cluster}_rate_pct"]
            )

        rows.append(row)

    framework = pd.DataFrame(rows)

    seven_day = risks.loc[
        risks["outcome"].eq("mortality_7d")
    ].iloc[0]

    framework["cluster_1_vs_0_7d_relative_risk"] = float(
        seven_day["relative_risk"]
    )
    framework["cluster_1_vs_0_7d_rr_ci_lower"] = float(
        seven_day["relative_risk_ci_lower"]
    )
    framework["cluster_1_vs_0_7d_rr_ci_upper"] = float(
        seven_day["relative_risk_ci_upper"]
    )
    framework["cluster_1_vs_0_7d_risk_difference_pp"] = float(
        seven_day["risk_difference_pct_points"]
    )

    sensitivity_7d = sensitivity.loc[
        sensitivity["outcome"].eq("mortality_7d")
    ].iloc[0]

    framework["complete_cohort_7d_relative_risk"] = float(
        sensitivity_7d["relative_risk"]
    )

    return framework


def build_dashboard_table(
    framework: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for row in framework.itertuples(index=False):
        rows.append(
            {
                "cluster": row.trajectory_cluster,
                "display_title": (
                    f"{row.phenotype_code}: {row.phenotype_name}"
                ),
                "risk_zone": row.risk_zone,
                "prevalence": f"{row.cluster_pct:.1f}%",
                "lactate": (
                    f"{row.lactate_clearance_pct:+.1f}% "
                    f"({row.lactate_direction})"
                ),
                "creatinine": (
                    f"{row.creatinine_percent_change:+.1f}% "
                    f"({row.creatinine_direction})"
                ),
                "wbc": (
                    f"{row.wbc_percent_change:+.1f}% "
                    f"({row.wbc_direction})"
                ),
                "platelet": (
                    f"{row.platelet_percent_change:+.1f}% "
                    f"({row.platelet_direction})"
                ),
                "mortality_1d": f"{row.mortality_1d_rate_pct:.2f}%",
                "mortality_3d": f"{row.mortality_3d_rate_pct:.2f}%",
                "mortality_7d": f"{row.mortality_7d_rate_pct:.2f}%",
                "clinical_message": row.clinical_interpretation,
                "caution": row.clinical_caution,
            }
        )

    return pd.DataFrame(rows)


def build_zone_rules(
    framework: pd.DataFrame,
) -> pd.DataFrame:
    """
    These are descriptive centroid-based rules, not validated diagnostic cutoffs.
    """
    rows = []

    for row in framework.itertuples(index=False):
        rows.append(
            {
                "trajectory_cluster": row.trajectory_cluster,
                "phenotype_name": row.phenotype_name,
                "risk_zone": row.risk_zone,
                "descriptive_rule": (
                    f"Lactate clearance around "
                    f"{row.lactate_clearance_pct:.1f}%; "
                    f"creatinine change around "
                    f"{row.creatinine_percent_change:.1f}%; "
                    f"WBC change around "
                    f"{row.wbc_percent_change:.1f}%; "
                    f"platelet change around "
                    f"{row.platelet_percent_change:.1f}%."
                ),
                "rule_status": (
                    "Centroid description only; not a clinical threshold"
                ),
            }
        )

    return pd.DataFrame(rows)


def build_clinical_summary(
    framework: pd.DataFrame,
) -> pd.DataFrame:
    lower = framework.loc[
        framework["trajectory_cluster"].eq(0)
    ].iloc[0]

    higher = framework.loc[
        framework["trajectory_cluster"].eq(1)
    ].iloc[0]

    return pd.DataFrame(
        [
            {
                "comparison": "Phenotype prevalence",
                "lower_risk_trajectory": (
                    f"{lower['cluster_n']:,} "
                    f"({lower['cluster_pct']:.2f}%)"
                ),
                "higher_risk_trajectory": (
                    f"{higher['cluster_n']:,} "
                    f"({higher['cluster_pct']:.2f}%)"
                ),
            },
            {
                "comparison": "Biochemical movement",
                "lower_risk_trajectory": (
                    "Lactate clearance, stable creatinine, "
                    "decreasing WBC, modest platelet decline"
                ),
                "higher_risk_trajectory": (
                    "Absent lactate clearance, rising creatinine, "
                    "rising WBC, rising platelet"
                ),
            },
            {
                "comparison": "1-day mortality",
                "lower_risk_trajectory": (
                    f"{lower['mortality_1d_rate_pct']:.2f}%"
                ),
                "higher_risk_trajectory": (
                    f"{higher['mortality_1d_rate_pct']:.2f}%"
                ),
            },
            {
                "comparison": "3-day mortality",
                "lower_risk_trajectory": (
                    f"{lower['mortality_3d_rate_pct']:.2f}%"
                ),
                "higher_risk_trajectory": (
                    f"{higher['mortality_3d_rate_pct']:.2f}%"
                ),
            },
            {
                "comparison": "7-day mortality",
                "lower_risk_trajectory": (
                    f"{lower['mortality_7d_rate_pct']:.2f}%"
                ),
                "higher_risk_trajectory": (
                    f"{higher['mortality_7d_rate_pct']:.2f}%"
                ),
            },
            {
                "comparison": "7-day relative risk",
                "lower_risk_trajectory": "Reference",
                "higher_risk_trajectory": (
                    f"{higher['cluster_1_vs_0_7d_relative_risk']:.3f} "
                    f"(95% CI "
                    f"{higher['cluster_1_vs_0_7d_rr_ci_lower']:.3f}–"
                    f"{higher['cluster_1_vs_0_7d_rr_ci_upper']:.3f})"
                ),
            },
        ]
    )


# ============================================================
# Visualization
# ============================================================

def create_framework_figure(
    framework: pd.DataFrame,
) -> None:
    features = [
        "Lactate clearance",
        "Creatinine change",
        "WBC change",
        "Platelet change",
    ]

    cluster0 = framework.loc[
        framework["trajectory_cluster"].eq(0)
    ].iloc[0]

    cluster1 = framework.loc[
        framework["trajectory_cluster"].eq(1)
    ].iloc[0]

    values0 = [
        cluster0["lactate_clearance_pct"],
        cluster0["creatinine_percent_change"],
        cluster0["wbc_percent_change"],
        cluster0["platelet_percent_change"],
    ]

    values1 = [
        cluster1["lactate_clearance_pct"],
        cluster1["creatinine_percent_change"],
        cluster1["wbc_percent_change"],
        cluster1["platelet_percent_change"],
    ]

    x = np.arange(len(features))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 7))

    bars0 = ax.bar(
        x - width / 2,
        values0,
        width,
        label=PHENOTYPE_NAMES[0],
    )
    bars1 = ax.bar(
        x + width / 2,
        values1,
        width,
        label=PHENOTYPE_NAMES[1],
    )

    ax.axhline(0, linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(features)
    ax.set_ylabel("Median percent change / clearance")
    ax.set_title(
        "Clinical Framework for Pure Biochemical Trajectory Phenotypes"
    )
    ax.legend()

    for bars in [bars0, bars1]:
        for bar in bars:
            value = bar.get_height()
            ax.annotate(
                f"{value:+.1f}%",
                (
                    bar.get_x() + bar.get_width() / 2,
                    value,
                ),
                xytext=(0, 4 if value >= 0 else -14),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    text = (
        f"7-day mortality: "
        f"{cluster0['mortality_7d_rate_pct']:.2f}% vs "
        f"{cluster1['mortality_7d_rate_pct']:.2f}%\n"
        f"RR={cluster1['cluster_1_vs_0_7d_relative_risk']:.3f} "
        f"(95% CI "
        f"{cluster1['cluster_1_vs_0_7d_rr_ci_lower']:.3f}–"
        f"{cluster1['cluster_1_vs_0_7d_rr_ci_upper']:.3f})"
    )

    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox={"boxstyle": "round", "alpha": 0.15},
    )

    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE, dpi=300)
    plt.close(fig)


# ============================================================
# Report
# ============================================================

def build_report(
    framework: pd.DataFrame,
) -> str:
    cluster0 = framework.loc[
        framework["trajectory_cluster"].eq(0)
    ].iloc[0]

    cluster1 = framework.loc[
        framework["trajectory_cluster"].eq(1)
    ].iloc[0]

    lines = [
        "=" * 82,
        "STEP 25. CLINICAL INTERPRETATION AND TRAJECTORY PHENOTYPE FRAMEWORK",
        "=" * 82,
        "",
        "Final phenotype framework:",
        "",
        f"Cluster 0 — {cluster0['phenotype_name']}",
        f"- Code: {cluster0['phenotype_code']}",
        f"- Zone: {cluster0['risk_zone']}",
        (
            f"- Prevalence: {cluster0['cluster_n']:,} "
            f"({cluster0['cluster_pct']:.2f}%)"
        ),
        (
            f"- Lactate clearance: "
            f"{cluster0['lactate_clearance_pct']:.2f}%"
        ),
        (
            f"- Creatinine change: "
            f"{cluster0['creatinine_percent_change']:.2f}%"
        ),
        (
            f"- WBC change: "
            f"{cluster0['wbc_percent_change']:.2f}%"
        ),
        (
            f"- Platelet change: "
            f"{cluster0['platelet_percent_change']:.2f}%"
        ),
        (
            f"- Mortality: 1-day "
            f"{cluster0['mortality_1d_rate_pct']:.2f}%, "
            f"3-day {cluster0['mortality_3d_rate_pct']:.2f}%, "
            f"7-day {cluster0['mortality_7d_rate_pct']:.2f}%"
        ),
        f"- Interpretation: {cluster0['clinical_interpretation']}",
        "",
        f"Cluster 1 — {cluster1['phenotype_name']}",
        f"- Code: {cluster1['phenotype_code']}",
        f"- Zone: {cluster1['risk_zone']}",
        (
            f"- Prevalence: {cluster1['cluster_n']:,} "
            f"({cluster1['cluster_pct']:.2f}%)"
        ),
        (
            f"- Lactate clearance: "
            f"{cluster1['lactate_clearance_pct']:.2f}%"
        ),
        (
            f"- Creatinine change: "
            f"{cluster1['creatinine_percent_change']:.2f}%"
        ),
        (
            f"- WBC change: "
            f"{cluster1['wbc_percent_change']:.2f}%"
        ),
        (
            f"- Platelet change: "
            f"{cluster1['platelet_percent_change']:.2f}%"
        ),
        (
            f"- Mortality: 1-day "
            f"{cluster1['mortality_1d_rate_pct']:.2f}%, "
            f"3-day {cluster1['mortality_3d_rate_pct']:.2f}%, "
            f"7-day {cluster1['mortality_7d_rate_pct']:.2f}%"
        ),
        f"- Interpretation: {cluster1['clinical_interpretation']}",
        "",
        "Risk comparison:",
        (
            f"- Cluster 1 vs Cluster 0 7-day RR: "
            f"{cluster1['cluster_1_vs_0_7d_relative_risk']:.3f} "
            f"(95% CI "
            f"{cluster1['cluster_1_vs_0_7d_rr_ci_lower']:.3f}–"
            f"{cluster1['cluster_1_vs_0_7d_rr_ci_upper']:.3f})"
        ),
        (
            f"- Absolute 7-day risk difference: "
            f"{cluster1['cluster_1_vs_0_7d_risk_difference_pp']:.2f} "
            "percentage points"
        ),
        (
            f"- Complete-cohort 7-day RR: "
            f"{cluster1['complete_cohort_7d_relative_risk']:.3f}"
        ),
        "",
        "ICU presentation concept:",
        (
            "- Display the current trajectory phenotype, four biomarker "
            "directions, and observed outcome association."
        ),
        (
            "- Use 'lower-risk' and 'higher-risk' rather than 'safe' and "
            "'dangerous'; neither cluster constitutes a clinical guarantee."
        ),
        (
            "- The framework is intended for clinical review and monitoring "
            "support, not autonomous diagnosis or treatment selection."
        ),
        "",
        "Important limitation:",
        (
            "The framework describes associations observed in a retrospective "
            "MIMIC-IV cohort. External validation, prospective calibration, and "
            "time-window transition analysis are required before clinical deployment."
        ),
        "",
        "=" * 82,
    ]

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 82)
    print(
        "Step 25. Clinical Interpretation and "
        "Trajectory Phenotype Framework"
    )
    print("=" * 82)

    ensure_output_directory()

    print("Loading trajectory signature and outcome validation results...")
    signature, profile, risks, sensitivity = load_inputs()
    validate_inputs(
        signature,
        profile,
        risks,
        sensitivity,
    )

    print("Building final phenotype framework...")
    framework = build_framework(
        signature,
        profile,
        risks,
        sensitivity,
    )

    dashboard = build_dashboard_table(framework)
    zone_rules = build_zone_rules(framework)
    clinical_summary = build_clinical_summary(framework)

    print("Creating clinical framework figure...")
    create_framework_figure(framework)

    report = build_report(framework)

    framework.to_csv(OUTPUT_FRAMEWORK, index=False)
    dashboard.to_csv(OUTPUT_DASHBOARD, index=False)
    clinical_summary.to_csv(
        OUTPUT_CLINICAL_SUMMARY,
        index=False,
    )
    zone_rules.to_csv(OUTPUT_ZONE_RULES, index=False)
    OUTPUT_REPORT.write_text(report, encoding="utf-8")

    print("")
    print("Final phenotype framework:")
    print(
        framework[
            [
                "trajectory_cluster",
                "phenotype_code",
                "phenotype_name",
                "risk_zone",
                "cluster_n",
                "cluster_pct",
                "mortality_1d_rate_pct",
                "mortality_3d_rate_pct",
                "mortality_7d_rate_pct",
            ]
        ].to_string(index=False)
    )

    print("")
    print("Saved:")
    for path in [
        OUTPUT_FRAMEWORK,
        OUTPUT_DASHBOARD,
        OUTPUT_CLINICAL_SUMMARY,
        OUTPUT_ZONE_RULES,
        OUTPUT_FIGURE,
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
