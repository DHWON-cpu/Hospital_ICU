# 26_adjusted_clinical_validation_v2.py

"""
input_content : 22B_primary_cluster_labels.csv, results/15_modeling_dataset.csv (covariate source),
                results/14_outcome_labels.csv; covariates resolved by alias search
                (age, sex, ICU type, baseline lactate/creatinine/WBC/platelet first values)
output_content : results/26_adjusted_clinical_validation/ — analysis dataset, model fit summary
                 (n, events, AIC, BIC-deviance, McFadden pseudo-R2, convergence), RIWT adjusted effects,
                 all model coefficients with ORs and 95% CIs, covariate missingness table, numeric VIF table,
                 forest plot PNG, text report
calls : statsmodels GLM (Binomial, HC0 robust covariance), variance_inflation_factor, matplotlib, numpy, pandas
side effect : pins numerical-library threads to 1, creates the 26 output directory,
              writes 6 CSVs + 1 PNG + a .txt report, prints resolved covariates and effect tables to stdout
responsibility : Step 26 (v1) — test whether the RIWT-mortality association survives confounder adjustment
                 via four sequential logistic models (RIWT only -> + age/sex -> + ICU type ->
                 + baseline biomarkers) at 7-, 3-, and 1-day endpoints, with numeric covariates
                 median-imputed, categorical missingness kept as an explicit level, trajectory-defining
                 change variables deliberately excluded from the adjustment set, and 1-day flagged
                 exploratory due to outcome-window overlap.
"""

from __future__ import annotations

import io
import math
import os
import subprocess
import sys
import warnings
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor


# ============================================================
# Project paths
# ============================================================

PROJECT_DIR = Path("/Volumes/dhwon_lab1/ICU-Trajectory-Lab")
RESULTS_DIR = PROJECT_DIR / "results"

CLUSTER_LABELS_INPUT = (
    RESULTS_DIR
    / "22B_pure_trajectory_clustering"
    / "22B_primary_cluster_labels.csv"
)

MODELING_INPUT = RESULTS_DIR / "15_modeling_dataset.csv"
OUTCOMES_INPUT = RESULTS_DIR / "14_outcome_labels.csv"

# Optional demographic CSV candidates.
DEMOGRAPHIC_CANDIDATES = [
    RESULTS_DIR / "02_cohort.csv",
    RESULTS_DIR / "cohort_icu_adult.csv",
    RESULTS_DIR / "26_cohort_demographics.csv",
    PROJECT_DIR / "data" / "cohort_icu_adult.csv",
]

OUTPUT_DIR = RESULTS_DIR / "26_adjusted_clinical_validation_v2"

OUTPUT_DEMOGRAPHICS = OUTPUT_DIR / "26_cohort_demographics.csv"
OUTPUT_ANALYSIS_DATASET = OUTPUT_DIR / "26_adjusted_validation_analysis_dataset.csv"
OUTPUT_MODEL_SUMMARY = OUTPUT_DIR / "26_adjusted_model_summary.csv"
OUTPUT_RIWT_EFFECTS = OUTPUT_DIR / "26_riwt_adjusted_effects.csv"
OUTPUT_ALL_COEFFICIENTS = OUTPUT_DIR / "26_all_model_coefficients.csv"
OUTPUT_MISSINGNESS = OUTPUT_DIR / "26_covariate_missingness.csv"
OUTPUT_VIF = OUTPUT_DIR / "26_numeric_covariate_vif.csv"
OUTPUT_FOREST = OUTPUT_DIR / "26_riwt_adjusted_or_forest_plot.png"
OUTPUT_REPORT = OUTPUT_DIR / "26_adjusted_clinical_validation_report.txt"


# ============================================================
# Docker/PostgreSQL settings
# ============================================================

DOCKER_CONTAINER = "mimic_postgres"
POSTGRES_USER = "dh"
POSTGRES_DB = "mimiciv"

DEMOGRAPHIC_SQL = """
COPY (
    SELECT
        stay_id,
        anchor_age,
        gender,
        first_careunit
    FROM mimiciv_derived.cohort_icu_adult
) TO STDOUT WITH CSV HEADER;
"""


# ============================================================
# Analysis configuration
# ============================================================

PRIMARY_OUTCOME = "mortality_7d"
SECONDARY_OUTCOMES = ["mortality_3d", "mortality_1d"]

