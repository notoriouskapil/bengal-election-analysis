-- Q3: Which seats changed hands, and in which direction.
-- A self-join: the same table twice, once as 2021 and once as 2026.

SELECT a.winner_party AS won_2021,
       b.winner_party AS won_2026,
       COUNT(*)       AS seats,
       CASE WHEN a.winner_party = b.winner_party THEN 'held' ELSE 'flipped' END AS outcome
FROM winners a
JOIN winners b ON b.ac_no = a.ac_no      -- same seat...
               AND b.year = 2026          -- ...but the other election
WHERE a.year = 2021
GROUP BY a.winner_party, b.winner_party
ORDER BY seats DESC;
