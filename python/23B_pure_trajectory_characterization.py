# 23B_pure_trajectory_characterization.py

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
from scipy.stats import mannwhitneyu


# ============================================================
# Project paths
# ============================================================

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

LABELS_INPUT = (
    RESULTS_DIR
    / "22B_pure_trajectory_clustering"
    / "22B_primary_cluster_labels.csv"
)

RAW_INPUT = (
    RESULTS_DIR
    / "21B_trajectory_cohort_selection"
    / "21B_eligible_trajectory_winsorized.csv"
)

SCALED_INPUT = (
    RESULTS_DIR
    / "22B_pure_trajectory_clustering"
    / "22B_primary_pure_trajectory_scaled.csv"
)

OUTPUT_DIR = RESULTS_DIR / "23B_pure_trajectory_characterization"

OUTPUT_PATIENT_LEVEL = OUTPUT_DIR / "23B_patient_level_pure_trajectory.csv"
OUTPUT_FEATURE_STATS = OUTPUT_DIR / "23B_feature_statistics.csv"
OUTPUT_SIGNATURE = OUTPUT_DIR / "23B_pure_trajectory_signature.csv"
OUTPUT_EFFECT_RANKING = OUTPUT_DIR / "23B_effect_size_ranking.csv"
OUTPUT_DIRECTION = OUTPUT_DIR / "23B_direction_summary.csv"
OUTPUT_CLUSTER_PROFILE = OUTPUT_DIR / "23B_cluster_profile_table.csv"
OUTPUT_REPORT = OUTPUT_DIR / "23B_pure_trajectory_characterization_summary.txt"

OUTPUT_VOLCANO = OUTPUT_DIR / "23B_volcano_plot.png"
OUTPUT_HEATMAP = OUTPUT_DIR / "23B_cluster_heatmap.png"
OUTPUT_RADAR = OUTPUT_DIR / "23B_radar_plot.png"
OUTPUT_PROFILE = OUTPUT_DIR / "23B_trajectory_profile_plot.png"


# ============================================================
# Feature definition
# ============================================================

PURE_TRAJECTORY_FEATURES = [
    "lactate_clearance_pct",
    "creatinine_percent_change",
    "white_blood_cells_percent_change",
    "platelet_count_percent_change",
]

FEATURE_LABELS = {
    "lactate_clearance_pct": "Lactate clearance",
    "creatinine_percent_change": "Creatinine change",
    "white_blood_cells_percent_change": "WBC change",
    "platelet_count_percent_change": "Platelet change",
}

FEATURE_METADATA = {
    "lactate_clearance_pct": {
        "biomarker": "Lactate",
        "unit": "%",
        "positive_meaning": "Improving",
        "negative_meaning": "Deteriorating",
    },
    "creatinine_percent_change": {
        "biomarker": "Creatinine",
        "unit": "%",
        "positive_meaning": "Deteriorating",
        "negative_meaning": "Improving",
    },
    "white_blood_cells_percent_change": {
        "biomarker": "White Blood Cells",
        "unit": "%",
        "positive_meaning": "Increasing",
        "negative_meaning": "Decreasing",
    },
    "platelet_count_percent_change": {
        "biomarker": "Platelet Count",
        "unit": "%",
        "positive_meaning": "Increasing",
        "negative_meaning": "Decreasing",
    },
}

HEATMAP_SAMPLE_PER_CLUSTER = 250
RANDOM_STATE = 42


# ============================================================
# Utilities
# ============================================================

def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [LABELS_INPUT, RAW_INPUT, SCALED_INPUT]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    labels = pd.read_csv(LABELS_INPUT, low_memory=False)
    raw = pd.read_csv(RAW_INPUT, low_memory=False)
    scaled = pd.read_csv(SCALED_INPUT, low_memory=False)

    return labels, raw, scaled


def validate_inputs(
    labels: pd.DataFrame,
    raw: pd.DataFrame,
    scaled: pd.DataFrame,
) -> None:
    required_label_columns = {"stay_id", "trajectory_cluster"}
    missing_label_columns = required_label_columns.difference(labels.columns)

    if missing_label_columns:
        raise ValueError(
            "Cluster label file is missing columns: "
            + ", ".join(sorted(missing_label_columns))
        )

    for name, frame in [("Raw", raw), ("Scaled", scaled)]:
        required = {"stay_id", *PURE_TRAJECTORY_FEATURES}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                f"{name} matrix is missing columns:\n"
                + "\n".join(f"  - {column}" for column in missing)
            )

    clusters = sorted(labels["trajectory_cluster"].dropna().unique().tolist())

    if clusters != [0, 1]:
        raise ValueError(
            f"Step 23B expects clusters [0, 1], but found {clusters}."
        )