BASELINE_BIOMARKERS = [
    "lactate_first_value",
    "creatinine_first_value",
    "white_blood_cells_first_value",
    "platelet_count_first_value",
]

MODEL_DEFINITIONS = {
    "Model 1: RIWT only": [
        "riwt",
    ],
    "Model 2: + age and sex": [
        "riwt",
        "age",
        "sex",
    ],
    "Model 3: + ICU type": [
        "riwt",
        "age",
        "sex",
        "icu_type",
    ],
    "Model 4: + baseline biomarkers": [
        "riwt",
        "age",
        "sex",
        "icu_type",
        "lactate_first",
        "creatinine_first",
        "wbc_first",
        "platelet_first",
    ],
}


# ============================================================
# Utilities
# ============================================================

def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv_required(path: Path, name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{name} not found: {path}")

    return pd.read_csv(path, low_memory=False)


def load_demographics_from_csv() -> tuple[pd.DataFrame | None, Path | None]:
    for path in DEMOGRAPHIC_CANDIDATES:
        if path.exists():
            demographics = pd.read_csv(path, low_memory=False)
            return demographics, path

    return None, None


def load_demographics_from_postgres() -> pd.DataFrame:
    command = [
        "docker",
        "exec",
        DOCKER_CONTAINER,
        "psql",
        "-U",
        POSTGRES_USER,
        "-d",
        POSTGRES_DB,
        "-c",
        DEMOGRAPHIC_SQL,
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "The docker command was not found. Start Docker Desktop "
            "or export cohort_icu_adult to a CSV candidate path."
        ) from error
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip()
        raise RuntimeError(
            "Could not read cohort_icu_adult from PostgreSQL.\n"
            f"Docker/psql error:\n{stderr}"
        ) from error

    csv_text = result.stdout.strip()

    if not csv_text:
        raise RuntimeError(
            "PostgreSQL returned no demographic data."
        )

    demographics = pd.read_csv(io.StringIO(csv_text))
    return demographics


def normalize_demographic_columns(
    demographics: pd.DataFrame,
) -> pd.DataFrame:
    aliases = {
        "stay_id": ["stay_id"],
        "anchor_age": ["anchor_age", "age"],
        "gender": ["gender", "sex"],
        "first_careunit": [
            "first_careunit",
            "icu_type",
            "careunit",
        ],
    }

    rename_map: dict[str, str] = {}
    lower_map = {
        column.lower(): column
        for column in demographics.columns
    }

    for canonical, candidates in aliases.items():
        source = None

        for candidate in candidates:
            if candidate.lower() in lower_map:
                source = lower_map[candidate.lower()]
                break

        if source is None:
            raise ValueError(
                "Demographic data is missing required column "
                f"for {canonical}. Found columns: "
                f"{list(demographics.columns)}"
            )

        rename_map[source] = canonical

    result = demographics.rename(columns=rename_map)[
        [
            "stay_id",
            "anchor_age",
            "gender",
            "first_careunit",
        ]
    ].copy()

    result = result.drop_duplicates(subset=["stay_id"])

    return result


def load_demographics() -> tuple[pd.DataFrame, str]:
    demographics, path = load_demographics_from_csv()

    if demographics is not None and path is not None:
        source = f"CSV: {path}"
    else:
        print(
            "  No demographic CSV found; querying Docker PostgreSQL..."
        )
        demographics = load_demographics_from_postgres()
        source = (
            "PostgreSQL: mimiciv_derived.cohort_icu_adult"
        )

    demographics = normalize_demographic_columns(
        demographics
    )

    return demographics, source


def validate_inputs(
    labels: pd.DataFrame,
    modeling: pd.DataFrame,
    outcomes: pd.DataFrame,
    demographics: pd.DataFrame,
) -> None:
    for name, frame in [
        ("Cluster labels", labels),
        ("Modeling dataset", modeling),
        ("Outcome labels", outcomes),
        ("Demographics", demographics),
    ]:
        if "stay_id" not in frame.columns:
            raise ValueError(
                f"{name} does not contain stay_id."
            )

    if "trajectory_cluster" not in labels.columns:
        raise ValueError(
            "Cluster labels do not contain trajectory_cluster."
        )

    clusters = sorted(
        labels["trajectory_cluster"]
        .dropna()
        .unique()
        .tolist()
    )

    if clusters != [0, 1]:
        raise ValueError(
            f"Expected clusters [0, 1], found {clusters}."
        )

    missing_biomarkers = sorted(
        set(BASELINE_BIOMARKERS).difference(
            modeling.columns
        )
    )

    if missing_biomarkers:
        raise ValueError(
            "Modeling dataset is missing baseline biomarkers:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing_biomarkers
            )
        )

    for outcome in [PRIMARY_OUTCOME] + SECONDARY_OUTCOMES:
        if outcome not in outcomes.columns:
            raise ValueError(
                f"Outcome file does not contain {outcome}."
            )


