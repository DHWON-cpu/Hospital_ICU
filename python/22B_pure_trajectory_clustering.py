# 22B_pure_trajectory_clustering.py

from __future__ import annotations

import os

# Limit BLAS threads before importing NumPy/scikit-learn.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import RobustScaler


# ============================================================
# Project paths
# ============================================================

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

PRIMARY_INPUT = (
    RESULTS_DIR
    / "21B_trajectory_cohort_selection"
    / "21B_eligible_trajectory_winsorized.csv"
)

COMPLETE_INPUT = (
    RESULTS_DIR
    / "21C_trajectory_sensitivity_cohort"
    / "21C_complete_trajectory_winsorized.csv"
)

OUTPUT_DIR = RESULTS_DIR / "22B_pure_trajectory_clustering"

OUTPUT_PRIMARY_SCORES = OUTPUT_DIR / "22B_primary_k_selection_scores.csv"
OUTPUT_COMPLETE_SCORES = OUTPUT_DIR / "22B_complete_k_selection_scores.csv"
OUTPUT_PRIMARY_LABELS = OUTPUT_DIR / "22B_primary_cluster_labels.csv"
OUTPUT_COMPLETE_LABELS = OUTPUT_DIR / "22B_complete_cluster_labels.csv"

OUTPUT_PRIMARY_CENTROIDS_SCALED = (
    OUTPUT_DIR / "22B_primary_centroids_scaled.csv"
)
OUTPUT_COMPLETE_CENTROIDS_SCALED = (
    OUTPUT_DIR / "22B_complete_centroids_scaled.csv"
)
OUTPUT_PRIMARY_CENTROIDS_RAW = (
    OUTPUT_DIR / "22B_primary_centroids_raw.csv"
)
OUTPUT_COMPLETE_CENTROIDS_RAW = (
    OUTPUT_DIR / "22B_complete_centroids_raw.csv"
)

OUTPUT_CLUSTER_MATCHING = (
    OUTPUT_DIR / "22B_primary_complete_cluster_matching.csv"
)
OUTPUT_OVERLAP_AGREEMENT = (
    OUTPUT_DIR / "22B_overlap_cluster_agreement.csv"
)
OUTPUT_PRIMARY_SCALED_MATRIX = (
    OUTPUT_DIR / "22B_primary_pure_trajectory_scaled.csv"
)
OUTPUT_COMPLETE_SCALED_MATRIX = (
    OUTPUT_DIR / "22B_complete_pure_trajectory_scaled.csv"
)
OUTPUT_SUMMARY = OUTPUT_DIR / "22B_pure_trajectory_clustering_summary.txt"


# ============================================================
# Pure trajectory feature definition
# ============================================================

PURE_TRAJECTORY_FEATURES = [
    "lactate_clearance_pct",
    "creatinine_percent_change",
    "white_blood_cells_percent_change",
    "platelet_count_percent_change",
]


# ============================================================
# Clustering configuration
# ============================================================

K_VALUES = range(2, 7)
RANDOM_STATE = 42
N_INIT = 20
MAX_ITER = 500
SILHOUETTE_SAMPLE_SIZE = 5000

MIN_CLUSTER_N = 100
MIN_CLUSTER_PCT = 1.0

SCORE_WEIGHTS = {
    "silhouette_rank": 0.40,
    "calinski_rank": 0.30,
    "davies_rank": 0.30,
}


# ============================================================
# Data preparation
# ============================================================

def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_pure_trajectory_matrix(
    path: Path,
    cohort_name: str,
    allow_missing: bool,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{cohort_name} input not found: {path}"
        )

    df = pd.read_csv(path, low_memory=False)

    required = {"stay_id", *PURE_TRAJECTORY_FEATURES}
    missing_columns = sorted(required.difference(df.columns))

    if missing_columns:
        raise ValueError(
            f"{cohort_name} input is missing columns:\n"
            + "\n".join(f"  - {column}" for column in missing_columns)
        )

    result = df[["stay_id"] + PURE_TRAJECTORY_FEATURES].copy()

    duplicated = int(result["stay_id"].duplicated().sum())
    if duplicated:
        raise ValueError(
            f"{cohort_name} contains {duplicated:,} duplicated stay_id values."
        )

    missing_values = int(
        result[PURE_TRAJECTORY_FEATURES].isna().sum().sum()
    )

    if missing_values and not allow_missing:
        raise ValueError(
            f"{cohort_name} contains {missing_values:,} missing values."
        )

    if missing_values and allow_missing:
        print(
            f"  Note: {cohort_name} contains {missing_values:,} missing "
            "trajectory values. Median imputation will be applied before "
            "scaling and clustering."
        )

    return result


