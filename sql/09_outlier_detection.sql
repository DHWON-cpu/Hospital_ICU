-- 09_outlier_detection.sql
-- IQR-based outlier detection summary by clinical variable

WITH distribution AS (
    SELECT
        label,
        source,
        valueuom,
        COUNT(*) AS n_measurements,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY valuenum) AS q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY valuenum) AS q3
    FROM mimiciv_derived.trajectory_first24h
    WHERE valuenum IS NOT NULL
    GROUP BY label, source, valueuom
),

bounds AS (
    SELECT
        label,
        source,
        valueuom,
        n_measurements,
        q1,
        q3,
        (q3 - q1) AS iqr,
        (q1 - 1.5 * (q3 - q1)) AS lower_bound,
        (q3 + 1.5 * (q3 - q1)) AS upper_bound
    FROM distribution
),

outlier_summary AS (
    SELECT
        t.label,
        t.source,
        t.valueuom,
        b.n_measurements,
        b.q1,
        b.q3,
        b.iqr,
        b.lower_bound,
        b.upper_bound,
        COUNT(*) FILTER (
            WHERE t.valuenum < b.lower_bound
               OR t.valuenum > b.upper_bound
        ) AS n_outliers
    FROM mimiciv_derived.trajectory_first24h AS t
    JOIN bounds AS b
      ON t.label = b.label
     AND t.source = b.source
     AND COALESCE(t.valueuom, '') = COALESCE(b.valueuom, '')
    WHERE t.valuenum IS NOT NULL
    GROUP BY
        t.label,
        t.source,
        t.valueuom,
        b.n_measurements,
        b.q1,
        b.q3,
        b.iqr,
        b.lower_bound,
        b.upper_bound
)

SELECT
    label,
    source,
    valueuom,
    n_measurements,
    ROUND(q1::numeric, 2) AS q1,
    ROUND(q3::numeric, 2) AS q3,
    ROUND(iqr::numeric, 2) AS iqr,
    ROUND(lower_bound::numeric, 2) AS lower_bound,
    ROUND(upper_bound::numeric, 2) AS upper_bound,
    n_outliers,
    ROUND((n_outliers::numeric / n_measurements) * 100, 2) AS outlier_percent
FROM outlier_summary
WHERE n_measurements >= 100 -- 측정값이 4개, 5개, 8개뿐인 변수는 outlier percent가 과장되므로 제외
ORDER BY outlier_percent DESC, n_outliers DESC;