# ============================================================
# Dataset construction
# ============================================================

def create_analysis_dataset(
    labels: pd.DataFrame,
    modeling: pd.DataFrame,
    outcomes: pd.DataFrame,
    demographics: pd.DataFrame,
) -> pd.DataFrame:
    modeling_selected = (
        modeling[
            ["stay_id"] + BASELINE_BIOMARKERS
        ]
        .drop_duplicates(subset=["stay_id"])
        .copy()
    )

    outcomes_selected = (
        outcomes[
            ["stay_id", PRIMARY_OUTCOME]
            + SECONDARY_OUTCOMES
        ]
        .drop_duplicates(subset=["stay_id"])
        .copy()
    )

    analysis = (
        labels[
            ["stay_id", "trajectory_cluster"]
        ]
        .merge(
            demographics,
            on="stay_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            modeling_selected,
            on="stay_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            outcomes_selected,
            on="stay_id",
            how="left",
            validate="one_to_one",
        )
    )

    analysis["riwt"] = (
        analysis["trajectory_cluster"].eq(1)
    ).astype(int)

    analysis["age"] = pd.to_numeric(
        analysis["anchor_age"],
        errors="coerce",
    )

    analysis["sex"] = (
        analysis["gender"]
        .astype("string")
        .str.strip()
        .str.upper()
        .replace(
            {
                "MALE": "M",
                "FEMALE": "F",
            }
        )
    )

    analysis["icu_type"] = (
        analysis["first_careunit"]
        .astype("string")
        .str.strip()
        .replace({"": pd.NA})
    )

    analysis["lactate_first"] = pd.to_numeric(
        analysis["lactate_first_value"],
        errors="coerce",
    )
    analysis["creatinine_first"] = pd.to_numeric(
        analysis["creatinine_first_value"],
        errors="coerce",
    )
    analysis["wbc_first"] = pd.to_numeric(
        analysis["white_blood_cells_first_value"],
        errors="coerce",
    )
    analysis["platelet_first"] = pd.to_numeric(
        analysis["platelet_count_first_value"],
        errors="coerce",
    )

    return analysis


def create_missingness_table(
    analysis: pd.DataFrame,
) -> pd.DataFrame:
    concepts = [
        "age",
        "sex",
        "icu_type",
        "lactate_first",
        "creatinine_first",
        "wbc_first",
        "platelet_first",
    ]

    rows = []

    for concept in concepts:
        missing = int(analysis[concept].isna().sum())

        rows.append(
            {
                "concept": concept,
                "n_missing": missing,
                "missing_pct": (
                    missing / len(analysis) * 100
                ),
            }
        )

    return pd.DataFrame(rows)


def clean_covariates(
    analysis: pd.DataFrame,
) -> pd.DataFrame:
    result = analysis.copy()

    numeric_terms = [
        "age",
        "lactate_first",
        "creatinine_first",
        "wbc_first",
        "platelet_first",
    ]

    for term in numeric_terms:
        median = result[term].median()

        if pd.isna(median):
            raise ValueError(
                f"Cannot impute {term}; all values are missing."
            )

        result[term] = result[term].fillna(median)

    result["sex"] = (
        result["sex"]
        .fillna("Missing")
        .astype("category")
    )

    result["icu_type"] = (
        result["icu_type"]
        .fillna("Missing")
        .astype("category")
    )

    return result


# ============================================================
# Design matrix and models
# ============================================================

def build_design_matrix(
    analysis: pd.DataFrame,
    terms: list[str],
) -> pd.DataFrame:
    frames = []

    for term in terms:
        if term in ["sex", "icu_type"]:
            dummies = pd.get_dummies(
                analysis[term],
                prefix=term,
                drop_first=True,
                dtype=float,
            )
            frames.append(dummies)
        else:
            frames.append(
                analysis[[term]].astype(float)
            )

    x = pd.concat(frames, axis=1)

    variable_columns = [
        column
        for column in x.columns
        if x[column].nunique(dropna=False) > 1
    ]

    x = x[variable_columns]
    x = sm.add_constant(
        x,
        has_constant="add",
    )

    return x


