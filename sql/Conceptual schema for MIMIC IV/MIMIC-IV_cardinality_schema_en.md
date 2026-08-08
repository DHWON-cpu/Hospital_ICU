# MIMIC-IV cardinality concept schema (based on constraint.sql)

This document summarizes the entity-relationship structure implied by the
`PRIMARY KEY` / `FOREIGN KEY` statements in `constraint.sql`. The full
schema was split into six smaller, report-friendly figures (A-F) instead
of one large diagram, so each one prints cleanly on a portrait page.

**Notation** (crow's-foot): a bar (`—|`) marks the "one" side of a
relationship and a crow's foot (`〈`) marks the "many" side, i.e. every
edge below is a **1 : N** relationship read from the bar end to the
crow's-foot end.

**Color key used in every figure**
| Color | Meaning |
|---|---|
| Orange box | Hub entity (`patients`, `admissions`, `icustays`) |
| Blue box | Table with a `subject_id` FK to `patients` |
| Green box | Reference / lookup table (`d_hcpcs`, `d_labitems`, `d_items`) |
| Dashed gray box | PK-only table with **no FK link** in this script |
| Blue edge | Relationship sourced from `patients` |
| Orange edge | Relationship sourced from `admissions` |
| Teal edge | Relationship sourced from `icustays` |
| Green edge | Relationship sourced from a reference table |
| Gray edge | Parent → detail relationship (e.g. `emar` → `emar_detail`) |

---

## Figure A — Admission & transfer
`hosp_module` core chain: `patients` (1) → `admissions` (N), and both
`patients` and `admissions` (1) → `transfers` / `services` (N).
Note `transfers` only carries a `subject_id` FK in this script (no
`hadm_id` FK), so it is *not* tied to a specific admission here.

## Figure B — Diagnoses & procedures
`patients`/`admissions` (1) → `diagnoses_icd`, `procedures_icd`,
`drgcodes` (N). The dashed boxes `d_icd_diagnoses` and `d_icd_procedures`
are PK-only reference tables — the dashed line shows the conceptual link
via `icd_code`/`icd_version`, but **no FK constraint for it exists** in
this script.

## Figure C — Billing, labs & microbiology
`d_hcpcs` (1) → `hcpcsevents` (N) and `d_labitems` (1) → `labevents` (N)
are code-lookup relationships. `patients`/`admissions` also FK directly
into `hcpcsevents` and `microbiologyevents`; `labevents` only carries a
`subject_id` FK (no `hadm_id` FK in this script).

## Figure D — Medications & orders
`patients`/`admissions` (1) → `emar`, `pharmacy`, `prescriptions`,
`poe` (N). `emar` (1) → `emar_detail` (N) and `poe` (1) → `poe_detail`
(N) are header/detail relationships; both detail tables also carry a
direct `subject_id` FK to `patients`.

## Figure E — ICU stay
`icu_module` hub chain: `patients` (1) → `admissions` (1) →
`icustays` (N per admission via `hadm_id`, N per patient via
`subject_id`).

## Figure F — ICU events
`icustays` (1) and `d_items` (1) both → `chartevents`, `datetimeevents`,
`inputevents`, `outputevents`, `procedureevents` (N each). For
readability this figure omits the direct `patients`/`admissions` FKs
that every one of these five tables also carries in the script (same
1 : N pattern shown in Figure E) — see the summary table below.

---

## Full relationship summary

| Parent | Child | FK column(s) | Cardinality |
|---|---|---|---|
| patients | admissions | subject_id | 1 : N |
| patients | transfers | subject_id | 1 : N |
| patients | diagnoses_icd | subject_id | 1 : N |
| patients | procedures_icd | subject_id | 1 : N |
| patients | drgcodes | subject_id | 1 : N |
| patients | hcpcsevents | subject_id | 1 : N |
| patients | labevents | subject_id | 1 : N |
| patients | microbiologyevents | subject_id | 1 : N |
| patients | emar | subject_id | 1 : N |
| patients | emar_detail | subject_id | 1 : N |
| patients | pharmacy | subject_id | 1 : N |
| patients | prescriptions | subject_id | 1 : N |
| patients | poe | subject_id | 1 : N |
| patients | poe_detail | subject_id | 1 : N |
| patients | services | subject_id | 1 : N |
| patients | icustays | subject_id | 1 : N |
| patients | chartevents | subject_id | 1 : N |
| patients | datetimeevents | subject_id | 1 : N |
| patients | inputevents | subject_id | 1 : N |
| patients | outputevents | subject_id | 1 : N |
| patients | procedureevents | subject_id | 1 : N |
| admissions | diagnoses_icd | hadm_id | 1 : N |
| admissions | procedures_icd | hadm_id | 1 : N |
| admissions | drgcodes | hadm_id | 1 : N |
| admissions | hcpcsevents | hadm_id | 1 : N |
| admissions | microbiologyevents | hadm_id | 1 : N |
| admissions | emar | hadm_id | 1 : N |
| admissions | pharmacy | hadm_id | 1 : N |
| admissions | prescriptions | hadm_id | 1 : N |
| admissions | poe | hadm_id | 1 : N |
| admissions | services | hadm_id | 1 : N |
| admissions | icustays | hadm_id | 1 : N |
| admissions | chartevents | hadm_id | 1 : N |
| admissions | datetimeevents | hadm_id | 1 : N |
| admissions | inputevents | hadm_id | 1 : N |
| admissions | outputevents | hadm_id | 1 : N |
| admissions | procedureevents | hadm_id | 1 : N |
| icustays | chartevents | stay_id | 1 : N |
| icustays | datetimeevents | stay_id | 1 : N |
| icustays | inputevents | stay_id | 1 : N |
| icustays | outputevents | stay_id | 1 : N |
| icustays | procedureevents | stay_id | 1 : N |
| emar | emar_detail | emar_id | 1 : N |
| poe | poe_detail | poe_id | 1 : N |
| d_hcpcs | hcpcsevents | hcpcs_cd → code | 1 : N |
| d_labitems | labevents | itemid | 1 : N |
| d_items | chartevents | itemid | 1 : N |
| d_items | datetimeevents | itemid | 1 : N |
| d_items | inputevents | itemid | 1 : N |
| d_items | outputevents | itemid | 1 : N |
| d_items | procedureevents | itemid | 1 : N |

## Tables with no PK/FK declared in this script

- `drgcodes` — FKs only, no PK statement present
- `emar_detail` — PK statement exists but is commented out
- `chartevents` — FKs only, no PK statement present
- `d_icd_diagnoses`, `d_icd_procedures` — PK only, no incoming FK in
  this script (conceptually referenced by `diagnoses_icd` /
  `procedures_icd` via `icd_code`/`icd_version`, but not enforced here)
