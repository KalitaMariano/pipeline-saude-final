CREATE OR REPLACE TABLE marts.medication_costs_by_code AS
WITH costs AS (
SELECT CODE AS medication_code,
 string_agg(DISTINCT DESCRIPTION, ' | ' ORDER BY DESCRIPTION) AS medication_description,
 count(*) AS medication_record_count,
 count(DISTINCT ENCOUNTER) AS encounter_count,
 count(*) FILTER (WHERE finance_valid) AS financial_record_count,
 sum(DISPENSES) FILTER (WHERE finance_valid) AS dispenses,
 sum(TOTALCOST) FILTER (WHERE finance_valid) AS medication_total_cost,
 sum(PAYER_COVERAGE) FILTER (WHERE finance_valid) AS medication_payer_coverage,
 sum(TOTALCOST) FILTER (WHERE finance_valid) / nullif(sum(DISPENSES) FILTER (WHERE finance_valid), 0) AS cost_per_dispense
FROM marts_medications GROUP BY CODE
)
SELECT *, medication_total_cost / nullif(sum(medication_total_cost) OVER (), 0)
 AS medication_cost_proportion
FROM costs;
