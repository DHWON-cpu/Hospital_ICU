-- 02_cohort.sql

/*
Build the baseline ICU cohort for the project.
Select adult patients (age ≥ 18 years) with an ICU length 
of stay of at least 24 hours by joining ICU stay records with patient
demographic information. 
*/

DROP TABLE IF EXISTS mimiciv_derived.cohort_icu_adult;

CREATE TABLE mimiciv_derived.cohort_icu_adult AS
SELECT
    ie.subject_id,
    ie.hadm_id,
    ie.stay_id,
    ie.first_careunit,
    ie.last_careunit,
    ie.intime,
    ie.outtime,
    ie.los,
    p.gender,
    p.anchor_age
FROM mimiciv_icu.icustays AS ie
JOIN mimiciv_hosp.patients AS p
    ON ie.subject_id = p.subject_id
WHERE
    p.anchor_age >= 18
    AND ie.los >= 1.0;


/*
NOTICE:  table "cohort_icu_adult" does not exist, skipping
DROP TABLE
SELECT 74829
*/
