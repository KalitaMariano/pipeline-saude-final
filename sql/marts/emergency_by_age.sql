CREATE OR REPLACE TABLE marts.emergency_by_age AS
SELECT age_group, count(*) AS encounter_count,
 count(*) FILTER (WHERE ENCOUNTERCLASS = 'emergency') AS emergency_count,
 count(DISTINCT PATIENT) AS patient_count,
 count(DISTINCT PATIENT) FILTER (WHERE ENCOUNTERCLASS = 'emergency') AS emergency_patient_count,
 count(*) FILTER (WHERE ENCOUNTERCLASS = 'emergency')::DOUBLE / count(*) AS emergency_encounter_proportion
FROM marts_encounters GROUP BY age_group;
