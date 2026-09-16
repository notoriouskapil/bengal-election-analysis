-- Q4: The 20 narrowest wins in each year.
-- RANK() numbers the rows within each year separately.

WITH ranked AS (
    SELECT w.year, w.ac_no, c.ac_name, c.region,
           w.winner_party, w.runner_up_party,
           w.win_margin, w.margin_pct_polled,
           RANK() OVER (PARTITION BY w.year             -- restart numbering each year
                        ORDER BY w.margin_pct_polled)   -- smallest margin = rank 1
               AS closeness_rank
    FROM winners w
    JOIN constituencies c ON c.ac_no = w.ac_no
)
SELECT year, closeness_rank, ac_no, ac_name, region,
       winner_party, runner_up_party, win_margin, margin_pct_polled
FROM ranked
WHERE closeness_rank <= 20
ORDER BY year, closeness_rank;
