-- 4) Top 20 closest seats in each year

with margin as  (
SELECT ac_no
                ,winner as candidate_name 
				, winner_party
				,year 
				,win_margin
				, DENSE_RANK() OVER(PARTITION BY year ORDER BY win_margin asc  ) as rnk
FROM winners

)

SELECT *
FROM margin 
WHERE rnk <= 20 ;
