
-- 1)

with seats as(
SELECT  winner_party as party
                , year 
				, count(*) as seats
FROM winners 
GROUP BY 1,2
),
votes_party as (
SELECT sum( total_votes ) as votes_per_party
                 , party 
				 ,year 
FROM results
GROUP BY 2,3
)
,  total_votes as (
SELECT  sum(total_votes) as votes_year
                , year
FROM results
GROUP BY year
),
 combined as (
SELECT  v.votes_per_party
                , v.year 
				,v.party
				,ROUND(v.votes_per_party*100.0/t. votes_year,2) as vote_pct 
				,coalesce(s.seats,0) as seats
FROM votes_party v 
JOIN total_votes t ON t.year = v.year 
LEFT JOIN seats s ON s.party = v.party and s.year = v.year 
)
SELECT  party
                , MAX(CASE WHEN year = 2021 THEN vote_pct END) as vote_pct_2021
				, MAX(CASE WHEN year = 2026 THEN vote_pct END) as vote_pct_2026
				,  ROUND(COALESCE(MAX(CASE WHEN year = 2026 THEN vote_pct END), 0)
           - COALESCE(MAX(CASE WHEN year = 2021 THEN vote_pct END), 0), 2) AS vote_change
                 ,coalesce(MAX( CASE WHEN year = 2021 then seats end ) ,0)as  seats_2021
				 , coalesce(MAX(case when year = 2026 then seats end),0 )as  seats_2026
FROM combined
GROUP BY party 
ORDER BY seats DESC ;