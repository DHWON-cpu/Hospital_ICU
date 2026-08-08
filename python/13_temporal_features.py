# 13_temporal_features.py

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd


# ============================================================
# Project paths
# ============================================================

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"
OUTPUT_CSV = RESULTS_DIR / "13_temporal_features.csv"


# ============================================================
# Variables included in the first-24-hour trajectory analysis
# ============================================================

CORE_VARIABLES = [
    "Heart Rate",
    "Respiratory Rate",
    "O2 saturation pulseoxymetry",
    "Creatinine",
    "Lactate",
    "Glucose",
    "Platelet Count",
    "White Blood Cells",
]


# ============================================================
# Database configuration
# ============================================================

DOCKER_CONTAINER = "mimic_postgres"
POSTGRES_USER = "dh"
POSTGRES_DATABASE = "mimiciv"
SOURCE_TABLE = "mimiciv_derived.trajectory_first24h"


def build_sql() -> str:
    """
    Build the PostgreSQL query used to generate patient-level temporal
    and trajectory features.

    Sign conventions
    ----------------
    delta_value:
        last_value - first_value

    percent_change:
        ((last_value - first_value) / ABS(first_value)) * 100

        Positive value = increase
        Negative value = decrease

    lactate_clearance_pct:
        ((first_value - last_value) / ABS(first_value)) * 100

        Positive value = lactate decreased
        Negative value = lactate increased

    slope_per_hour:
        (last_value - first_value) / elapsed hours

        This is a first-to-last simple slope, not an OLS regression slope.
    """
    labels_sql = ", ".join(
        "'" + variable.replace("'", "''") + "'"
        for variable in CORE_VARIABLES
    )

    return f"""
    COPY (
        WITH ordered AS (
            SELECT
                stay_id,
                label,
                charttime,
                valuenum,

                EXTRACT(
                    EPOCH FROM charttime - MIN(charttime) OVER (
                        PARTITION BY stay_id, label
                    )
                ) / 3600.0 AS hours_from_first,

                ROW_NUMBER() OVER (
                    PARTITION BY stay_id, label
                    ORDER BY charttime ASC, valuenum ASC
                ) AS rn_first,

                ROW_NUMBER() OVER (
                    PARTITION BY stay_id, label
                    ORDER BY charttime DESC, valuenum DESC
                ) AS rn_last,

                ROW_NUMBER() OVER (
                    PARTITION BY stay_id, label
                    ORDER BY valuenum DESC, charttime ASC
                ) AS rn_peak

            FROM {SOURCE_TABLE}

            WHERE label IN ({labels_sql})
              AND valuenum IS NOT NULL
              AND charttime IS NOT NULL
        ),

        summary AS (
            SELECT
                stay_id,
                label,
                COUNT(*) AS n_measurements,
                COUNT(DISTINCT charttime) AS n_distinct_times,
                AVG(valuenum) AS mean_value,
                STDDEV_SAMP(valuenum) AS std_value,
                MIN(valuenum) AS min_value,
                MAX(valuenum) AS max_value,
                PERCENTILE_CONT(0.5)
                    WITHIN GROUP (ORDER BY valuenum) AS median_value,
                MIN(charttime) AS first_time,
                MAX(charttime) AS last_time

            FROM ordered

            GROUP BY
                stay_id,
                label
        ),

        first_values AS (
            SELECT
                stay_id,
                label,
                valuenum AS first_value

            FROM ordered

            WHERE rn_first = 1
        ),

        last_values AS (
            SELECT
                stay_id,
                label,
                valuenum AS last_value

            FROM ordered

            WHERE rn_last = 1
        ),

        peak_values AS (
            SELECT
                stay_id,
                label,
                valuenum AS peak_value,
                hours_from_first AS time_to_peak_hours

            FROM ordered

            WHERE rn_peak = 1
        )

        SELECT
            s.stay_id,
            s.label,

            -- Sampling information
            s.n_measurements,
            s.n_distinct_times,
            EXTRACT(
                EPOCH FROM s.last_time - s.first_time
            ) / 3600.0 AS measurement_window_hours,

            -- Initial and final state
            f.first_value,
            l.last_value,

            -- Absolute change
            CASE
                WHEN s.n_measurements >= 2
                THEN l.last_value - f.first_value
                ELSE NULL
            END AS delta_value,

            -- Relative change
            CASE
                WHEN s.n_measurements >= 2
                 AND f.first_value IS NOT NULL
                 AND ABS(f.first_value) > 0
                THEN (
                    (l.last_value - f.first_value)
                    / ABS(f.first_value)
                ) * 100.0
                ELSE NULL
            END AS percent_change,

            -- Lactate-specific normalized recovery measure
            CASE
                WHEN s.label = 'Lactate'
                 AND s.n_measurements >= 2
                 AND f.first_value IS NOT NULL
                 AND ABS(f.first_value) > 0
                THEN (
                    (f.first_value - l.last_value)
                    / ABS(f.first_value)
                ) * 100.0
                ELSE NULL
            END AS lactate_clearance_pct,

            -- First-to-last rate of change
            CASE
                WHEN s.n_measurements >= 2
                 AND EXTRACT(
                        EPOCH FROM s.last_time - s.first_time
                     ) > 0
                THEN (
                    l.last_value - f.first_value
                ) / (
                    EXTRACT(
                        EPOCH FROM s.last_time - s.first_time
                    ) / 3600.0
                )
                ELSE NULL
            END AS slope_per_hour,

            -- Distribution and variability features
            s.mean_value,
            s.median_value,
            s.std_value,
            s.min_value,
            s.max_value,

            CASE
                WHEN s.std_value IS NOT NULL
                 AND s.mean_value IS NOT NULL
                 AND ABS(s.mean_value) > 0
                THEN s.std_value / ABS(s.mean_value)
                ELSE NULL
            END AS coefficient_of_variation,

            -- Peak information
            p.peak_value,
            p.time_to_peak_hours,

            -- Feature availability flags
            CASE
                WHEN s.n_measurements >= 2
                THEN 1
                ELSE 0
            END AS change_available,

            CASE
                WHEN s.n_measurements >= 2
                 AND EXTRACT(
                        EPOCH FROM s.last_time - s.first_time
                     ) > 0
                THEN 1
                ELSE 0
            END AS slope_available

        FROM summary AS s

        JOIN first_values AS f
          ON s.stay_id = f.stay_id
         AND s.label = f.label

        JOIN last_values AS l
          ON s.stay_id = l.stay_id
         AND s.label = l.label

        JOIN peak_values AS p
          ON s.stay_id = p.stay_id
         AND s.label = p.label

        ORDER BY
            s.stay_id,
            s.label

    ) TO STDOUT WITH CSV HEADER;
    """


