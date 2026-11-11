-- Uma linha global, inclusive para bases vazias; mesmas populações aprovadas.
CREATE OR REPLACE TABLE marts.dashboard_kpis AS
WITH links AS (SELECT DISTINCT ENCOUNTER FROM marts_medications),
encounters AS (
 SELECT count(DISTINCT e.PATIENT) AS patient_count,
 count(*) AS encounter_count,
 count(l.ENCOUNTER) AS encounters_with_medications,
 count(l.ENCOUNTER)::DOUBLE / nullif(count(*), 0) AS medication_encounter_proportion,
 sum(e.TOTAL_CLAIM_COST) FILTER (WHERE e.finance_valid) AS total_claim_cost
 FROM marts_encounters e LEFT JOIN links l ON l.ENCOUNTER = e.Id
), medications AS (
 SELECT sum(TOTALCOST) FILTER (WHERE finance_valid) AS medication_total_cost
 FROM marts_medications
)
SELECT encounters.*, medications.medication_total_cost
FROM encounters CROSS JOIN medications;
