CREATE OR REPLACE TABLE marts.encounters_with_medications AS
WITH links AS (SELECT DISTINCT ENCOUNTER FROM marts_medications)
SELECT e.ENCOUNTERCLASS AS encounter_class, e.age_group, count(*) AS encounter_count,
 count(l.ENCOUNTER) AS encounters_with_medications,
 count(l.ENCOUNTER)::DOUBLE / count(*) AS medication_encounter_proportion
FROM marts_encounters e LEFT JOIN links l ON l.ENCOUNTER = e.Id
GROUP BY e.ENCOUNTERCLASS, e.age_group;
