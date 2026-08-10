# run_sql_pipeline.py

"""
input_content : sql/01_validation.sql, 02_cohort.sql, 03_vitals.sql, 04_labs.sql,
                05_trajectory.sql, 06_dataset_summary.sql (executed in this fixed order)
output_content : none returned; tables and views created inside the mimiciv PostgreSQL database
                 (row-count validation, adult ICU cohort, vitals, labs, first-24h trajectory,
                 dataset summary), plus psql output streamed to stdout
calls : docker exec -i mimic_postgres psql -v ON_ERROR_STOP=1, subprocess
side effect : mutates the database schema and contents; exits with status 1 on any failure
responsibility : Run the SQL half of the pipeline sequentially with fail-fast semantics — each file is
                 checked for existence, piped to psql via stdin, and a non-zero return code aborts the
                 whole run so no downstream step consumes partially built tables.
"""


from pathlib import Path
import subprocess
import sys
from typing import List

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
SQL_DIR = PROJECT_DIR / "sql"

SQL_FILES = [
    "01_validation.sql",
    "02_cohort.sql",
    "03_vitals.sql",
    "04_labs.sql",
    "05_trajectory.sql",
    "06_dataset_summary.sql",
]


def build_command() -> List[str]:
    return [
        "docker", "exec", "-i",
        "mimic_postgres",
        "psql",
        "-v", "ON_ERROR_STOP=1",
        "-U", "dh",
        "-d", "mimiciv",
    ]


def get_sql_path(sql_file: str) -> Path:
    return SQL_DIR / sql_file


def validate_sql_file(sql_path: Path) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"File not found: {sql_path}")


def run_sql_file(sql_file: str) -> None:
    sql_path = get_sql_path(sql_file)
    validate_sql_file(sql_path)

    print(f"\nRunning: {sql_file}")

    command = build_command()

    with open(sql_path, "r", encoding="utf-8") as f:
        result = subprocess.run(
            command,
            stdin=f,
            text=True,
        )

    if result.returncode != 0:
        raise RuntimeError(f"Error occurred in: {sql_file}")


def run_pipeline(sql_files: List[str]) -> None:
    for sql_file in sql_files:
        run_sql_file(sql_file)


def main() -> None:
    try:
        run_pipeline(SQL_FILES)
        print("\nSQL pipeline completed successfully.")
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


"""
main()
 → run_pipeline()
   → run_sql_file()
     → build_command()
     → validate_sql_file()
"""
