-- 05_trajectory.sql
-- Build unified trajectory dataset

DROP TABLE IF EXISTS mimiciv_derived.trajectory_first24h CASCADE;

CREATE TABLE mimiciv_derived.trajectory_first24h AS

SELECT
    subject_id,
    hadm_id,
    stay_id,
    charttime,
    itemid,
    label,
    valuenum,
    valueuom,
    'vital' AS source

FROM mimiciv_derived.vitals_first24h

UNION ALL

SELECT
    subject_id,
    hadm_id,
    stay_id,
    charttime,
    itemid,
    label,
    valuenum,
    valueuom,
    'lab' AS source

FROM mimiciv_derived.labs_first24h;

-- Verification

SELECT COUNT(*) AS n_rows
FROM mimiciv_derived.trajectory_first24h;

SELECT *
FROM mimiciv_derived.trajectory_first24h
ORDER BY stay_id, charttime
LIMIT 50;
