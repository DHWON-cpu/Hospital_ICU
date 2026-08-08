-- # 03_vitals.sql
/*
03_vitals.sql extracts core ICU vital signs recorded during the first 24 hours of ICU admission. 
The script filters numeric chartevents by predefined MIMIC-IV item IDs for heart rate, 
respiratory rate, oxygen saturation, temperature, and blood pressure measurements.
*/
-- 03_vitals.sql
-- Extract core vital signs during the first 24 hours of ICU stay

DROP TABLE IF EXISTS mimiciv_derived.vitals_first24h CASCADE;

CREATE TABLE mimiciv_derived.vitals_first24h AS
SELECT
    ce.subject_id,
    ce.hadm_id,
    ce.stay_id,
    ce.charttime,
    ce.itemid,
    di.label,
    ce.valuenum,
    ce.valueuom
FROM mimiciv_icu.chartevents ce
JOIN mimiciv_icu.d_items di
    ON ce.itemid = di.itemid
JOIN mimiciv_derived.cohort_icu_adult co
    ON ce.stay_id = co.stay_id
WHERE ce.charttime >= co.intime
  AND ce.charttime < co.intime + INTERVAL '24 hours'
  AND ce.valuenum IS NOT NULL
  AND ce.itemid IN (
      220045, -- Heart Rate
      220210, -- Respiratory Rate
      220277, -- O2 saturation pulseoxymetry / SpO2
      223761, -- Temperature Fahrenheit
      223762, -- Temperature Celsius
      220179, -- Non-invasive BP systolic
      220180, -- Non-invasive BP diastolic
      220181, -- Non-invasive BP mean
      220050, -- Arterial BP systolic
      220051, -- Arterial BP diastolic
      220052  -- Arterial BP mean
  );

-- Verification 1: total rows
SELECT COUNT(*) AS n_vitals_first24h
FROM mimiciv_derived.vitals_first24h;

-- Verification 2: check included vital sign labels
SELECT itemid, label, COUNT(*) AS n
FROM mimiciv_derived.vitals_first24h
GROUP BY itemid, label
ORDER BY n DESC;

