-- 1_validation.sql

-- Check ICU Stay Count 
-- icusatys = 94,458
SELECT COUNT(*) AS n_icustays
FROM mimiciv_icu.icustays;


-- Check Patient Count
-- Patients in hospital = 367,627
SELECT COUNT(*) AS n_patients
FROM mimiciv_hosp.patients;


-- unique icu patient = 65,366 
SELECT COUNT(DISTINCT subject_id) AS n_unique_icu_patients
FROM mimiciv_icu.icustays;

-- hospital admissions = 546,028
SELECT COUNT(*) AS n_hospital_admissions
FROM mimiciv_hosp.admissions;




