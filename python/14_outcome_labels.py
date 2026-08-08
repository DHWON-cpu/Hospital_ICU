# 14_outcome_labels.py

from pathlib import Path
import subprocess
import pandas as pd
from io import StringIO


PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"
OUTPUT_PATH = RESULTS_DIR / "14_outcome_labels.csv"


SQL_QUERY = """
SELECT
    co.subject_id,
    co.hadm_id,
    co.stay_id,
    co.intime,
    co.outtime,
    ad.deathtime,

    CASE
        WHEN ad.deathtime IS NOT NULL
         AND ad.deathtime >= co.intime
         AND ad.deathtime < co.intime + INTERVAL '1 day'
        THEN 1 ELSE 0
    END AS mortality_1d,

    CASE
        WHEN ad.deathtime IS NOT NULL
         AND ad.deathtime >= co.intime
         AND ad.deathtime < co.intime + INTERVAL '3 days'
        THEN 1 ELSE 0
    END AS mortality_3d,

    CASE
        WHEN ad.deathtime IS NOT NULL
         AND ad.deathtime >= co.intime
         AND ad.deathtime < co.intime + INTERVAL '7 days'
        THEN 1 ELSE 0
    END AS mortality_7d

FROM mimiciv_derived.cohort_icu_adult co
LEFT JOIN mimiciv_hosp.admissions ad
    ON co.hadm_id = ad.hadm_id
ORDER BY co.stay_id
"""


def run_query_to_dataframe(sql_query: str) -> pd.DataFrame:
    command = [
        "docker", "exec", "-i",
        "mimic_postgres",
        "psql", "-U", "dh", "-d", "mimiciv",
        "-c",
        f"\\copy ({sql_query}) TO STDOUT WITH CSV HEADER"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    return pd.read_csv(StringIO(result.stdout))


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating outcome labels from PostgreSQL...")
    df = run_query_to_dataframe(SQL_QUERY)

    print("Saving CSV file...")
    df.to_csv(OUTPUT_PATH, index=False)

    print("\nOutcome labels created successfully.")
    print(f"Output file: {OUTPUT_PATH}")
    print(f"Rows: {df.shape[0]:,}")
    print(f"Columns: {df.shape[1]:,}")

    print("\nMortality counts:")
    print(df[["mortality_1d", "mortality_3d", "mortality_7d"]].sum())

    print("\nMortality rates (%):")
    print((df[["mortality_1d", "mortality_3d", "mortality_7d"]].mean() * 100).round(2))

def run_query_to_dataframe(sql_query: str) -> pd.DataFrame:
    command = [
        "docker", "exec", "-i",
        "mimic_postgres",
        "psql", "-U", "dh", "-d", "mimiciv",
        "-c",
        f"\\copy ({sql_query}) TO STDOUT WITH CSV HEADER"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("PostgreSQL error:")
        print(result.stderr)
        raise RuntimeError("Failed to export outcome labels from PostgreSQL.")

    return pd.read_csv(StringIO(result.stdout))


if __name__ == "__main__":
    main()