def fit_logistic_model(
    analysis: pd.DataFrame,
    outcome: str,
    model_name: str,
    terms: list[str],
) -> tuple[pd.DataFrame, dict[str, object]]:
    x = build_design_matrix(
        analysis,
        terms,
    )

    y = pd.to_numeric(
        analysis[outcome],
        errors="coerce",
    )

    mask = (
        y.notna()
        & x.notna().all(axis=1)
    )

    x_model = x.loc[mask].astype(float)
    y_model = y.loc[mask].astype(int)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        model = sm.GLM(
            y_model,
            x_model,
            family=sm.families.Binomial(),
        )

        fitted = model.fit(
            cov_type="HC0",
            maxiter=200,
        )

    confidence = fitted.conf_int()

    coefficients = pd.DataFrame(
        {
            "term": fitted.params.index,
            "coefficient": fitted.params.values,
            "standard_error": fitted.bse.values,
            "p_value": fitted.pvalues.values,
            "odds_ratio": np.exp(
                fitted.params.values
            ),
            "or_ci_lower": np.exp(
                confidence[0].values
            ),
            "or_ci_upper": np.exp(
                confidence[1].values
            ),
        }
    )

    coefficients.insert(
        0,
        "outcome",
        outcome,
    )
    coefficients.insert(
        0,
        "model",
        model_name,
    )

    info = {
        "model": model_name,
        "outcome": outcome,
        "predictor_concepts": "|".join(terms),
        "design_matrix_columns": (
            x_model.shape[1] - 1
        ),
        "n": len(y_model),
        "events": int(y_model.sum()),
        "event_rate_pct": float(
            y_model.mean() * 100
        ),
        "aic": float(fitted.aic),
        "bic_deviance": float(
            fitted.bic_deviance
        ),
        "pseudo_r2_mcfadden": float(
            1 - fitted.llf / fitted.llnull
        ),
        "converged": int(
            bool(fitted.converged)
        ),
    }

    return coefficients, info