def merge_inputs(
    labels: pd.DataFrame,
    raw: pd.DataFrame,
    scaled: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_selected = raw[["stay_id"] + PURE_TRAJECTORY_FEATURES].copy()
    scaled_selected = scaled[["stay_id"] + PURE_TRAJECTORY_FEATURES].copy()

    raw_merged = raw_selected.merge(
        labels[["stay_id", "trajectory_cluster"]],
        on="stay_id",
        how="inner",
        validate="one_to_one",
    )

    scaled_merged = scaled_selected.merge(
        labels[["stay_id", "trajectory_cluster"]],
        on="stay_id",
        how="inner",
        validate="one_to_one",
    )

    if len(raw_merged) != len(labels) or len(scaled_merged) != len(labels):
        raise ValueError(
            "Merged patient count does not match cluster label count."
        )

    return raw_merged, scaled_merged


def benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    values = p_values.fillna(1.0).to_numpy(dtype=float)
    n = len(values)
    order = np.argsort(values)
    ranked = values[order]

    adjusted_ranked = np.empty(n, dtype=float)
    running_min = 1.0

    for index in range(n - 1, -1, -1):
        rank = index + 1
        candidate = ranked[index] * n / rank
        running_min = min(running_min, candidate)
        adjusted_ranked[index] = running_min

    adjusted = np.empty(n, dtype=float)
    adjusted[order] = np.clip(adjusted_ranked, 0.0, 1.0)

    return pd.Series(adjusted, index=p_values.index)


def rank_biserial_from_u(
    u_statistic: float,
    n_cluster1: int,
    n_cluster0: int,
) -> float:
    if n_cluster0 == 0 or n_cluster1 == 0:
        return np.nan

    return float(
        (2.0 * u_statistic) / (n_cluster1 * n_cluster0) - 1.0
    )


def effect_category(effect: float) -> str:
    absolute = abs(effect)

    if absolute < 0.10:
        return "negligible"
    if absolute < 0.30:
        return "small"
    if absolute < 0.50:
        return "moderate"
    return "large"


def median_iqr(series: pd.Series) -> tuple[float, float, float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()

    if clean.empty:
        return np.nan, np.nan, np.nan

    return (
        float(clean.median()),
        float(clean.quantile(0.25)),
        float(clean.quantile(0.75)),
    )


def classify_direction(feature: str, value: float) -> str:
    if pd.isna(value):
        return "Unknown"

    if abs(value) <= 5:
        return "Stable"

    if feature == "lactate_clearance_pct":
        return "Improving" if value > 5 else "Deteriorating"

    if feature == "creatinine_percent_change":
        return "Deteriorating" if value > 5 else "Improving"

    if feature == "white_blood_cells_percent_change":
        return "Increasing" if value > 5 else "Decreasing"

    if feature == "platelet_count_percent_change":
        return "Increasing" if value > 5 else "Decreasing"

    return "Unknown"


# ============================================================
# Statistical characterization
# ============================================================

def compare_features(raw_merged: pd.DataFrame) -> pd.DataFrame:
    cluster0 = raw_merged.loc[
        raw_merged["trajectory_cluster"].eq(0)
    ]
    cluster1 = raw_merged.loc[
        raw_merged["trajectory_cluster"].eq(1)
    ]

    rows = []

    for feature in PURE_TRAJECTORY_FEATURES:
        values0 = pd.to_numeric(
            cluster0[feature],
            errors="coerce",
        ).dropna()

        values1 = pd.to_numeric(
            cluster1[feature],
            errors="coerce",
        ).dropna()

        median0, q1_0, q3_0 = median_iqr(values0)
        median1, q1_1, q3_1 = median_iqr(values1)

        if values0.empty or values1.empty:
            u_statistic = np.nan
            p_value = np.nan
            effect = np.nan
        else:
            test = mannwhitneyu(
                values1,
                values0,
                alternative="two-sided",
            )
            u_statistic = float(test.statistic)
            p_value = float(test.pvalue)
            effect = rank_biserial_from_u(
                u_statistic,
                len(values1),
                len(values0),
            )

        metadata = FEATURE_METADATA[feature]

        rows.append(
            {
                "feature": feature,
                "display_name": FEATURE_LABELS[feature],
                "biomarker": metadata["biomarker"],
                "unit": metadata["unit"],
                "cluster_0_n_non_missing": int(values0.size),
                "cluster_0_median": median0,
                "cluster_0_q1": q1_0,
                "cluster_0_q3": q3_0,
                "cluster_1_n_non_missing": int(values1.size),
                "cluster_1_median": median1,
                "cluster_1_q1": q1_1,
                "cluster_1_q3": q3_1,
                "median_difference_cluster1_minus_cluster0": (
                    median1 - median0
                    if pd.notna(median1) and pd.notna(median0)
                    else np.nan
                ),
                "mannwhitney_u": u_statistic,
                "p_value": p_value,
                "rank_biserial_effect": effect,
                "effect_category": (
                    effect_category(effect)
                    if pd.notna(effect)
                    else "unknown"
                ),
            }
        )

    result = pd.DataFrame(rows)
    result["fdr_q_value"] = benjamini_hochberg(
        result["p_value"]
    )
    result["fdr_significant"] = (
        result["fdr_q_value"] < 0.05
    ).astype(int)

    return result


def build_signature(feature_stats: pd.DataFrame) -> pd.DataFrame:
    signature = feature_stats[
        [
            "feature",
            "display_name",
            "biomarker",
            "unit",
            "cluster_0_median",
            "cluster_1_median",
            "median_difference_cluster1_minus_cluster0",
            "rank_biserial_effect",
            "effect_category",
            "fdr_q_value",
        ]
    ].copy()

    signature["cluster_0_direction"] = signature.apply(
        lambda row: classify_direction(
            row["feature"],
            row["cluster_0_median"],
        ),
        axis=1,
    )

    signature["cluster_1_direction"] = signature.apply(
        lambda row: classify_direction(
            row["feature"],
            row["cluster_1_median"],
        ),
        axis=1,
    )

    signature["higher_cluster"] = np.select(
        [
            signature["rank_biserial_effect"] > 0,
            signature["rank_biserial_effect"] < 0,
        ],
        [
            "Cluster 1",
            "Cluster 0",
        ],
        default="Similar",
    )

    return signature


def build_direction_summary(
    signature: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for cluster in [0, 1]:
        for _, row in signature.iterrows():
            rows.append(
                {
                    "trajectory_cluster": cluster,
                    "feature": row["feature"],
                    "display_name": row["display_name"],
                    "biomarker": row["biomarker"],
                    "median_value": row[f"cluster_{cluster}_median"],
                    "direction_label": row[
                        f"cluster_{cluster}_direction"
                    ],
                }
            )

    return pd.DataFrame(rows)


def build_cluster_profile(
    raw_merged: pd.DataFrame,
) -> pd.DataFrame:
    counts = (
        raw_merged["trajectory_cluster"]
        .value_counts()
        .sort_index()
    )

    rows = []

    for cluster in [0, 1]:
        group = raw_merged.loc[
            raw_merged["trajectory_cluster"].eq(cluster)
        ]

        row = {
            "trajectory_cluster": cluster,
            "cluster_n": int(counts.get(cluster, 0)),
            "cluster_pct": float(
                counts.get(cluster, 0) / len(raw_merged) * 100
            ),
        }

        for feature in PURE_TRAJECTORY_FEATURES:
            row[f"{feature}_median"] = float(
                group[feature].median()
            )
            row[f"{feature}_mean"] = float(
                group[feature].mean()
            )

        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# Visualization
# ============================================================

def create_volcano_plot(feature_stats: pd.DataFrame) -> None:
    plot_df = feature_stats.copy()
    plot_df["minus_log10_q"] = -np.log10(
        plot_df["fdr_q_value"].clip(lower=1e-300)
    )

    fig, ax = plt.subplots(figsize=(9, 6))

    ax.scatter(
        plot_df["rank_biserial_effect"],
        plot_df["minus_log10_q"],
        s=100,
    )

    for row in plot_df.itertuples(index=False):
        ax.annotate(
            row.display_name,
            (
                row.rank_biserial_effect,
                row.minus_log10_q,
            ),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=9,
        )

    ax.axvline(0, linewidth=1)
    ax.axhline(-np.log10(0.05), linestyle="--", linewidth=1)
    ax.set_xlabel(
        "Rank-biserial effect\n"
        "(positive = Cluster 1 higher)"
    )
    ax.set_ylabel("-log10(FDR q-value)")
    ax.set_title("Pure Trajectory Feature Differences")
    fig.tight_layout()
    fig.savefig(OUTPUT_VOLCANO, dpi=300)
    plt.close(fig)


def create_cluster_heatmap(
    scaled_merged: pd.DataFrame,
) -> None:
    sampled_frames = []

    for cluster in [0, 1]:
        group = scaled_merged.loc[
            scaled_merged["trajectory_cluster"].eq(cluster)
        ]

        sample_n = min(HEATMAP_SAMPLE_PER_CLUSTER, len(group))

        sampled_frames.append(
            group.sample(
                n=sample_n,
                random_state=RANDOM_STATE,
            )
        )

    sample = pd.concat(
        sampled_frames,
        ignore_index=True,
    ).sort_values("trajectory_cluster")

    matrix = sample[PURE_TRAJECTORY_FEATURES].to_numpy()

    fig, ax = plt.subplots(figsize=(10, 8))
    image = ax.imshow(
        matrix,
        aspect="auto",
        interpolation="nearest",
    )

    ax.set_xticks(range(len(PURE_TRAJECTORY_FEATURES)))
    ax.set_xticklabels(
        [FEATURE_LABELS[f] for f in PURE_TRAJECTORY_FEATURES],
        rotation=35,
        ha="right",
    )
    ax.set_ylabel("Sampled ICU stays ordered by cluster")
    ax.set_title("Patient-Level Pure Trajectory Heatmap")

    cluster0_n = int(
        sample["trajectory_cluster"].eq(0).sum()
    )
    ax.axhline(cluster0_n - 0.5, linewidth=2)

    fig.colorbar(
        image,
        ax=ax,
        label="Robust-scaled trajectory value",
    )

    fig.tight_layout()
    fig.savefig(OUTPUT_HEATMAP, dpi=300)
    plt.close(fig)


def create_radar_plot(
    scaled_merged: pd.DataFrame,
) -> None:
    centroids = (
        scaled_merged
        .groupby("trajectory_cluster")[
            PURE_TRAJECTORY_FEATURES
        ]
        .mean()
    )

    labels = [
        FEATURE_LABELS[feature]
        for feature in PURE_TRAJECTORY_FEATURES
    ]

    angles = np.linspace(
        0,
        2 * np.pi,
        len(labels),
        endpoint=False,
    ).tolist()

    angles += angles[:1]

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)

    for cluster in [0, 1]:
        values = centroids.loc[cluster].tolist()
        values += values[:1]

        ax.plot(
            angles,
            values,
            linewidth=2,
            label=f"Cluster {cluster}",
        )
        ax.fill(
            angles,
            values,
            alpha=0.15,
        )

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_title("Pure Trajectory Cluster Profiles")
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))

    fig.tight_layout()
    fig.savefig(OUTPUT_RADAR, dpi=300)
    plt.close(fig)


