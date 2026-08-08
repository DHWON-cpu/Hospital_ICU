-- 08_variable_distribution.sql

SELECT
    label,
    source,
    valueuom,
    COUNT(*) AS n_measurements,

    ROUND(MIN(valuenum)::numeric, 2) AS min_value,

    ROUND(
        PERCENTILE_CONT(0.25)
        WITHIN GROUP (ORDER BY valuenum)::numeric,
        2
    ) AS q1,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (ORDER BY valuenum)::numeric,
        2
    ) AS median,

    ROUND(AVG(valuenum)::numeric, 2) AS mean_value,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (ORDER BY valuenum)::numeric,
        2
    ) AS q3,

    ROUND(MAX(valuenum)::numeric, 2) AS max_value,

    ROUND(STDDEV(valuenum)::numeric, 2) AS std_dev

FROM mimiciv_derived.trajectory_first24h
WHERE valuenum IS NOT NULL
GROUP BY
    label,
    source,
    valueuom
ORDER BY
    source,
    label,
    valueuom;