# 26_adjusted_clinical_validation.py

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

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from pathlib import Path
import sys
import warnings

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

OUTPUT_DIR = RESULTS_DIR / "26_adjusted_clinical_validation"

OUTPUT_ANALYSIS_DATASET = (
    OUTPUT_DIR / "26_adjusted_validation_analysis_dataset.csv"
)
OUTPUT_MODEL_SUMMARY = (
    OUTPUT_DIR / "26_adjusted_model_summary.csv"
)
OUTPUT_RIWT_EFFECTS = (
    OUTPUT_DIR / "26_riwt_adjusted_effects.csv"
)
OUTPUT_ALL_COEFFICIENTS = (
    OUTPUT_DIR / "26_all_model_coefficients.csv"
)
OUTPUT_MISSINGNESS = (
    OUTPUT_DIR / "26_covariate_missingness.csv"
)
OUTPUT_VIF = OUTPUT_DIR / "26_numeric_covariate_vif.csv"
OUTPUT_FOREST = OUTPUT_DIR / "26_riwt_adjusted_or_forest_plot.png"
OUTPUT_REPORT = (
    OUTPUT_DIR / "26_adjusted_clinical_validation_report.txt"
)


# ============================================================
# Analysis configuration
# ============================================================

PRIMARY_OUTCOME = "mortality_7d"
SECONDARY_OUTCOMES = ["mortality_3d", "mortality_1d"]

# Candidate aliases are searched in this order.
COLUMN_ALIASES = {
    "age": [
        "anchor_age",
        "age",
        "admission_age",
    ],
    "sex": [
        "gender",
        "sex",
    ],
    "icu_type": [
        "first_careunit",
        "icu_type",
        "careunit",
        "first_icu",
    ],
    "lactate_first": [
        "lactate_first_value",
        "Lactate_first_value",
    ],
    "creatinine_first": [
        "creatinine_first_value",
        "Creatinine_first_value",
    ],
    "wbc_first": [
        "white_blood_cells_first_value",
        "wbc_first_value",
        "White_Blood_Cells_first_value",
    ],
    "platelet_first": [
        "platelet_count_first_value",
        "platelet_first_value",
        "Platelet_Count_first_value",
    ],
}

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

REFERENCE_CLUSTER = 0
EXPOSURE_CLUSTER = 1


# ============================================================
# Utilities
# ============================================================

