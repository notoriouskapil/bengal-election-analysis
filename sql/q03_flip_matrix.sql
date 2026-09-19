-- 3) Each 2026 winners 2021 position
WITH winners_2026 AS (
SELECT ac_no  
                , UPPER(TRIM(candidate)) as candidate
				,position
FROM results 
WHERE position = 1 AND year = 2026
)
, position_2021 AS (
SELECT ac_no 
               ,UPPER(TRIM(candidate)) as candidate
			   , position as position_2021 
FROM results 
WHERE year = 2021
)
SELECT w.ac_no,
                 w.candidate 
				 ,w.position as winner_2026
				 ,coalesce(p. position_2021,0) as position_2021
FROM winners_2026 w 
LEFT JOIN  position_2021 p on w.candidate = p.candidate;