def median_impute_and_scale(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = df.copy()

    medians = raw[PURE_TRAJECTORY_FEATURES].median()

    imputed = raw.copy()
    imputed[PURE_TRAJECTORY_FEATURES] = (
        imputed[PURE_TRAJECTORY_FEATURES].fillna(medians)
    )

    scaler = RobustScaler()
    scaled_values = scaler.fit_transform(
        imputed[PURE_TRAJECTORY_FEATURES]
    )

    scaled = pd.DataFrame(
        scaled_values,
        columns=PURE_TRAJECTORY_FEATURES,
        index=imputed.index,
    )
    scaled.insert(0, "stay_id", imputed["stay_id"].values)

    return imputed, scaled


# ============================================================
# K evaluation
# ============================================================

def evaluate_k_values(
    scaled_df: pd.DataFrame,
    cohort_name: str,
) -> pd.DataFrame:
    x = scaled_df[PURE_TRAJECTORY_FEATURES].to_numpy(dtype=float)
    rows = []

    for k in K_VALUES:
        print(f"  {cohort_name}: fitting k={k}...")

        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=N_INIT,
            max_iter=MAX_ITER,
            algorithm="lloyd",
        )
        labels = model.fit_predict(x)

        counts = pd.Series(labels).value_counts().sort_index()
        min_n = int(counts.min())
        min_pct = float(min_n / len(labels) * 100)

        rows.append(
            {
                "cohort": cohort_name,
                "k": k,
                "inertia": float(model.inertia_),
                "silhouette_score": float(
                    silhouette_score(
                        x,
                        labels,
                        sample_size=min(
                            SILHOUETTE_SAMPLE_SIZE,
                            len(x),
                        ),
                        random_state=RANDOM_STATE,
                    )
                ),
                "calinski_harabasz_score": float(
                    calinski_harabasz_score(x, labels)
                ),
                "davies_bouldin_score": float(
                    davies_bouldin_score(x, labels)
                ),
                "smallest_cluster_n": min_n,
                "smallest_cluster_pct": min_pct,
                "passes_min_cluster_size": int(
                    min_n >= MIN_CLUSTER_N
                    and min_pct >= MIN_CLUSTER_PCT
                ),
                "cluster_counts": "|".join(
                    f"{cluster}:{count}"
                    for cluster, count in counts.items()
                ),
            }
        )

    scores = pd.DataFrame(rows)
    valid = scores["passes_min_cluster_size"].eq(1)

    scores["silhouette_rank"] = np.nan
    scores["calinski_rank"] = np.nan
    scores["davies_rank"] = np.nan

    scores.loc[valid, "silhouette_rank"] = (
        scores.loc[valid, "silhouette_score"]
        .rank(ascending=False, method="min")
    )
    scores.loc[valid, "calinski_rank"] = (
        scores.loc[valid, "calinski_harabasz_score"]
        .rank(ascending=False, method="min")
    )
    scores.loc[valid, "davies_rank"] = (
        scores.loc[valid, "davies_bouldin_score"]
        .rank(ascending=True, method="min")
    )

    scores["weighted_rank_score"] = (
        SCORE_WEIGHTS["silhouette_rank"] * scores["silhouette_rank"]
        + SCORE_WEIGHTS["calinski_rank"] * scores["calinski_rank"]
        + SCORE_WEIGHTS["davies_rank"] * scores["davies_rank"]
    )

    return scores


def select_k(primary_scores: pd.DataFrame) -> int:
    valid = primary_scores.loc[
        primary_scores["passes_min_cluster_size"].eq(1)
        & primary_scores["weighted_rank_score"].notna()
    ].copy()

    if valid.empty:
        raise ValueError(
            "No k candidate passed the minimum cluster-size criteria."
        )

    best = valid.sort_values(
        [
            "weighted_rank_score",
            "silhouette_score",
            "davies_bouldin_score",
            "k",
        ],
        ascending=[True, False, True, True],
    ).iloc[0]

    return int(best["k"])


# ============================================================
# Final clustering
# ============================================================