def ensure_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [
        CLUSTER_LABELS_INPUT,
        MODELING_INPUT,
        OUTCOMES_INPUT,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    labels = pd.read_csv(CLUSTER_LABELS_INPUT, low_memory=False)
    modeling = pd.read_csv(MODELING_INPUT, low_memory=False)
    outcomes = pd.read_csv(OUTCOMES_INPUT, low_memory=False)

    return labels, modeling, outcomes


def find_column(
    columns: pd.Index,
    aliases: list[str],
) -> str | None:
    exact_map = {column.lower(): column for column in columns}

    for alias in aliases:
        if alias.lower() in exact_map:
            return exact_map[alias.lower()]

    return None


def resolve_covariates(
    modeling: pd.DataFrame,
) -> dict[str, str | None]:
    return {
        concept: find_column(
            modeling.columns,
            aliases,
        )
        for concept, aliases in COLUMN_ALIASES.items()
    }


def validate_core_inputs(
    labels: pd.DataFrame,
    modeling: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> None:
    for name, frame in [
        ("Cluster labels", labels),
        ("Modeling dataset", modeling),
        ("Outcome labels", outcomes),
    ]:
        if "stay_id" not in frame.columns:
            raise ValueError(f"{name} does not contain stay_id.")

    if "trajectory_cluster" not in labels.columns:
        raise ValueError(
            "Cluster labels do not contain trajectory_cluster."
        )

    clusters = sorted(
        labels["trajectory_cluster"].dropna().unique().tolist()
    )

    if clusters != [0, 1]:
        raise ValueError(
            f"Expected clusters [0, 1], found {clusters}."
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
    resolved: dict[str, str | None],
) -> pd.DataFrame:
    selected_modeling_columns = ["stay_id"]

    for source_column in resolved.values():
        if source_column is not None:
            selected_modeling_columns.append(source_column)

    selected_modeling_columns = list(
        dict.fromkeys(selected_modeling_columns)
    )

    modeling_selected = (
        modeling[selected_modeling_columns]
        .drop_duplicates(subset=["stay_id"])
        .copy()
    )

    outcomes_selected = (
        outcomes[
            ["stay_id", PRIMARY_OUTCOME] + SECONDARY_OUTCOMES
        ]
        .drop_duplicates(subset=["stay_id"])
        .copy()
    )

    analysis = (
        labels[["stay_id", "trajectory_cluster"]]
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
        analysis["trajectory_cluster"].eq(EXPOSURE_CLUSTER)
    ).astype(int)

    for concept, source_column in resolved.items():
        if source_column is not None:
            analysis[concept] = analysis[source_column]

    return analysis


def clean_covariates(
    analysis: pd.DataFrame,
    resolved: dict[str, str | None],
) -> pd.DataFrame:
    result = analysis.copy()

    numeric_concepts = [
        "age",
        "lactate_first",
        "creatinine_first",
        "wbc_first",
        "platelet_first",
    ]

    for concept in numeric_concepts:
        if resolved.get(concept) is not None:
            result[concept] = pd.to_numeric(
                result[concept],
                errors="coerce",
            )

    if resolved.get("sex") is not None:
        result["sex"] = (
            result["sex"]
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

    if resolved.get("icu_type") is not None:
        result["icu_type"] = (
            result["icu_type"]
            .astype("string")
            .str.strip()
            .replace({"": pd.NA})
        )

    # Median imputation for numeric covariates.
    for concept in numeric_concepts:
        if concept in result.columns:
            median = result[concept].median()
            result[concept] = result[concept].fillna(median)

    # Explicit missing category for categorical variables.
    for concept in ["sex", "icu_type"]:
        if concept in result.columns:
            result[concept] = (
                result[concept]
                .fillna("Missing")
                .astype("category")
            )

    return result


def create_missingness_table(
    analysis: pd.DataFrame,
    resolved: dict[str, str | None],
) -> pd.DataFrame:
    rows = []

    for concept, source_column in resolved.items():
        if source_column is None:
            rows.append(
                {
                    "concept": concept,
                    "source_column": None,
                    "available": 0,
                    "n_missing": np.nan,
                    "missing_pct": np.nan,
                }
            )
        else:
            missing = int(analysis[concept].isna().sum())
            rows.append(
                {
                    "concept": concept,
                    "source_column": source_column,
                    "available": 1,
                    "n_missing": missing,
                    "missing_pct": missing / len(analysis) * 100,
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# Design matrix
# ============================================================

def available_terms(
    requested_terms: list[str],
    analysis: pd.DataFrame,
) -> list[str]:
    return [
        term
        for term in requested_terms
        if term in analysis.columns
    ]


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

    if not frames:
        raise ValueError("No predictors are available.")

    x = pd.concat(frames, axis=1)

    # Drop zero-variance predictors.
    variable_columns = [
        column
        for column in x.columns
        if x[column].nunique(dropna=False) > 1
    ]

    x = x[variable_columns]
    x = sm.add_constant(x, has_constant="add")

    return x


# ============================================================
# Regression modeling
# ============================================================

def fit_logistic_model(
    analysis: pd.DataFrame,
    outcome: str,
    model_name: str,
    requested_terms: list[str],
) -> tuple[
    pd.DataFrame,
    dict[str, float | int | str],
]:
    terms = available_terms(
        requested_terms,
        analysis,
    )

    x = build_design_matrix(analysis, terms)
    y = analysis[outcome].astype(int)

    complete_mask = (
        y.notna()
        & x.notna().all(axis=1)
    )

    x_model = x.loc[complete_mask].astype(float)
    y_model = y.loc[complete_mask].astype(int)

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

    conf_int = fitted.conf_int()

    coefficients = pd.DataFrame(
        {
            "term": fitted.params.index,
            "coefficient": fitted.params.values,
            "standard_error": fitted.bse.values,
            "p_value": fitted.pvalues.values,
            "odds_ratio": np.exp(fitted.params.values),
            "or_ci_lower": np.exp(conf_int[0].values),
            "or_ci_upper": np.exp(conf_int[1].values),
        }
    )

    coefficients.insert(0, "outcome", outcome)
    coefficients.insert(0, "model", model_name)

    model_info = {
        "model": model_name,
        "outcome": outcome,
        "requested_predictor_count": len(requested_terms),
        "used_predictor_concepts": "|".join(terms),
        "design_matrix_columns": x_model.shape[1] - 1,
        "n": len(y_model),
        "events": int(y_model.sum()),
        "event_rate_pct": float(y_model.mean() * 100),
        "aic": float(fitted.aic),
        "bic_deviance": float(fitted.bic_deviance),
        "pseudo_r2_mcfadden": float(
            1 - fitted.llf / fitted.llnull
        ),
        "converged": int(bool(fitted.converged)),
    }

    return coefficients, model_info


def run_all_models(
    analysis: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    coefficient_frames = []
    model_rows = []

    for outcome in [PRIMARY_OUTCOME] + SECONDARY_OUTCOMES:
        for model_name, requested_terms in MODEL_DEFINITIONS.items():
            print(f"  Fitting {outcome} — {model_name}")

            coefficients, model_info = fit_logistic_model(
                analysis=analysis,
                outcome=outcome,
                model_name=model_name,
                requested_terms=requested_terms,
            )

            coefficient_frames.append(coefficients)
            model_rows.append(model_info)

    all_coefficients = pd.concat(
        coefficient_frames,
        ignore_index=True,
    )

    model_summary = pd.DataFrame(model_rows)

    return all_coefficients, model_summary


def extract_riwt_effects(
    all_coefficients: pd.DataFrame,
    model_summary: pd.DataFrame,
) -> pd.DataFrame:
    effects = all_coefficients.loc[
        all_coefficients["term"].eq("riwt")
    ].copy()

    effects = effects.merge(
        model_summary[
            [
                "model",
                "outcome",
                "used_predictor_concepts",
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


# ============================================================
# Collinearity diagnostics
# ============================================================

def calculate_vif(
    analysis: pd.DataFrame,
) -> pd.DataFrame:
    numeric_terms = [
        term
        for term in [
            "riwt",
            "age",
            "lactate_first",
            "creatinine_first",
            "wbc_first",
            "platelet_first",
        ]
        if term in analysis.columns
    ]

    if len(numeric_terms) < 2:
        return pd.DataFrame()

    x = analysis[numeric_terms].astype(float).copy()
    x = x.loc[:, x.nunique() > 1]

    if x.shape[1] < 2:
        return pd.DataFrame()

    x = sm.add_constant(x, has_constant="add")

    rows = []

    for index, column in enumerate(x.columns):
        if column == "const":
            continue

        try:
            value = float(
                variance_inflation_factor(
                    x.to_numpy(),
                    index,
                )
            )
        except Exception:
            value = np.nan

        rows.append(
            {
                "term": column,
                "vif": value,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# Visualization
# ============================================================

def create_forest_plot(
    riwt_effects: pd.DataFrame,
) -> None:
    plot_df = riwt_effects.loc[
        riwt_effects["outcome"].eq(PRIMARY_OUTCOME)
    ].copy()

    model_order = list(MODEL_DEFINITIONS.keys())

    plot_df["model"] = pd.Categorical(
        plot_df["model"],
        categories=model_order,
        ordered=True,
    )

    plot_df = plot_df.sort_values("model")

    y = np.arange(len(plot_df))
    odds_ratios = plot_df["odds_ratio"].to_numpy()
    lower = plot_df["or_ci_lower"].to_numpy()
    upper = plot_df["or_ci_upper"].to_numpy()

    xerr = np.vstack(
        [
            odds_ratios - lower,
            upper - odds_ratios,
        ]
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.errorbar(
        odds_ratios,
        y,
        xerr=xerr,
        fmt="o",
        capsize=5,
    )

    ax.axvline(1.0, linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["model"])
    ax.set_xlabel("Odds ratio for RIWT membership")
    ax.set_title(
        "Adjusted Association Between RIWT and 7-Day Mortality"
    )

    for index, row in enumerate(plot_df.itertuples(index=False)):
        ax.annotate(
            (
                f"OR {row.odds_ratio:.2f} "
                f"({row.or_ci_lower:.2f}–{row.or_ci_upper:.2f})"
            ),
            (
                row.odds_ratio,
                index,
            ),
            xytext=(8, 6),
            textcoords="offset points",
            fontsize=9,
        )

    fig.tight_layout()
    fig.savefig(OUTPUT_FOREST, dpi=300)
    plt.close(fig)


# ============================================================
# Reporting
# ============================================================

def build_report(
    analysis: pd.DataFrame,
    resolved: dict[str, str | None],
    missingness: pd.DataFrame,
    riwt_effects: pd.DataFrame,
    model_summary: pd.DataFrame,
) -> str:
    primary_effects = riwt_effects.loc[
        riwt_effects["outcome"].eq(PRIMARY_OUTCOME)
    ].copy()

    lines = [
        "=" * 84,
        "STEP 26. ADJUSTED CLINICAL VALIDATION OF RIWT",
        "=" * 84,
        "",
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
        "Secondary outcomes:",
        "- 3-day mortality",
        "- 1-day mortality (exploratory because the trajectory window overlaps)",
        "",
        "Resolved covariates:",
    ]

    for concept, source in resolved.items():
        lines.append(
            f"- {concept}: "
            f"{source if source is not None else 'NOT FOUND'}"
        )

    lines.extend(
        [
            "",
            "Sequential logistic regression models:",
        ]
    )

    for row in primary_effects.itertuples(index=False):
        lines.append(
            f"- {row.model}: "
            f"RIWT OR={row.odds_ratio:.3f} "
            f"(95% CI {row.or_ci_lower:.3f}–"
            f"{row.or_ci_upper:.3f}), "
            f"p={row.p_value:.3e}, "
            f"n={row.n:,}, events={row.events:,}"
        )

    final_model_name = list(MODEL_DEFINITIONS.keys())[-1]
    final_effect = primary_effects.loc[
        primary_effects["model"].eq(final_model_name)
    ]

    lines.extend(["", "Primary interpretation:"])

    if not final_effect.empty:
        row = final_effect.iloc[0]

        if (
            row["odds_ratio"] > 1
            and row["or_ci_lower"] > 1
        ):
            lines.append(
                (
                    "- RIWT remained independently associated with "
                    "higher 7-day mortality after adjustment for the "
                    "available demographic, ICU-type, and baseline "
                    "biochemical covariates."
                )
            )
        elif (
            row["odds_ratio"] < 1
            and row["or_ci_upper"] < 1
        ):
            lines.append(
                (
                    "- RIWT was independently associated with lower "
                    "7-day mortality after full adjustment."
                )
            )
        else:
            lines.append(
                (
                    "- The fully adjusted association between RIWT "
                    "and 7-day mortality was not statistically conclusive."
                )
            )

    lines.extend(
        [
            "",
            "Methodological cautions:",
            (
                "- Odds ratios are adjusted associations and do not "
                "establish causation."
            ),
            (
                "- Trajectory-defining change variables were deliberately "
                "excluded from the adjustment set."
            ),
            (
                "- Baseline covariates were median-imputed for numeric "
                "variables; categorical missingness was retained as an "
                "explicit category."
            ),
            (
                "- The 1-day mortality analysis is exploratory because "
                "the outcome can overlap the first-24-hour phenotype window."
            ),
            (
                "- External and prospective validation remain necessary "
                "before clinical deployment."
            ),
            "",
            "Model fit summary:",
        ]
    )

    for row in model_summary.loc[
        model_summary["outcome"].eq(PRIMARY_OUTCOME)
    ].itertuples(index=False):
        lines.append(
            f"- {row.model}: AIC={row.aic:.2f}, "
            f"McFadden pseudo-R²={row.pseudo_r2_mcfadden:.4f}, "
            f"converged={row.converged}"
        )

    lines.extend(
        [
            "",
            "=" * 84,
        ]
    )

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 84)
    print("Step 26. Adjusted Clinical Validation")
    print("=" * 84)

    ensure_output_directory()

    print("Loading cluster labels, modeling dataset, and outcomes...")
    labels, modeling, outcomes = load_inputs()
    validate_core_inputs(labels, modeling, outcomes)

    print("Resolving adjustment covariates...")
    resolved = resolve_covariates(modeling)

    for concept, source in resolved.items():
        print(
            f"  {concept}: "
            f"{source if source is not None else 'NOT FOUND'}"
        )

    print("Building adjusted-validation analysis dataset...")
    analysis_raw = create_analysis_dataset(
        labels,
        modeling,
        outcomes,
        resolved,
    )

    missingness = create_missingness_table(
        analysis_raw,
        resolved,
    )

    analysis = clean_covariates(
        analysis_raw,
        resolved,
    )

    print(f"Analysis rows: {len(analysis):,}")
    print(
        f"RIWT cases: {int(analysis['riwt'].sum()):,} "
        f"({analysis['riwt'].mean() * 100:.2f}%)"
    )

    print("Fitting sequential adjusted logistic regression models...")
    all_coefficients, model_summary = run_all_models(
        analysis
    )

    riwt_effects = extract_riwt_effects(
        all_coefficients,
        model_summary,
    )

    vif = calculate_vif(analysis)

    print("Creating adjusted OR forest plot...")
    create_forest_plot(riwt_effects)

    report = build_report(
        analysis,
        resolved,
        missingness,
        riwt_effects,
        model_summary,
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
    all_coefficients.to_csv(
        OUTPUT_ALL_COEFFICIENTS,
        index=False,
    )
    missingness.to_csv(
        OUTPUT_MISSINGNESS,
        index=False,
    )

    if not vif.empty:
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
    print("Saved:")
    for path in [
        OUTPUT_ANALYSIS_DATASET,
        OUTPUT_MODEL_SUMMARY,
        OUTPUT_RIWT_EFFECTS,
        OUTPUT_ALL_COEFFICIENTS,
        OUTPUT_MISSINGNESS,
        OUTPUT_FOREST,
        OUTPUT_REPORT,
    ]:
        print(path)

    if not vif.empty:
        print(OUTPUT_VIF)

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
