-- 5) What was TMC's vote share in each region in 2021 and in 2026, and how much did it change

with base as (
SELECT  c.region,r.*
FROM constituencies c
LEFT JOIN results r on r.ac_no=c.ac_no
)
, votes_region as (
SELECT SUM(total_votes) as total_region_votes
                , region 
				,year
FROM base 
GROUP BY  region ,year
)
, tmc_votes_region as(
SELECT sum(CASE WHEN party ='TMC' THEN total_votes END) as tmc_votes
               , region 
			   ,year	   
FROM base 
GROUP BY region,year
),
combined as (
SELECT r.*
                  , t.*
                 ,( tmc_votes*100.0/total_region_votes ) as vote_per_region 
FROM votes_region r 
JOIN tmc_votes_region t on t.region = r.region  AND  t.year = r.year
)
SELECT  region
                ,ROUND( MAX(CASE WHEN year =2021 THEN vote_per_region  END  ),2) as vote_pct_2021
				,ROUND(MAX(CASE WHEN year =2026 THEN vote_per_region   END) ,2)as vote_pct_2026
				,ROUND((MAX(CASE WHEN year =2026 THEN vote_per_region   END)-MAX(CASE WHEN year =2021 THEN vote_per_region   END) ),2) as pct_change
FROM  combined
GROUP BY region;