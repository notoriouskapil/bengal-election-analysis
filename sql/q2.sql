-- 2) Vote share vs seat share, 2026
with total_seats as (
 SELECT  year 
                 ,SUM(CASE WHEN winner_party NOT NULL THEN 1  END) as  total_seat
from  winners
WHERE year =2026
GROUP BY year
)
, party_seats as(
SELECT year , winner_party as party, sum(CASE WHEN winner_party NOT NULL THEN 1 END ) as num_seats 
FROM winners
WHERE year = 2026
GROUP BY  1 , 2
)
, 
total_votes as (
SELECT  year , sum(total_votes ) as votes_year
FROM results 
WHERE year = 2026
GROUP BY 1 
),
party_votes as(
SELECT  party ,
                   year 
                  ,SUM(total_votes) as total_party_votes
				  
FROM results 
WHERE year =2026
GROUP BY 1,2
)
, combine1 as (
SELECT s.party ,
                  ROUND(s.num_seats*100.0/t.total_seat,2) as seat_share
FROM party_seats s 
JOIN total_seats t  ON t.year= s.year 
)
, combine2 as (
SELECT p. party 
                ,p.year
                , round(p. total_party_votes*100.0/t.votes_year,2) as vote_pct 
FROM party_votes p 
JOIN  total_votes t on t.year = p.year 
)


SELECT v.party , v.vote_pct ,coalesce( s.seat_share,0 ) as seat_share 
                  , ROUND((coalesce(seat_share,0) - vote_pct ) ,2) as eat_vote_gap
FROM combine2 v
LEFT JOIN combine1  s ON s.party = v.party
ORDER BY  2 desc ;