-- Q2: Vote share vs seat share, 2026. The amplification gap.
-- Shows how first-past-the-post converts votes into seats disproportionately.

WITH party_votes AS (            -- grain: party
    SELECT party, SUM(total_votes) AS votes
    FROM results WHERE year = 2026
    GROUP BY party
),
all_votes AS (                   -- grain: the whole year (ONE number)
    SELECT SUM(total_votes) AS total FROM results WHERE year = 2026
),
party_seats AS (                 -- grain: party
    SELECT winner_party AS party, COUNT(*) AS seats
    FROM winners WHERE year = 2026
    GROUP BY winner_party
)
SELECT v.party,
       ROUND(v.votes * 100.0 / a.total, 1)        AS vote_share_pct,
       COALESCE(s.seats, 0)                       AS seats,
       ROUND(COALESCE(s.seats,0) * 100.0 / 293, 1) AS seat_share_pct,   -- 293: Falta had no poll
       ROUND(COALESCE(s.seats,0) * 100.0 / 293
           - v.votes * 100.0 / a.total, 1)        AS amplification
FROM party_votes v
CROSS JOIN all_votes a                            -- one row, attach to every party
LEFT JOIN party_seats s ON s.party = v.party
WHERE v.votes * 100.0 / a.total >= 0.5
ORDER BY vote_share_pct DESC;
