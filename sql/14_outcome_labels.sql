-- 14_outcome_labels.sql

/*
Create mortality outcome labels for each adult ICU stay.

Input:
    mimiciv_derived.cohort_icu_adult
    mimiciv_hosp.admissions

Output:
    mimiciv_derived.outcome_labels

Outcomes:
    mortality_1d = death within 1 day after ICU admission
    mortality_3d = death within 3 days after ICU admission
    mortality_7d = death within 7 days after ICU admission
*/

DROP TABLE IF EXISTS mimiciv_derived.outcome_labels;

CREATE TABLE mimiciv_derived.outcome_labels AS
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
    ON co.hadm_id = ad.hadm_id;

-- Validation 1: total ICU stays
SELECT COUNT(*) AS n_outcome_rows
FROM mimiciv_derived.outcome_labels;

-- Validation 2: mortality counts
SELECT
    SUM(mortality_1d) AS n_mortality_1d,
    SUM(mortality_3d) AS n_mortality_3d,
    SUM(mortality_7d) AS n_mortality_7d
FROM mimiciv_derived.outcome_labels;

-- Validation 3: mortality rates
SELECT
    ROUND(100.0 * SUM(mortality_1d) / COUNT(*), 2) AS mortality_1d_percent,
    ROUND(100.0 * SUM(mortality_3d) / COUNT(*), 2) AS mortality_3d_percent,
    ROUND(100.0 * SUM(mortality_7d) / COUNT(*), 2) AS mortality_7d_percent
FROM mimiciv_derived.outcome_labels;

-- Validation 4: sample rows
SELECT *
FROM mimiciv_derived.outcome_labels
ORDER BY stay_id
LIMIT 20;