def ensure_output_directory() -> None:
    """Create the results directory when it does not yet exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def check_docker_available() -> None:
    """
    Check whether Docker is available before running the SQL export.
    """
    result = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Docker is not running or cannot be reached.\n"
            "Start Docker Desktop and confirm with:\n"
            "  docker info\n\n"
            f"Docker message:\n{result.stderr.strip()}"
        )


def check_container_running() -> None:
    """
    Confirm that the PostgreSQL container is running.
    """
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            DOCKER_CONTAINER,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Container '{DOCKER_CONTAINER}' was not found.\n"
            "From the project directory run:\n"
            "  docker compose up -d"
        )

    if result.stdout.strip().lower() != "true":
        raise RuntimeError(
            f"Container '{DOCKER_CONTAINER}' exists but is not running.\n"
            "Run:\n"
            "  docker compose up -d"
        )


def run_query_to_csv() -> None:
    """
    Execute the PostgreSQL COPY query through Docker and write the output CSV.
    """
    ensure_output_directory()
    check_docker_available()
    check_container_running()

    sql = build_sql()

    command = [
        "docker",
        "exec",
        "-i",
        DOCKER_CONTAINER,
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        POSTGRES_USER,
        "-d",
        POSTGRES_DATABASE,
        "-c",
        sql,
    ]

    temporary_output = OUTPUT_CSV.with_suffix(".tmp.csv")

    try:
        with temporary_output.open("w", encoding="utf-8") as file:
            result = subprocess.run(
                command,
                stdout=file,
                stderr=subprocess.PIPE,
                text=True,
            )

        if result.returncode != 0:
            raise RuntimeError(
                "PostgreSQL query failed.\n"
                f"{result.stderr.strip()}"
            )

        if not temporary_output.exists() or temporary_output.stat().st_size == 0:
            raise RuntimeError(
                "The SQL command completed but produced an empty output file."
            )

        temporary_output.replace(OUTPUT_CSV)

    except Exception:
        if temporary_output.exists():
            temporary_output.unlink()
        raise


def validate_output(df: pd.DataFrame) -> None:
    """
    Validate required output columns and basic consistency.
    """
    required_columns = {
        "stay_id",
        "label",
        "n_measurements",
        "first_value",
        "last_value",
        "delta_value",
        "percent_change",
        "lactate_clearance_pct",
        "measurement_window_hours",
        "slope_per_hour",
        "coefficient_of_variation",
        "peak_value",
        "time_to_peak_hours",
        "change_available",
        "slope_available",
    }

    missing = sorted(required_columns.difference(df.columns))

    if missing:
        raise ValueError(
            "Output validation failed. Missing columns:\n"
            + "\n".join(f"  - {column}" for column in missing)
        )

    duplicated = df.duplicated(subset=["stay_id", "label"]).sum()

    if duplicated > 0:
        raise ValueError(
            f"Output contains {duplicated:,} duplicated stay_id-label rows."
        )

    invalid_change = df.loc[
        (df["n_measurements"] < 2)
        & df["delta_value"].notna()
    ]

    if not invalid_change.empty:
        raise ValueError(
            "Some rows with fewer than two measurements have a delta value."
        )


def print_availability_summary(df: pd.DataFrame) -> None:
    """
    Print trajectory feature availability by laboratory or vital-sign label.
    """
    summary = (
        df.groupby("label", as_index=False)
        .agg(
            rows=("stay_id", "size"),
            unique_stays=("stay_id", "nunique"),
            median_measurements=("n_measurements", "median"),
            change_available_pct=(
                "change_available",
                lambda series: series.mean() * 100.0,
            ),
            slope_available_pct=(
                "slope_available",
                lambda series: series.mean() * 100.0,
            ),
        )
        .sort_values("label")
    )

    print("\nTrajectory feature availability:")
    print(summary.to_string(index=False))


def check_output() -> None:
    """
    Load and validate the generated CSV, then print a concise report.
    """
    if not OUTPUT_CSV.exists():
        raise FileNotFoundError(f"Output file was not created: {OUTPUT_CSV}")

    df = pd.read_csv(OUTPUT_CSV, low_memory=False)

    if df.empty:
        raise ValueError("The output CSV is empty.")

    validate_output(df)

    print("\nTemporal trajectory feature engineering completed.")
    print(f"Saved to: {OUTPUT_CSV}")
    print(f"Rows: {len(df):,}")
    print(f"Unique ICU stays: {df['stay_id'].nunique():,}")
    print(f"Variables: {df['label'].nunique():,}")

    print_availability_summary(df)

    print("\nPreview:")
    preview_columns = [
        "stay_id",
        "label",
        "n_measurements",
        "first_value",
        "last_value",
        "delta_value",
        "percent_change",
        "lactate_clearance_pct",
        "slope_per_hour",
        "peak_value",
        "time_to_peak_hours",
    ]
    print(df[preview_columns].head(20).to_string(index=False))

    lactate = df.loc[
        df["label"].eq("Lactate"),
        [
            "stay_id",
            "first_value",
            "last_value",
            "percent_change",
            "lactate_clearance_pct",
        ],
    ].dropna(subset=["lactate_clearance_pct"])

    if not lactate.empty:
        print("\nLactate sign check:")
        print(
            lactate.head(5).to_string(index=False)
        )
        print(
            "\nInterpretation: positive lactate_clearance_pct means "
            "lactate decreased from first to last measurement."
        )


def main() -> None:
    print("=" * 61)
    print("Step 13. Temporal and Trajectory Feature Engineering")
    print("=" * 61)

    run_query_to_csv()
    check_output()

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
