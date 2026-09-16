-- Q1: Seats won and vote share by party, 2021 vs 2026, with the change.
-- Vote share = % of valid votes (NOTA lives in its own table, so it is excluded).

WITH votes AS (                      -- votes each party got, per year
    SELECT year, party, SUM(total_votes) AS party_votes
    FROM results
    GROUP BY year, party
),
totals AS (                          -- ALL votes cast, per year (one number per year)
    SELECT year, SUM(total_votes) AS year_votes
    FROM results
    GROUP BY year
),
seats AS (                           -- seats each party won, per year
    SELECT year, winner_party AS party, COUNT(*) AS seats
    FROM winners
    GROUP BY year, winner_party
),
combined AS (                        -- one row per party per year
    SELECT v.party,
           v.year,
           ROUND(v.party_votes * 100.0 / t.year_votes, 2) AS vote_pct,
           COALESCE(s.seats, 0)                            AS seats
    FROM votes v
    JOIN      totals t ON t.year  = v.year
    LEFT JOIN seats  s ON s.year  = v.year AND s.party = v.party
)
SELECT party,                        -- pivot the years into columns
       MAX(CASE WHEN year = 2021 THEN vote_pct END)        AS vote_pct_2021,
       MAX(CASE WHEN year = 2026 THEN vote_pct END)        AS vote_pct_2026,
       ROUND(COALESCE(MAX(CASE WHEN year = 2026 THEN vote_pct END), 0)
           - COALESCE(MAX(CASE WHEN year = 2021 THEN vote_pct END), 0), 2) AS vote_change,
       COALESCE(MAX(CASE WHEN year = 2021 THEN seats END), 0) AS seats_2021,
       COALESCE(MAX(CASE WHEN year = 2026 THEN seats END), 0) AS seats_2026
FROM combined
GROUP BY party
HAVING vote_pct_2021 >= 0.5 OR vote_pct_2026 >= 0.5
ORDER BY vote_pct_2026 DESC;
