
-- 04_labs.sql
-- Extract laboratory measurements during the first 24 hours of ICU stay
-- Make a table: labs_first24h 

DROP TABLE IF EXISTS mimiciv_derived.labs_first24h CASCADE;

CREATE TABLE mimiciv_derived.labs_first24h AS

SELECT
    le.subject_id,
    le.hadm_id,
    co.stay_id,
    le.charttime,
    le.itemid,
    dl.label,
    le.valuenum,
    le.valueuom

FROM mimiciv_hosp.labevents le

JOIN mimiciv_hosp.d_labitems dl
    ON le.itemid = dl.itemid

JOIN mimiciv_derived.cohort_icu_adult co
    ON le.hadm_id = co.hadm_id

WHERE
    le.charttime >= co.intime
AND le.charttime < co.intime + INTERVAL '24 hours'
AND le.valuenum IS NOT NULL;

-- Verification

SELECT COUNT(*) AS n_labs_first24h
FROM mimiciv_derived.labs_first24h;

SELECT
    label,
    COUNT(*) AS n
FROM mimiciv_derived.labs_first24h
GROUP BY label
ORDER BY n DESC
LIMIT 30;
