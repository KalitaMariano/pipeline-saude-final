CREATE OR REPLACE TABLE marts.encounters_by_year_class AS
SELECT year, ENCOUNTERCLASS AS encounter_class, count(*) AS encounter_count
FROM marts_encounters GROUP BY year, ENCOUNTERCLASS;
