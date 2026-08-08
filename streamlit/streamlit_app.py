"""
streamlit_app.py — ICU Trajectory Watch
====================================================================
Where the patient is heading, from the first 24 hours of labs.

PAGE STRUCTURE
--------------
  title
  top tab bar   0-5   the pre-rendered project slides
                Summary — this patient   the live verdict, drift and timeline,
                                         as its own independent tab
  ------------
  1 · Admission     entered once, then left alone
  2 · New lab draw  the repeated action

The modelling forms flow down the page; the Summary is NOT wedged between them.
Entering a draw and reading the consequence are two different jobs, often two
different people, so the verdict sits in the tab bar where it can be opened at
any time without touching the inputs.

WHY ADMISSION IS SEPARATE FROM THE DRAW
---------------------------------------
The first lab panel already exists in the EHR. It is registered once, by whoever
admits the patient, and then nobody retypes it — it is held in session state and
becomes the baseline every later draw is measured against. Each new draw is one
panel: lactate, creatinine, WBC, platelets, and the hour it came back.

PRINCIPLE
---------
Read only what already exists: the slide PNGs and the fitted coefficients in
26_all_model_coefficients.csv. Nothing is refitted at serve time; the only
arithmetic is a nearest-centroid comparison and one logistic transform. If the
coefficient file is missing the app stops with an error — a plausible-looking
fake risk number is worse than no number.

Layout on disk:
    streamlit/
    ├── 26_all_model_coefficients.csv   <- fitted Step 26 V2 coefficients (required)
    ├── .streamlit/config.toml          <- dark theme
    ├── slide/0_Summary.png ... 5_Reporting_Deployment.png
    └── streamlit_app.py                <- this file

Run:
    pip install streamlit pandas numpy matplotlib
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SLIDE_DIR = os.path.join(BASE_DIR, "slide")
COEF_PATH = os.path.join(BASE_DIR, "26_all_model_coefficients.csv")

st.set_page_config(page_title="ICU Trajectory Watch", layout="wide")

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
BG_COLOR = "#000000"
PANEL_COLOR = "#111111"
TEXT_COLOR = "#FFFFFF"
MUTED_TEXT_COLOR = "#B3B3B3"
FONT_FAMILY = "'Inter', sans-serif"

RBT_COLOR = "#2a78d6"
RIWT_COLOR = "#e34948"

MODEL_LABEL = "Model 4: + baseline biomarkers"
OUTCOMES = ["mortality_1d", "mortality_3d", "mortality_7d"]
OUTCOME_LABELS = {
    "mortality_1d": "1-day mortality",
    "mortality_3d": "3-day mortality",
    "mortality_7d": "7-day mortality",
}

# RBT / RIWT centroid signatures from Step 23/25
CENTROIDS = {
    "RBT": {"lactate_clearance_pct": 25.00, "creatinine_pct_change": 0.00,
            "wbc_pct_change": -10.74, "platelet_pct_change": -8.58},
    "RIWT": {"lactate_clearance_pct": 0.00, "creatinine_pct_change": 13.33,
             "wbc_pct_change": 50.00, "platelet_pct_change": 18.38},
}
PHENOTYPE_FULL = {
    "RBT": "Recovery-like Biochemical Trajectory",
    "RIWT": "Renal-inflammatory Worsening Trajectory",
}

SLIDES = [
    ("0 · Summary", "0_Summary.png",
     "The whole project on one page: business need, data engineering, "
     "statistics/ML, and the resulting decision aid."),
    ("1 · Business question", "1_Business_Question.png",
     "An ICU records vitals and labs. Only the labs carry biochemistry — and a "
     "single lab value carries no direction."),
    ("2 · Data build", "2_Data_Build.png",
     "MIMIC-IV v3.1 in Docker/PostgreSQL → 74,829 adult ICU stays → an 8-variable "
     "trajectory table, every row count validated."),
    ("3 · Evaluation & phenotyping", "3_Evaluation_Phenotyping.png",
     "Winsorize, impute, robust-scale, then K-means k = 2–6. Two clusters win on "
     "every internal metric: RBT 76.3% vs. RIWT 23.7%."),
    ("4 · Outcome validation", "4_Outcome_Validation.png",
     "RIWT carries higher mortality at 1, 3 and 7 days, and the signal survives "
     "adjustment and a complete-case re-run."),
    ("5 · Reporting & deployment", "5_Reporting_Deployment.png",
     "What is still open, and how the phenotype reaches the bedside — this app."),
]
SUMMARY_TAB_LABEL = "Summary — this patient"

LAB_SPECS = [                      # key, label, min, max, default, step
    ("lactate", "Lactate (mmol/L)", 0.3, 15.0, 2.0, 0.1),
    ("creatinine", "Creatinine (mg/dL)", 0.2, 8.0, 1.0, 0.1),
    ("wbc", "WBC (10⁹/L)", 0.5, 40.0, 10.0, 0.1),
    ("platelet", "Platelet (10⁹/L)", 10.0, 600.0, 220.0, 5.0),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def banner(text: str, size: str = "26px", pad: str = "8px 16px"):
    st.markdown(
        f"<div style='background:{PANEL_COLOR};color:{TEXT_COLOR};padding:{pad};"
        f"font-family:{FONT_FAMILY};font-weight:700;font-size:{size};"
        f"display:inline-block;margin:6px 0;'>{text}</div>",
        unsafe_allow_html=True,
    )


def role_note(text: str):
    st.markdown(
        f"<div style='color:{MUTED_TEXT_COLOR};font-family:{FONT_FAMILY};"
        f"font-size:13px;margin:2px 0 10px 0;'>{text}</div>",
        unsafe_allow_html=True,
    )


def show_saved_image(path: str):
    if os.path.exists(path):
        st.image(path, use_container_width=True)
    else:
        st.warning(f"Missing slide: slide/{os.path.basename(path)} — export it from "
                   "BI_ICU_Pipeline_Flow.pptx into the slide/ folder.")


@st.cache_data
def load_model4_coefficients(path: str) -> dict[str, dict[str, float]]:
    """Fitted Model 4 coefficients per outcome, keyed exactly as the CSV spells the
    terms. The ICU-type dummies use full unit names, so the input widget is built
    FROM these keys rather than guessed — guessing silently drops ICU type."""
    df = pd.read_csv(path)
    missing = {"model", "outcome", "term", "coefficient"} - set(df.columns)
    if missing:
        raise ValueError(f"missing required columns {sorted(missing)}")
    model4 = df[df["model"] == MODEL_LABEL]
    if model4.empty:
        raise ValueError(f"no rows for '{MODEL_LABEL}' "
                         f"(models present: {sorted(df['model'].unique())})")
    coefs: dict[str, dict[str, float]] = {}
    for outcome in OUTCOMES:
        sub = model4[model4["outcome"] == outcome]
        if sub.empty:
            raise ValueError(f"no '{outcome}' rows for {MODEL_LABEL}")
        coefs[outcome] = dict(zip(sub["term"], sub["coefficient"].astype(float)))
    return coefs


def icu_options(coefs: dict[str, dict[str, float]]) -> list[str]:
    terms: set[str] = set()
    for row in coefs.values():
        terms |= {t for t in row if t.startswith("icu_type_")}
    return sorted(t[len("icu_type_"):] for t in terms)


def predict_probability(coefs_row: dict[str, float], values: dict[str, float]) -> float:
    logit = coefs_row.get("const", 0.0)
    for term, coef in coefs_row.items():
        if term != "const" and term in values:
            logit += coef * values[term]
    return float(1 / (1 + np.exp(-logit)))


def trajectory_signature(first: dict[str, float], follow: dict[str, float]) -> dict[str, float]:
    """Direction, not level. Lactate is expressed as clearance (positive = falling);
    the other three as percent change (positive = rising)."""
    return {
        "lactate_clearance_pct": (first["lactate"] - follow["lactate"]) / first["lactate"] * 100,
        "creatinine_pct_change": (follow["creatinine"] - first["creatinine"]) / first["creatinine"] * 100,
        "wbc_pct_change": (follow["wbc"] - first["wbc"]) / first["wbc"] * 100,
        "platelet_pct_change": (follow["platelet"] - first["platelet"]) / first["platelet"] * 100,
    }


def classify_phenotype(signature: dict[str, float]) -> tuple[str, float, float]:
    def dist(centroid):
        return sum((signature[k] - centroid[k]) ** 2 for k in centroid) ** 0.5

    d_rbt, d_riwt = dist(CENTROIDS["RBT"]), dist(CENTROIDS["RIWT"])
    return ("RIWT" if d_riwt < d_rbt else "RBT"), d_rbt, d_riwt


def score_draw(coefs, admission, follow) -> dict:
    """One follow-up panel -> phenotype + the three mortality probabilities."""
    signature = trajectory_signature(admission["labs"], follow["labs"])
    label, d_rbt, d_riwt = classify_phenotype(signature)
    values: dict[str, float] = {
        "riwt": 1 if label == "RIWT" else 0,
        "age": admission["age"],
        "sex_M": 1 if admission["sex"] == "M" else 0,
        "lactate_first": admission["labs"]["lactate"],
        "creatinine_first": admission["labs"]["creatinine"],
        "wbc_first": admission["labs"]["wbc"],
        "platelet_first": admission["labs"]["platelet"],
    }
    for unit in icu_options(coefs):
        values[f"icu_type_{unit}"] = 1 if admission["icu_type"] == unit else 0
    risks = {o: predict_probability(coefs[o], values) * 100 for o in OUTCOMES}
    # Model 4's only trajectory input is the binary riwt flag, so the risk numbers
    # are flat inside a phenotype and jump when it flips. The signed centroid
    # margin is the continuous quantity that moves with every draw: positive means
    # the patient now sits closer to RIWT, and crossing zero IS the flip.
    return dict(signature=signature, label=label, d_rbt=d_rbt, d_riwt=d_riwt,
                margin=d_rbt - d_riwt, risks=risks)


def render_patient_summary(coefs, adm, draws):
    """The Summary tab: read-only verdict for whatever has been entered so far."""
    if adm is None:
        st.info("Register an admission panel below to start watching this patient.")
        return
    if not draws:
        st.info("No follow-up draw yet. Add one below — a single admission panel has "
                "no direction to report.")
        return

    scored = [score_draw(coefs, adm, d) for d in draws]
    latest, latest_draw = scored[-1], draws[-1]
    previous = scored[-2] if len(scored) > 1 else None

    st.markdown(
        f"<div style='font-family:{FONT_FAMILY};color:{MUTED_TEXT_COLOR};"
        f"font-size:15px;margin-bottom:6px;'><b style='color:{TEXT_COLOR};'>"
        f"{adm['patient_code']}</b> · {adm['age']} y · {adm['sex']} · "
        f"{adm['icu_type']} · {len(scored)} draw(s)</div>",
        unsafe_allow_html=True,
    )

    label = latest["label"]
    verdict_color = RBT_COLOR if label == "RBT" else RIWT_COLOR
    st.markdown(
        f"<div style='font-family:{FONT_FAMILY};margin:10px 0 4px 0;'>"
        f"<span style='font-size:72px;font-weight:800;color:{verdict_color};"
        f"line-height:1.05;'>{label}</span>"
        f"<span style='font-size:24px;color:{TEXT_COLOR};margin-left:16px;'>"
        f"{PHENOTYPE_FULL[label]}</span></div>"
        f"<div style='font-family:{FONT_FAMILY};font-size:17px;"
        f"color:{MUTED_TEXT_COLOR};margin-bottom:14px;'>Hour "
        f"{latest_draw['hours']} of admission · distance to RBT centroid "
        f"<b style='color:{TEXT_COLOR};'>{latest['d_rbt']:.1f}</b> · to RIWT "
        f"centroid <b style='color:{TEXT_COLOR};'>{latest['d_riwt']:.1f}</b> "
        "(nearest-centroid match against the Step 23/25 signatures)</div>",
        unsafe_allow_html=True,
    )

    if previous is not None and previous["label"] != label:
        direction = "worsening" if label == "RIWT" else "improving"
        st.warning(f"**Phenotype flipped** at hour {latest_draw['hours']}: "
                   f"{previous['label']} → {label}. The patient is {direction} "
                   "relative to the previous draw.")

    mcols = st.columns(4)
    for col, outcome in zip(mcols, OUTCOMES):
        value = latest["risks"][outcome]
        delta = None if previous is None else value - previous["risks"][outcome]
        with col:
            st.metric(
                OUTCOME_LABELS[outcome], f"{value:.1f}%",
                None if delta is None else f"{delta:+.1f} pp vs. previous draw",
                delta_color="inverse",
            )
    with mcols[3]:
        drift = latest["margin"]
        st.metric(
            "Drift toward RIWT", f"{drift:+.1f}",
            None if previous is None
            else f"{drift - previous['margin']:+.1f} vs. previous draw",
            delta_color="inverse",
            help="Distance to the RBT centroid minus distance to the RIWT centroid. "
                 "Negative = still recovery-like; crossing zero is the phenotype flip.",
        )

    st.caption(
        "The three mortality figures are driven by the phenotype flag, so they hold "
        "steady inside a phenotype and step when it flips — that is a property of the "
        "fitted model, not a stalled reading. **Drift toward RIWT** is the number that "
        "moves with every draw, and it is what gives you warning before the flip."
    )

    # Drift across draws — the one line that moves every time, with the zero
    # crossing marked because that is where the phenotype (and risk) flips.
    fig, ax = plt.subplots(figsize=(9, 2.8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    hours_axis = [d["hours"] for d in draws]
    margins = [s["margin"] for s in scored]
    ax.axhline(0, color=MUTED_TEXT_COLOR, linewidth=1, linestyle="--")
    ax.plot(hours_axis, margins, "-", color=MUTED_TEXT_COLOR, linewidth=1.5, zorder=2)
    for hour, margin, entry in zip(hours_axis, margins, scored):
        ax.scatter([hour], [margin], s=70, zorder=3,
                   color=RIWT_COLOR if entry["label"] == "RIWT" else RBT_COLOR)
        ax.annotate(f"{margin:+.0f}", (hour, margin), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=9,
                    color=TEXT_COLOR)
    span = max(abs(min(margins + [0])), abs(max(margins + [0])), 5) * 1.45
    ax.set_ylim(-span, span)
    ax.set_xlabel("Hour since admission", color=TEXT_COLOR)
    ax.set_ylabel("Drift toward RIWT", color=TEXT_COLOR)
    ax.text(0.005, 0.93, "closer to RIWT", transform=ax.transAxes,
            fontsize=9, color=RIWT_COLOR)
    ax.text(0.005, 0.04, "closer to RBT", transform=ax.transAxes,
            fontsize=9, color=RBT_COLOR)
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax.spines[spine].set_color(MUTED_TEXT_COLOR)
    fig.tight_layout()
    st.pyplot(fig)
    if len(scored) == 1:
        st.caption("Add the next draw to see whether the patient is drifting toward "
                   "the flip line or away from it.")

    selected_term = f"icu_type_{adm['icu_type']}"
    extreme = [o for o in OUTCOMES
               if selected_term in coefs[o] and abs(coefs[o][selected_term]) > 5]
    if extreme:
        st.warning(
            f"**{adm['icu_type']}** is a near-separated category in the fitted model "
            f"(|coefficient| > 5 for {', '.join(OUTCOME_LABELS[o] for o in extreme)}). "
            "Read its estimate as 'too few events to estimate', not as a real "
            "probability."
        )

    st.caption(
        "Read this as a screening aid, not a decision. The estimate is a model output "
        "from one historical cohort (MIMIC-IV, n = 24,799); patients near a decision "
        "threshold belong with a clinician, not a calculator."
    )

    st.markdown("---")
    banner("Draw timeline", size="24px")
    timeline = pd.DataFrame([
        {
            "Hour": d["hours"],
            "Lactate": d["labs"]["lactate"],
            "Creatinine": d["labs"]["creatinine"],
            "WBC": d["labs"]["wbc"],
            "Platelet": d["labs"]["platelet"],
            "Lactate clearance (%)": round(s["signature"]["lactate_clearance_pct"], 1),
            "Creatinine Δ (%)": round(s["signature"]["creatinine_pct_change"], 1),
            "WBC Δ (%)": round(s["signature"]["wbc_pct_change"], 1),
            "Platelet Δ (%)": round(s["signature"]["platelet_pct_change"], 1),
            "Phenotype": s["label"],
            "Drift": round(s["margin"], 1),
            "1-day (%)": round(s["risks"]["mortality_1d"], 1),
            "3-day (%)": round(s["risks"]["mortality_3d"], 1),
            "7-day (%)": round(s["risks"]["mortality_7d"], 1),
        }
        for d, s in zip(draws, scored)
    ])
    st.dataframe(timeline, hide_index=True, use_container_width=True)
    st.caption("Every change column is measured against the admission panel, not "
               "against the previous draw — the phenotype is defined over the "
               "first-24-hour window.")
    st.download_button(
        "Download this patient's timeline (CSV)",
        data=timeline.to_csv(index=False).encode("utf-8"),
        file_name=f"trajectory_{adm['patient_code']}.csv", mime="text/csv")


# ===========================================================================
# Title
# ===========================================================================
st.markdown(
    f"<h1 style='color:{TEXT_COLOR};font-family:{FONT_FAMILY};margin-bottom:2px;'>"
    "ICU Trajectory Watch</h1>"
    f"<div style='color:{MUTED_TEXT_COLOR};font-family:{FONT_FAMILY};font-size:18px;"
    "margin-bottom:18px;'>Where the patient is heading, from the first 24 hours "
    "of labs</div>",
    unsafe_allow_html=True,
)

# ===========================================================================
# Fitted coefficients — required, no fallback. Loaded before the tabs so the
# Summary tab can render from whatever is already in session state.
# ===========================================================================
try:
    coefs = load_model4_coefficients(COEF_PATH)
except FileNotFoundError:
    st.error(
        "**26_all_model_coefficients.csv not found.** Place the Step 26 V2 "
        f"coefficient file next to streamlit_app.py (expected at `{COEF_PATH}`). "
        "The risk calculator cannot run without the fitted model."
    )
    st.stop()
except Exception as exc:                       # noqa: BLE001 — surfaced to the user
    st.error(f"**Could not read 26_all_model_coefficients.csv** — {exc}")
    st.stop()

units = icu_options(coefs)

if "admission" not in st.session_state:
    st.session_state.admission = None
if "draws" not in st.session_state:
    st.session_state.draws = []

# ===========================================================================
# Top tab bar — the six project slides plus the patient Summary as its own tab
# ===========================================================================
tabs = st.tabs([label for label, _, _ in SLIDES] + [SUMMARY_TAB_LABEL])
for tab, (_, filename, caption) in zip(tabs, SLIDES):
    with tab:
        show_saved_image(os.path.join(SLIDE_DIR, filename))
        st.caption(caption)
with tabs[-1]:
    render_patient_summary(coefs, st.session_state.admission, st.session_state.draws)

st.markdown("---")

# ===========================================================================
# 1 · Admission — entered ONCE, then left alone
# ===========================================================================
banner("1 · Admission", size="24px")
role_note("Filled once, by whoever admits the patient — or exported from the EHR. "
          "The first lab panel becomes the baseline every later draw is measured "
          "against, so it is registered here and never retyped below.")

adm = st.session_state.admission

if adm is None:
    with st.form("admission_form"):
        c1, c2, c3 = st.columns([1.1, 1, 1.4])
        with c1:
            patient_code = st.text_input("Patient code", value="")
            age = st.slider("Age", 18, 110, 65)
            sex = st.radio("Sex", ["M", "F"], horizontal=True)
        with c2:
            icu_type = st.selectbox(
                "ICU type", ["Not selected (reference)"] + units,
                help="Categories come from the fitted model's own term names.",
            )
        with c3:
            st.markdown(f"<div style='color:{TEXT_COLOR};font-family:{FONT_FAMILY};"
                        "font-weight:600;margin-bottom:6px;'>Admission labs "
                        "(first measurement)</div>", unsafe_allow_html=True)
            first_labs = {
                key: st.number_input(label, min_value=lo, max_value=hi,
                                     value=default, step=step, key=f"adm_{key}")
                for key, label, lo, hi, default, step in LAB_SPECS
            }
        if st.form_submit_button("Register admission", type="primary"):
            st.session_state.admission = dict(
                patient_code=patient_code or "(unlabelled)", age=age, sex=sex,
                icu_type=icu_type, labs=first_labs,
                registered_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            st.session_state.draws = []
            st.rerun()
    st.info("Register the admission panel to start watching this patient.")
    st.stop()

a1, a2 = st.columns([3, 1])
with a1:
    st.markdown(
        f"<div style='font-family:{FONT_FAMILY};color:{TEXT_COLOR};font-size:16px;'>"
        f"<b>{adm['patient_code']}</b> · {adm['age']} y · {adm['sex']} · "
        f"{adm['icu_type']}<br>"
        f"<span style='color:{MUTED_TEXT_COLOR};font-size:14px;'>Baseline labs — "
        f"lactate {adm['labs']['lactate']} · creatinine {adm['labs']['creatinine']} · "
        f"WBC {adm['labs']['wbc']} · platelet {adm['labs']['platelet']} "
        f"(registered {adm['registered_at']})</span></div>",
        unsafe_allow_html=True,
    )
with a2:
    if st.button("New patient / reset"):
        st.session_state.admission = None
        st.session_state.draws = []
        st.rerun()

st.markdown("")

# ===========================================================================
# 2 · New lab draw — the repeated action
# ===========================================================================
banner("2 · New lab draw", size="24px")
role_note("The only form the bedside nurse touches. Enter the panel that just came "
          "back; the verdict updates in the **Summary** tab above.")

with st.form("draw_form"):
    d0, *dcols = st.columns([0.8, 1, 1, 1, 1])
    with d0:
        hours = st.number_input("Hour since admission", min_value=1, max_value=24,
                                value=min(24, 6 + 6 * len(st.session_state.draws)),
                                step=1)
    follow_labs = {}
    for col, (key, label, lo, hi, default, step) in zip(dcols, LAB_SPECS):
        with col:
            follow_labs[key] = st.number_input(label, min_value=lo, max_value=hi,
                                               value=float(adm["labs"][key]), step=step,
                                               key=f"draw_{key}")
    if st.form_submit_button("Add draw", type="primary"):
        st.session_state.draws.append(dict(hours=int(hours), labs=follow_labs))
        st.session_state.draws.sort(key=lambda d: d["hours"])
        st.rerun()

if st.session_state.draws:
    latest_hour = st.session_state.draws[-1]["hours"]
    st.success(f"{len(st.session_state.draws)} draw(s) recorded, latest at hour "
               f"{latest_hour} — open the **{SUMMARY_TAB_LABEL}** tab above for the "
               "verdict, the drift and the timeline.")
else:
    st.info("No follow-up draw yet. Add the first one to see which way this patient "
            "is moving.")

st.markdown("---")

# ===========================================================================
# References
# ===========================================================================
banner("References", size="24px")
st.markdown(
    """
- **Phenotype signatures** — Step 23 / 25: RBT and RIWT trajectory signatures and
  unadjusted mortality rates (`23B_pure_trajectory_signature.csv`,
  `25_trajectory_phenotype_framework.csv`)
- **Adjusted effects** — Step 26 V2: fully adjusted Model 4 logistic regression
  (`26_all_model_coefficients.csv`, `26_riwt_adjusted_effects.csv`)
- **Cohort** — MIMIC-IV v3.1, `mimiciv_derived.cohort_icu_adult`; 74,829 adult ICU
  stays screened, n = 24,799 in the Step 26 analysis cohort
- **Reported effect** — 7-day RR 1.37 (1.26–1.49) unadjusted; 7-day OR 2.14 fully
  adjusted
"""
)

with st.expander(f"Active coefficients — {MODEL_LABEL}"):
    st.json(coefs)
