-- Q5: How far each region moved between the two elections.
-- Same pivot trick as Q1, but the grain is region instead of party.

WITH regional AS (               -- grain: region + year
    SELECT c.region, r.year,
           SUM(CASE WHEN r.party = 'TMC' THEN r.total_votes ELSE 0 END) AS tmc_votes,
           SUM(CASE WHEN r.party = 'BJP' THEN r.total_votes ELSE 0 END) AS bjp_votes,
           SUM(r.total_votes)                                           AS all_votes
    FROM results r
    JOIN constituencies c ON c.ac_no = r.ac_no
    GROUP BY c.region, r.year
),
shares AS (
    SELECT region, year,
           tmc_votes * 100.0 / all_votes AS tmc_pct,
           bjp_votes * 100.0 / all_votes AS bjp_pct
    FROM regional
)
SELECT region,
       ROUND(MAX(CASE WHEN year = 2021 THEN tmc_pct END), 1) AS tmc_2021,
       ROUND(MAX(CASE WHEN year = 2026 THEN tmc_pct END), 1) AS tmc_2026,
       ROUND(MAX(CASE WHEN year = 2026 THEN tmc_pct END)
           - MAX(CASE WHEN year = 2021 THEN tmc_pct END), 1) AS tmc_swing,
       ROUND(MAX(CASE WHEN year = 2026 THEN bjp_pct END)
           - MAX(CASE WHEN year = 2021 THEN bjp_pct END), 1) AS bjp_swing
FROM shares
GROUP BY region
ORDER BY tmc_swing;
