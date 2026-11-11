-- Bases temporárias; chaves ambíguas são excluídas antes dos JOINs.
CREATE OR REPLACE TEMP VIEW marts_encounters AS
WITH patients AS (
 SELECT * FROM refined.patients WHERE Id IS NOT NULL
 QUALIFY count(*) OVER (PARTITION BY Id) = 1
), encounters AS (
 SELECT * FROM refined.encounters WHERE Id IS NOT NULL
 QUALIFY count(*) OVER (PARTITION BY Id) = 1
), eligible AS (
 SELECT e.*, date_part('year', e.START AT TIME ZONE 'UTC')::INTEGER AS year,
 date_part('year', age(CAST(e.START AT TIME ZONE 'UTC' AS DATE), p.BIRTHDATE))::INTEGER AS age_years
 FROM encounters e JOIN patients p ON p.Id = e.PATIENT
 WHERE e.START IS NOT NULL AND e.STOP >= e.START
 AND p.BIRTHDATE IS NOT NULL
 AND (p.DEATHDATE IS NULL OR p.DEATHDATE >= p.BIRTHDATE)
 AND CAST(e.START AT TIME ZONE 'UTC' AS DATE) >= p.BIRTHDATE
 AND (p.DEATHDATE IS NULL OR CAST(e.STOP AT TIME ZONE 'UTC' AS DATE) <= p.DEATHDATE)
 AND e.ENCOUNTERCLASS IS NOT NULL
 AND e.DESCRIPTION IS DISTINCT FROM 'Death Certification'
)
SELECT *, CASE WHEN age_years < 18 THEN '0-17' WHEN age_years < 45 THEN '18-44'
 WHEN age_years < 65 THEN '45-64' ELSE '65+' END AS age_group,
 coalesce(BASE_ENCOUNTER_COST >= 0 AND TOTAL_CLAIM_COST >= BASE_ENCOUNTER_COST
 AND PAYER_COVERAGE BETWEEN 0 AND TOTAL_CLAIM_COST, false) AS finance_valid
FROM eligible;
CREATE OR REPLACE TEMP VIEW marts_medications AS
SELECT m.*,
 coalesce(m.BASE_COST >= 0 AND m.TOTALCOST >= 0
 AND m.PAYER_COVERAGE BETWEEN 0 AND m.TOTALCOST AND m.DISPENSES > 0
 AND CAST(m.TOTALCOST AS DECIMAL(38,2)) = CAST(m.BASE_COST AS DECIMAL(38,2)) * m.DISPENSES, false) AS finance_valid
FROM refined.medications m JOIN marts_encounters e
 ON e.Id = m.ENCOUNTER AND e.PATIENT = m.PATIENT
-- O vínculo permite início posterior ao atendimento; preservar o alerta na REFINED.
WHERE m.START >= e.START
 AND (m.STOP IS NULL OR m.STOP >= m.START)
 AND m.CODE IS NOT NULL AND m._medication_id IS NOT NULL
QUALIFY count(*) OVER (PARTITION BY m._medication_id) = 1;
