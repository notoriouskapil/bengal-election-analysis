-- 6) For each seat, how much did the electoral roll change between 2021 and 2026, and how much did turnout change?


WITH electrol_roll AS (
         SELECT year 
		                ,ac_no 
						,total_electors
	  FROM electorate 
	  GROUP BY 1,2
),
turnout as (
SELECT year 
                , ac_no 
				,turnout_pct
FROM electorate
GROUP BY 1,2 
)
, combine as (
            SELECT e. ac_no
			               ,e.year 
						   ,e.total_electors
						   ,t.turnout_pct
			FROM electrol_roll e
			JOIN turnout t ON t.ac_no = e.ac_no AND t.year = e.year
)
SELECT ac_no 
               ,MAX(CASE WHEN year=2021 THEN   total_electors END ) AS electoral_roll_2021 
			   ,MAX(CASE WHEN year=2026 THEN   total_electors END ) AS electoral_roll_2026
			   ,ROUND(MAX(CASE WHEN year=2026 THEN   total_electors END )-MAX(CASE WHEN year=2021 THEN   total_electors END ),2) AS electrol_chng
			   ,MAX(CASE WHEN year = 2021 THEN turnout_pct END) as turnout_pct_2021
			   ,MAX(CASE WHEN year = 2026 THEN turnout_pct END) as turnout_pct_2026
			   ,ROUND(MAX(CASE WHEN year = 2026 THEN turnout_pct END)-MAX(CASE WHEN year = 2021 THEN turnout_pct END),2) as turnout_pct_chng
 FROM combine
 WHERE  ac_no<>144
GROUP BY  ac_no ;