def fit_final_model(
    scaled_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    k: int,
    cohort_name: str,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    x = scaled_df[PURE_TRAJECTORY_FEATURES].to_numpy(dtype=float)

    model = KMeans(
        n_clusters=k,
        random_state=RANDOM_STATE,
        n_init=N_INIT,
        max_iter=MAX_ITER,
        algorithm="lloyd",
    )
    labels = model.fit_predict(x)

    label_df = scaled_df[["stay_id"]].copy()
    label_df["trajectory_cluster"] = labels
    label_df["cohort"] = cohort_name

    scaled_with_labels = scaled_df.copy()
    scaled_with_labels["trajectory_cluster"] = labels

    raw_with_labels = raw_df.merge(
        label_df[["stay_id", "trajectory_cluster"]],
        on="stay_id",
        how="inner",
        validate="one_to_one",
    )

    scaled_centroids = (
        scaled_with_labels
        .groupby("trajectory_cluster", as_index=False)[
            PURE_TRAJECTORY_FEATURES
        ]
        .mean()
    )

    raw_centroids = (
        raw_with_labels
        .groupby("trajectory_cluster", as_index=False)[
            PURE_TRAJECTORY_FEATURES
        ]
        .median()
    )

    counts = (
        label_df["trajectory_cluster"]
        .value_counts()
        .sort_index()
    )

    for centroid_df in [scaled_centroids, raw_centroids]:
        centroid_df["cluster_n"] = (
            centroid_df["trajectory_cluster"].map(counts)
        )
        centroid_df["cluster_pct"] = (
            centroid_df["cluster_n"] / len(label_df) * 100
        )

    return label_df, scaled_centroids, raw_centroids


# ============================================================
# Reproducibility analysis
# ============================================================

def match_centroids(
    primary_centroids: pd.DataFrame,
    complete_centroids: pd.DataFrame,
) -> pd.DataFrame:
    primary_matrix = primary_centroids[
        PURE_TRAJECTORY_FEATURES
    ].to_numpy(dtype=float)

    complete_matrix = complete_centroids[
        PURE_TRAJECTORY_FEATURES
    ].to_numpy(dtype=float)

    similarity = np.zeros(
        (len(primary_matrix), len(complete_matrix)),
        dtype=float,
    )

    for i, primary_vector in enumerate(primary_matrix):
        for j, complete_vector in enumerate(complete_matrix):
            if (
                np.std(primary_vector) == 0
                or np.std(complete_vector) == 0
            ):
                similarity[i, j] = 0.0
            else:
                similarity[i, j] = float(
                    np.corrcoef(primary_vector, complete_vector)[0, 1]
                )

    row_ind, col_ind = linear_sum_assignment(-similarity)

    rows = []

    for primary_index, complete_index in zip(row_ind, col_ind):
        primary_cluster = int(
            primary_centroids.iloc[primary_index]["trajectory_cluster"]
        )
        complete_cluster = int(
            complete_centroids.iloc[complete_index]["trajectory_cluster"]
        )

        rows.append(
            {
                "primary_cluster": primary_cluster,
                "complete_cluster": complete_cluster,
                "centroid_correlation": float(
                    similarity[primary_index, complete_index]
                ),
                "euclidean_centroid_distance": float(
                    np.linalg.norm(
                        primary_matrix[primary_index]
                        - complete_matrix[complete_index]
                    )
                ),
                "primary_cluster_n": int(
                    primary_centroids.iloc[primary_index]["cluster_n"]
                ),
                "primary_cluster_pct": float(
                    primary_centroids.iloc[primary_index]["cluster_pct"]
                ),
                "complete_cluster_n": int(
                    complete_centroids.iloc[complete_index]["cluster_n"]
                ),
                "complete_cluster_pct": float(
                    complete_centroids.iloc[complete_index]["cluster_pct"]
                ),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("primary_cluster")
        .reset_index(drop=True)
    )


def compare_overlap_membership(
    primary_labels: pd.DataFrame,
    complete_labels: pd.DataFrame,
    matching: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    mapping = dict(
        zip(
            matching["complete_cluster"],
            matching["primary_cluster"],
        )
    )

    overlap = (
        primary_labels[
            ["stay_id", "trajectory_cluster"]
        ]
        .rename(
            columns={"trajectory_cluster": "primary_cluster"}
        )
        .merge(
            complete_labels[
                ["stay_id", "trajectory_cluster"]
            ].rename(
                columns={"trajectory_cluster": "complete_cluster"}
            ),
            on="stay_id",
            how="inner",
            validate="one_to_one",
        )
    )

    overlap["complete_cluster_matched"] = (
        overlap["complete_cluster"].map(mapping)
    )

    overlap["cluster_agreement"] = (
        overlap["primary_cluster"]
        == overlap["complete_cluster_matched"]
    ).astype(int)

    ari = float(
        adjusted_rand_score(
            overlap["primary_cluster"],
            overlap["complete_cluster"],
        )
    )

    return overlap, ari


# ============================================================
# Summary
# ============================================================

def build_summary(
    selected_k: int,
    primary_scores: pd.DataFrame,
    complete_scores: pd.DataFrame,
    primary_labels: pd.DataFrame,
    complete_labels: pd.DataFrame,
    primary_raw_centroids: pd.DataFrame,
    matching: pd.DataFrame,
    overlap: pd.DataFrame,
    overlap_ari: float,
) -> str:
    primary_selected = primary_scores.loc[
        primary_scores["k"].eq(selected_k)
    ].iloc[0]

    complete_selected = complete_scores.loc[
        complete_scores["k"].eq(selected_k)
    ].iloc[0]

    lines = [
        "=" * 76,
        "STEP 22B. PURE BIOCHEMICAL TRAJECTORY CLUSTERING",
        "=" * 76,
        "",
        "Model definition:",
        "- Baseline first-value features were excluded",
        "- Four normalized change features were used",
        "- PCA was not used as clustering input",
        "",
        "Pure trajectory features:",
    ]

    lines.extend(
        f"- {feature}" for feature in PURE_TRAJECTORY_FEATURES
    )

    lines.extend(
        [
            "",
            f"Selected k from primary cohort: {selected_k}",
            "",
            "Primary cohort selected-k metrics:",
            f"- n: {len(primary_labels):,}",
            (
                f"- Silhouette: "
                f"{primary_selected['silhouette_score']:.4f}"
            ),
            (
                f"- Calinski-Harabasz: "
                f"{primary_selected['calinski_harabasz_score']:.2f}"
            ),
            (
                f"- Davies-Bouldin: "
                f"{primary_selected['davies_bouldin_score']:.4f}"
            ),
            "",
            "Complete-cohort selected-k metrics:",
            f"- n: {len(complete_labels):,}",
            (
                f"- Silhouette: "
                f"{complete_selected['silhouette_score']:.4f}"
            ),
            (
                f"- Calinski-Harabasz: "
                f"{complete_selected['calinski_harabasz_score']:.2f}"
            ),
            (
                f"- Davies-Bouldin: "
                f"{complete_selected['davies_bouldin_score']:.4f}"
            ),
            "",
            "Primary raw trajectory centroids:",
        ]
    )

    for row in primary_raw_centroids.itertuples(index=False):
        lines.append(
            f"- Cluster {row.trajectory_cluster}: "
            f"lactate_clearance={row.lactate_clearance_pct:.2f}%, "
            f"creatinine_change={row.creatinine_percent_change:.2f}%, "
            f"WBC_change={row.white_blood_cells_percent_change:.2f}%, "
            f"platelet_change={row.platelet_count_percent_change:.2f}%, "
            f"n={row.cluster_n:,} ({row.cluster_pct:.2f}%)"
        )

    lines.extend(
        [
            "",
            "Primary-complete reproducibility:",
            f"- Overlap stays: {len(overlap):,}",
            f"- Adjusted Rand Index: {overlap_ari:.4f}",
            (
                f"- Matched membership agreement: "
                f"{overlap['cluster_agreement'].mean() * 100:.2f}%"
            ),
            "",
            "Matched centroid pairs:",
        ]
    )

    for row in matching.itertuples(index=False):
        lines.append(
            f"- Primary {row.primary_cluster} ↔ "
            f"Complete {row.complete_cluster}: "
            f"correlation={row.centroid_correlation:.4f}, "
            f"distance={row.euclidean_centroid_distance:.4f}"
        )

    lines.extend(
        [
            "",
            "Interpretation note:",
            (
                "This model isolates dynamic biochemical movement by "
                "excluding baseline state variables."
            ),
            (
                "Clinical phenotype names must be assigned only after "
                "feature characterization and outcome comparison."
            ),
            "",
            "=" * 76,
        ]
    )

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 76)
    print("Step 22B. Pure Biochemical Trajectory Clustering")
    print("=" * 76)

    ensure_output_directory()

    print("Loading primary trajectory matrix...")
    primary_raw = load_pure_trajectory_matrix(
        PRIMARY_INPUT,
        "Primary cohort",
        allow_missing=True,
    )

    print("Loading complete sensitivity trajectory matrix...")
    complete_raw = load_pure_trajectory_matrix(
        COMPLETE_INPUT,
        "Complete cohort",
        allow_missing=False,
    )

    print("Median-imputing and robust-scaling primary cohort...")
    primary_imputed, primary_scaled = median_impute_and_scale(
        primary_raw
    )

    print("Robust-scaling complete cohort...")
    complete_imputed, complete_scaled = median_impute_and_scale(
        complete_raw
    )

    print(f"Primary cohort: {len(primary_scaled):,}")
    print(f"Complete cohort: {len(complete_scaled):,}")
    print(f"Pure trajectory features: {len(PURE_TRAJECTORY_FEATURES)}")
    print("PCA clustering input: No")

    print("\nEvaluating k in primary cohort...")
    primary_scores = evaluate_k_values(
        primary_scaled,
        "Primary",
    )

    selected_k = select_k(primary_scores)
    print(f"\nSelected primary k: {selected_k}")

    print("\nEvaluating k in complete cohort...")
    complete_scores = evaluate_k_values(
        complete_scaled,
        "Complete",
    )

    print("\nFitting final primary model...")
    (
        primary_labels,
        primary_centroids_scaled,
        primary_centroids_raw,
    ) = fit_final_model(
        primary_scaled,
        primary_imputed,
        selected_k,
        "Primary",
    )

    print("Fitting final complete-cohort model...")
    (
        complete_labels,
        complete_centroids_scaled,
        complete_centroids_raw,
    ) = fit_final_model(
        complete_scaled,
        complete_imputed,
        selected_k,
        "Complete",
    )

    print("Matching primary and complete centroids...")
    matching = match_centroids(
        primary_centroids_scaled,
        complete_centroids_scaled,
    )

    overlap, overlap_ari = compare_overlap_membership(
        primary_labels,
        complete_labels,
        matching,
    )

    primary_scores.to_csv(OUTPUT_PRIMARY_SCORES, index=False)
    complete_scores.to_csv(OUTPUT_COMPLETE_SCORES, index=False)
    primary_labels.to_csv(OUTPUT_PRIMARY_LABELS, index=False)
    complete_labels.to_csv(OUTPUT_COMPLETE_LABELS, index=False)

    primary_centroids_scaled.to_csv(
        OUTPUT_PRIMARY_CENTROIDS_SCALED,
        index=False,
    )
    complete_centroids_scaled.to_csv(
        OUTPUT_COMPLETE_CENTROIDS_SCALED,
        index=False,
    )
    primary_centroids_raw.to_csv(
        OUTPUT_PRIMARY_CENTROIDS_RAW,
        index=False,
    )
    complete_centroids_raw.to_csv(
        OUTPUT_COMPLETE_CENTROIDS_RAW,
        index=False,
    )

    matching.to_csv(OUTPUT_CLUSTER_MATCHING, index=False)
    overlap.to_csv(OUTPUT_OVERLAP_AGREEMENT, index=False)
    primary_scaled.to_csv(
        OUTPUT_PRIMARY_SCALED_MATRIX,
        index=False,
    )
    complete_scaled.to_csv(
        OUTPUT_COMPLETE_SCALED_MATRIX,
        index=False,
    )

    summary = build_summary(
        selected_k=selected_k,
        primary_scores=primary_scores,
        complete_scores=complete_scores,
        primary_labels=primary_labels,
        complete_labels=complete_labels,
        primary_raw_centroids=primary_centroids_raw,
        matching=matching,
        overlap=overlap,
        overlap_ari=overlap_ari,
    )

    OUTPUT_SUMMARY.write_text(summary, encoding="utf-8")

    print("\nPrimary k-selection scores:")
    print(
        primary_scores[
            [
                "k",
                "silhouette_score",
                "calinski_harabasz_score",
                "davies_bouldin_score",
                "smallest_cluster_n",
                "smallest_cluster_pct",
                "weighted_rank_score",
            ]
        ].to_string(index=False)
    )

    print("\nPrimary raw trajectory centroids:")
    print(primary_centroids_raw.to_string(index=False))

    print("\nPrimary cluster counts:")
    print(
        primary_labels["trajectory_cluster"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nComplete cluster counts:")
    print(
        complete_labels["trajectory_cluster"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nPrimary-complete centroid matching:")
    print(matching.to_string(index=False))

    print(f"\nOverlap ARI: {overlap_ari:.4f}")
    print(
        "Matched membership agreement: "
        f"{overlap['cluster_agreement'].mean() * 100:.2f}%"
    )

    print("\nSaved all outputs to:")
    print(OUTPUT_DIR)
    print("\nCompleted.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        sys.exit(1)
