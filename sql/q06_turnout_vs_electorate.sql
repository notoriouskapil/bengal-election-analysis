-- Q6: Did turnout really rise, or did the electorate shrink?
-- Grain is the seat. Falta (144) excluded - it held no poll in 2026.

WITH by_seat AS (
    SELECT e.ac_no, c.region,
           MAX(CASE WHEN e.year = 2021 THEN e.total_electors END) AS electors_2021,
           MAX(CASE WHEN e.year = 2026 THEN e.total_electors END) AS electors_2026,
           MAX(CASE WHEN e.year = 2021 THEN e.turnout_pct    END) AS turnout_2021,
           MAX(CASE WHEN e.year = 2026 THEN e.turnout_pct    END) AS turnout_2026
    FROM electorate e
    JOIN constituencies c ON c.ac_no = e.ac_no
    WHERE e.ac_no <> 144
    GROUP BY e.ac_no, c.region
)
SELECT region,
       COUNT(*)                                                      AS seats,
       ROUND(AVG((electors_2026 - electors_2021) * 100.0 / electors_2021), 2)
                                                                     AS electorate_change_pct,
       ROUND(AVG(turnout_2026 - turnout_2021), 2)                    AS turnout_change_pts,
       SUM(CASE WHEN electors_2026 < electors_2021 THEN 1 ELSE 0 END) AS seats_where_roll_shrank
FROM by_seat
GROUP BY region
ORDER BY electorate_change_pct;
