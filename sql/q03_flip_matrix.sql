
-- 3) For every seat, which party won it in 2021 and which in 2026?

WITH by_seat AS (                     
    SELECT ac_no,
           MAX(CASE WHEN year = 2021 THEN winner_party END) AS won_2021,
           MAX(CASE WHEN year = 2026 THEN winner_party END) AS won_2026
    FROM winners
    GROUP BY ac_no
)
SELECT won_2021,
       won_2026,
       COUNT(*) AS seats,
       CASE WHEN won_2021 = won_2026 THEN 'held' ELSE 'flipped' END AS outcome
FROM by_seat
WHERE won_2026 IS NOT NULL             
GROUP BY won_2021, won_2026
ORDER BY seats DESC;