def create_profile_plot(
    cluster_profile: pd.DataFrame,
) -> None:
    long_rows = []

    for row in cluster_profile.itertuples(index=False):
        for feature in PURE_TRAJECTORY_FEATURES:
            long_rows.append(
                {
                    "trajectory_cluster": row.trajectory_cluster,
                    "feature": FEATURE_LABELS[feature],
                    "median_value": getattr(
                        row,
                        f"{feature}_median",
                    ),
                }
            )

    long_df = pd.DataFrame(long_rows)

    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(PURE_TRAJECTORY_FEATURES))

    for cluster in [0, 1]:
        cluster_df = long_df.loc[
            long_df["trajectory_cluster"].eq(cluster)
        ]

        ax.plot(
            x,
            cluster_df["median_value"],
            marker="o",
            linewidth=2,
            label=f"Cluster {cluster}",
        )

    ax.axhline(0, linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [FEATURE_LABELS[f] for f in PURE_TRAJECTORY_FEATURES],
        rotation=25,
        ha="right",
    )
    ax.set_ylabel("Median percent change / clearance")
    ax.set_title("Median Pure Trajectory Profiles")
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUTPUT_PROFILE, dpi=300)
    plt.close(fig)


# ============================================================
# Report
# ============================================================

def build_report(
    raw_merged: pd.DataFrame,
    feature_stats: pd.DataFrame,
    signature: pd.DataFrame,
    cluster_profile: pd.DataFrame,
) -> str:
    counts = (
        raw_merged["trajectory_cluster"]
        .value_counts()
        .sort_index()
    )

    lines = [
        "=" * 78,
        "STEP 23B. PURE TRAJECTORY PHENOTYPE CHARACTERIZATION",
        "=" * 78,
        "",
        f"Patient-level rows: {len(raw_merged):,}",
        f"Cluster 0: {counts.get(0, 0):,}",
        f"Cluster 1: {counts.get(1, 0):,}",
        "",
        "Model scope:",
        "- Baseline first-value features excluded",
        "- Four normalized trajectory features characterized",
        "",
        "Statistical methods:",
        "- Mann-Whitney U test",
        "- Rank-biserial effect size",
        "- Benjamini-Hochberg FDR correction",
        "",
        "Cluster trajectory profiles:",
    ]

    for row in cluster_profile.itertuples(index=False):
        lines.append(
            f"- Cluster {row.trajectory_cluster}: "
            f"lactate clearance="
            f"{row.lactate_clearance_pct_median:.2f}%, "
            f"creatinine change="
            f"{row.creatinine_percent_change_median:.2f}%, "
            f"WBC change="
            f"{row.white_blood_cells_percent_change_median:.2f}%, "
            f"platelet change="
            f"{row.platelet_count_percent_change_median:.2f}%"
        )

    lines.extend(
        [
            "",
            "Feature-level signature:",
        ]
    )

    for row in signature.itertuples(index=False):
        lines.append(
            f"- {row.display_name}: "
            f"C0={row.cluster_0_median:.2f}%, "
            f"C1={row.cluster_1_median:.2f}%, "
            f"effect={row.rank_biserial_effect:.3f} "
            f"({row.effect_category}), "
            f"q={row.fdr_q_value:.3e}"
        )

    lines.extend(
        [
            "",
            "Candidate descriptive interpretation:",
            (
                "- Cluster 0 shows lactate clearance, stable creatinine, "
                "and decreasing WBC, with a modest platelet decline."
            ),
            (
                "- Cluster 1 shows absent median lactate clearance, "
                "increasing creatinine, increasing WBC, and increasing "
                "platelet count."
            ),
            "",
            "Naming caution:",
            (
                "These are descriptive trajectory signatures only. "
                "Low-risk, high-risk, recovery, or deterioration labels "
                "must be finalized after clinical outcome validation."
            ),
            "",
            "=" * 78,
        ]
    )

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 78)
    print("Step 23B. Pure Trajectory Phenotype Characterization")
    print("=" * 78)

    ensure_output_directory()

    print("Loading pure trajectory labels and matrices...")
    labels, raw, scaled = load_inputs()
    validate_inputs(labels, raw, scaled)

    print("Merging patient-level data...")
    raw_merged, scaled_merged = merge_inputs(
        labels,
        raw,
        scaled,
    )

    print(f"Patient-level shape: {raw_merged.shape}")

    print("Calculating feature statistics...")
    feature_stats = compare_features(raw_merged)

    print("Building phenotype signature...")
    signature = build_signature(feature_stats)
    direction_summary = build_direction_summary(signature)
    cluster_profile = build_cluster_profile(raw_merged)

    effect_ranking = (
        feature_stats.assign(
            absolute_effect=feature_stats[
                "rank_biserial_effect"
            ].abs()
        )
        .sort_values(
            ["absolute_effect", "fdr_q_value"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    print("Creating publication-ready figures...")
    create_volcano_plot(feature_stats)
    create_cluster_heatmap(scaled_merged)
    create_radar_plot(scaled_merged)
    create_profile_plot(cluster_profile)

    report = build_report(
        raw_merged,
        feature_stats,
        signature,
        cluster_profile,
    )

    raw_merged.to_csv(OUTPUT_PATIENT_LEVEL, index=False)
    feature_stats.to_csv(OUTPUT_FEATURE_STATS, index=False)
    signature.to_csv(OUTPUT_SIGNATURE, index=False)
    effect_ranking.to_csv(OUTPUT_EFFECT_RANKING, index=False)
    direction_summary.to_csv(OUTPUT_DIRECTION, index=False)
    cluster_profile.to_csv(OUTPUT_CLUSTER_PROFILE, index=False)
    OUTPUT_REPORT.write_text(report, encoding="utf-8")

    print("")
    print("Feature statistics:")
    print(
        feature_stats[
            [
                "feature",
                "cluster_0_median",
                "cluster_1_median",
                "rank_biserial_effect",
                "effect_category",
                "fdr_q_value",
            ]
        ].to_string(index=False)
    )

    print("")
    print("Cluster profile:")
    print(cluster_profile.to_string(index=False))

    print("")
    print("Saved:")
    for path in [
        OUTPUT_PATIENT_LEVEL,
        OUTPUT_FEATURE_STATS,
        OUTPUT_SIGNATURE,
        OUTPUT_EFFECT_RANKING,
        OUTPUT_DIRECTION,
        OUTPUT_CLUSTER_PROFILE,
        OUTPUT_VOLCANO,
        OUTPUT_HEATMAP,
        OUTPUT_RADAR,
        OUTPUT_PROFILE,
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
