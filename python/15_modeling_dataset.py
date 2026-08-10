# python/15_modeling_dataset.py

"""
input_content : results/12_feature_wide.csv, results/13_temporal_features.csv (long),
                results/14_outcome_labels.csv
output_content : results/15_modeling_dataset.csv — one row per stay_id, static wide features +
                 pivoted temporal features ({label}_{first_value|last_value|delta_value|slope_per_hour|cv})
                 + mortality_1d / 3d / 7d labels
calls : pandas (read_csv, pivot_table, merge, to_csv)
side effect : writes OUTPUT_PATH, prints row/column counts, outcome counts, rates, and missing-outcome tallies
responsibility : Step 15 — reshape long trajectory features to wide, left-join features with outcome labels
                 on stay_id, and produce the single analysis-ready modeling table for clustering and
                 logistic-regression validation.
"""

from pathlib import Path
import pandas as pd


PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

FEATURE_WIDE_PATH = RESULTS_DIR / "12_feature_wide.csv"
TEMPORAL_PATH = RESULTS_DIR / "13_temporal_features.csv"
OUTCOME_PATH = RESULTS_DIR / "14_outcome_labels.csv"
OUTPUT_PATH = RESULTS_DIR / "15_modeling_dataset.csv"


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)


def summarize(name: str, df: pd.DataFrame) -> None:
    print(f"{name}")
    print(f"Rows: {df.shape[0]:,}")
    print(f"Columns: {df.shape[1]:,}")
    print("-" * 40)


def clean_name(name: str) -> str:
    return (
        str(name)
        .lower()
        .replace(" ", "_")
        .replace("₂", "2")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "_")
        .replace("-", "_")
    )


def make_temporal_wide(temporal: pd.DataFrame) -> pd.DataFrame:
    temporal_feature_cols = [
        "first_value",
        "last_value",
        "delta_value",
        "slope_per_hour",
        "cv",
    ]

    available_cols = [
        col for col in temporal_feature_cols
        if col in temporal.columns
    ]

    temporal_wide = temporal.pivot_table(
        index="stay_id",
        columns="label",
        values=available_cols,
        aggfunc="first",
    )

    temporal_wide.columns = [
        f"{clean_name(label)}_{feature}"
        for feature, label in temporal_wide.columns
    ]

    temporal_wide = temporal_wide.reset_index()

    return temporal_wide


def main() -> None:
    print("\nLoading input files...")
    feature_wide = load_csv(FEATURE_WIDE_PATH)
    temporal = load_csv(TEMPORAL_PATH)
    outcomes = load_csv(OUTCOME_PATH)

    summarize("Feature Wide Dataset", feature_wide)
    summarize("Temporal Feature Dataset - Long Format", temporal)
    summarize("Outcome Label Dataset", outcomes)

    print("Converting temporal features to wide format...")
    temporal_wide = make_temporal_wide(temporal)
    summarize("Temporal Feature Dataset - Wide Format", temporal_wide)

    outcome_cols = [
        "stay_id",
        "mortality_1d",
        "mortality_3d",
        "mortality_7d",
    ]

    print("Merging feature_wide + temporal_wide...")
    modeling_df = feature_wide.merge(
        temporal_wide,
        on="stay_id",
        how="left",
    )

    print("Merging outcome labels...")
    modeling_df = modeling_df.merge(
        outcomes[outcome_cols],
        on="stay_id",
        how="left",
    )

    print("Saving final modeling dataset...")
    modeling_df.to_csv(OUTPUT_PATH, index=False)

    print("\n=========================================")
    print("Final Modeling Dataset")
    print("=========================================")
    print(f"Rows: {modeling_df.shape[0]:,}")
    print(f"Columns: {modeling_df.shape[1]:,}")

    print("\nOutcome Counts")
    print(modeling_df[["mortality_1d", "mortality_3d", "mortality_7d"]].sum())

    print("\nOutcome Rates (%)")
    print(
        (modeling_df[["mortality_1d", "mortality_3d", "mortality_7d"]]
         .mean() * 100)
        .round(2)
    )

    print("\nMissing Outcomes")
    print(modeling_df[["mortality_1d", "mortality_3d", "mortality_7d"]].isna().sum())

    print(f"\nSaved: {OUTPUT_PATH}")
    print("Completed.")


if __name__ == "__main__":
    main()