def run_models(
    analysis: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    coefficient_frames = []
    model_rows = []

    outcomes = [
        PRIMARY_OUTCOME,
        *SECONDARY_OUTCOMES,
    ]

    for outcome in outcomes:
        for model_name, terms in MODEL_DEFINITIONS.items():
            print(
                f"  Fitting {outcome} — {model_name}"
            )

            coefficients, info = fit_logistic_model(
                analysis=analysis,
                outcome=outcome,
                model_name=model_name,
                terms=terms,
            )

            coefficient_frames.append(
                coefficients
            )
            model_rows.append(info)

    return (
        pd.concat(
            coefficient_frames,
            ignore_index=True,
        ),
        pd.DataFrame(model_rows),
    )


def extract_riwt_effects(
    coefficients: pd.DataFrame,
    model_summary: pd.DataFrame,
) -> pd.DataFrame:
    effects = coefficients.loc[
        coefficients["term"].eq("riwt")
    ].copy()

    effects = effects.merge(
        model_summary[
            [
                "model",
                "outcome",
                "predictor_concepts",
                "n",
                "events",
                "aic",
                "pseudo_r2_mcfadden",
                "converged",
            ]
        ],
        on=["model", "outcome"],
        how="left",
        validate="one_to_one",
    )

    effects["significant_005"] = (
        effects["p_value"] < 0.05
    ).astype(int)

    return effects


def calculate_vif(
    analysis: pd.DataFrame,
) -> pd.DataFrame:
    terms = [
        "riwt",
        "age",
        "lactate_first",
        "creatinine_first",
        "wbc_first",
        "platelet_first",
    ]

    x = analysis[terms].astype(float)
    x = x.loc[:, x.nunique() > 1]
    x = sm.add_constant(
        x,
        has_constant="add",
    )

    rows = []

    for index, column in enumerate(x.columns):
        if column == "const":
            continue

        try:
            vif = float(
                variance_inflation_factor(
                    x.to_numpy(),
                    index,
                )
            )
        except Exception:
            vif = np.nan

        rows.append(
            {
                "term": column,
                "vif": vif,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# Visualization and report
# ============================================================

def create_forest_plot(
    riwt_effects: pd.DataFrame,
) -> None:
    plot_df = riwt_effects.loc[
        riwt_effects["outcome"].eq(
            PRIMARY_OUTCOME
        )
    ].copy()

    order = list(
        MODEL_DEFINITIONS.keys()
    )

    plot_df["model"] = pd.Categorical(
        plot_df["model"],
        categories=order,
        ordered=True,
    )

    plot_df = plot_df.sort_values(
        "model"
    )

    y = np.arange(len(plot_df))
    odds_ratio = plot_df[
        "odds_ratio"
    ].to_numpy()
    lower = plot_df[
        "or_ci_lower"
    ].to_numpy()
    upper = plot_df[
        "or_ci_upper"
    ].to_numpy()

    xerr = np.vstack(
        [
            odds_ratio - lower,
            upper - odds_ratio,
        ]
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.errorbar(
        odds_ratio,
        y,
        xerr=xerr,
        fmt="o",
        capsize=5,
    )

    ax.axvline(
        1.0,
        linestyle="--",
        linewidth=1,
    )

    ax.set_yticks(y)
    ax.set_yticklabels(
        plot_df["model"]
    )
    ax.set_xlabel(
        "Odds ratio for RIWT"
    )
    ax.set_title(
        "Adjusted Association Between RIWT "
        "and 7-Day Mortality"
    )

    fig.tight_layout()
    fig.savefig(
        OUTPUT_FOREST,
        dpi=300,
    )
    plt.close(fig)


def build_report(
    analysis: pd.DataFrame,
    demographic_source: str,
    missingness: pd.DataFrame,
    riwt_effects: pd.DataFrame,
    model_summary: pd.DataFrame,
) -> str:
    primary = riwt_effects.loc[
        riwt_effects["outcome"].eq(
            PRIMARY_OUTCOME
        )
    ].copy()

    lines = [
        "=" * 86,
        "STEP 26 V2. FULLY ADJUSTED CLINICAL VALIDATION OF RIWT",
        "=" * 86,
        "",
        f"Demographic source: {demographic_source}",
        f"Analysis rows: {len(analysis):,}",
        f"RIWT cases: {int(analysis['riwt'].sum()):,}",
        (
            f"RIWT prevalence: "
            f"{analysis['riwt'].mean() * 100:.2f}%"
        ),
        "",
        "Primary outcome:",
        "- 7-day mortality",
        "",
        "Adjustment variables:",
        "- Age",
        "- Sex",
        "- First ICU care unit",
        "- Initial lactate",
        "- Initial creatinine",
        "- Initial WBC",
        "- Initial platelet count",
        "",
        "Sequential 7-day mortality models:",
    ]

    for row in primary.itertuples(
        index=False
    ):
        lines.append(
            f"- {row.model}: "
            f"RIWT OR={row.odds_ratio:.3f} "
            f"(95% CI "
            f"{row.or_ci_lower:.3f}–"
            f"{row.or_ci_upper:.3f}), "
            f"p={row.p_value:.3e}, "
            f"n={row.n:,}, "
            f"events={row.events:,}"
        )

    full_name = (
        "Model 4: + baseline biomarkers"
    )

    full = primary.loc[
        primary["model"].eq(full_name)
    ].iloc[0]

    lines.extend(
        [
            "",
            "Primary conclusion:",
        ]
    )

    if (
        full["odds_ratio"] > 1
        and full["or_ci_lower"] > 1
    ):
        lines.append(
            (
                "- RIWT remained independently associated "
                "with higher 7-day mortality after adjustment "
                "for age, sex, ICU type, and baseline "
                "biochemical values."
            )
        )
    else:
        lines.append(
            (
                "- The fully adjusted RIWT association "
                "with 7-day mortality was not statistically "
                "conclusive."
            )
        )

    lines.extend(
        [
            "",
            "Interpretation limits:",
            (
                "- This is an adjusted observational "
                "association, not proof of causation."
            ),
            (
                "- The trajectory-defining change variables "
                "were not included as covariates."
            ),
            (
                "- One-day mortality remains exploratory "
                "because it overlaps the trajectory window."
            ),
            (
                "- External and prospective validation "
                "remain required."
            ),
            "",
            "Covariate missingness before imputation:",
        ]
    )

    for row in missingness.itertuples(
        index=False
    ):
        lines.append(
            f"- {row.concept}: "
            f"{int(row.n_missing):,} "
            f"({row.missing_pct:.2f}%)"
        )

    lines.extend(
        [
            "",
            "Model fit for 7-day mortality:",
        ]
    )

    for row in model_summary.loc[
        model_summary["outcome"].eq(
            PRIMARY_OUTCOME
        )
    ].itertuples(index=False):
        lines.append(
            f"- {row.model}: "
            f"AIC={row.aic:.2f}, "
            f"McFadden pseudo-R²="
            f"{row.pseudo_r2_mcfadden:.4f}, "
            f"converged={row.converged}"
        )

    lines.extend(
        [
            "",
            "=" * 86,
        ]
    )

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 86)
    print(
        "Step 26 V2. Fully Adjusted "
        "Clinical Validation"
    )
    print("=" * 86)

    ensure_output_directory()

    print("Loading primary analysis inputs...")
    labels = read_csv_required(
        CLUSTER_LABELS_INPUT,
        "Cluster labels",
    )
    modeling = read_csv_required(
        MODELING_INPUT,
        "Modeling dataset",
    )
    outcomes = read_csv_required(
        OUTCOMES_INPUT,
        "Outcome labels",
    )

    print("Loading demographics and ICU type...")
    demographics, demographic_source = (
        load_demographics()
    )

    print(
        f"  Demographic source: "
        f"{demographic_source}"
    )
    print(
        f"  Demographic rows: "
        f"{len(demographics):,}"
    )

    validate_inputs(
        labels,
        modeling,
        outcomes,
        demographics,
    )

    demographics.to_csv(
        OUTPUT_DEMOGRAPHICS,
        index=False,
    )

    print("Building fully adjusted analysis dataset...")
    analysis_raw = create_analysis_dataset(
        labels,
        modeling,
        outcomes,
        demographics,
    )

    missingness = create_missingness_table(
        analysis_raw
    )

    analysis = clean_covariates(
        analysis_raw
    )

    missing_demographics = int(
        analysis_raw[
            [
                "anchor_age",
                "gender",
                "first_careunit",
            ]
        ].isna().all(axis=1).sum()
    )

    if missing_demographics:
        raise ValueError(
            f"{missing_demographics:,} analysis stays "
            "have no matched demographic record."
        )

    print(
        f"Analysis rows: {len(analysis):,}"
    )
    print(
        f"RIWT cases: "
        f"{int(analysis['riwt'].sum()):,} "
        f"({analysis['riwt'].mean() * 100:.2f}%)"
    )

    print("Fitting sequential logistic regression models...")
    coefficients, model_summary = run_models(
        analysis
    )

    riwt_effects = extract_riwt_effects(
        coefficients,
        model_summary,
    )

    vif = calculate_vif(analysis)

    print("Creating adjusted OR forest plot...")
    create_forest_plot(
        riwt_effects
    )

    report = build_report(
        analysis=analysis,
        demographic_source=demographic_source,
        missingness=missingness,
        riwt_effects=riwt_effects,
        model_summary=model_summary,
    )

    analysis.to_csv(
        OUTPUT_ANALYSIS_DATASET,
        index=False,
    )
    model_summary.to_csv(
        OUTPUT_MODEL_SUMMARY,
        index=False,
    )
    riwt_effects.to_csv(
        OUTPUT_RIWT_EFFECTS,
        index=False,
    )
    coefficients.to_csv(
        OUTPUT_ALL_COEFFICIENTS,
        index=False,
    )
    missingness.to_csv(
        OUTPUT_MISSINGNESS,
        index=False,
    )
    vif.to_csv(
        OUTPUT_VIF,
        index=False,
    )
    OUTPUT_REPORT.write_text(
        report,
        encoding="utf-8",
    )

    print("")
    print("RIWT adjusted effects:")
    print(
        riwt_effects[
            [
                "outcome",
                "model",
                "odds_ratio",
                "or_ci_lower",
                "or_ci_upper",
                "p_value",
                "n",
                "events",
            ]
        ].to_string(index=False)
    )

    print("")
    print("Saved all outputs to:")
    print(OUTPUT_DIR)
    print("")
    print("Completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(
            "\nInterrupted by user.",
            file=sys.stderr,
        )
        sys.exit(130)
    except Exception as error:
        print(
            f"\nERROR: {error}",
            file=sys.stderr,
        )
        sys.exit(1)
