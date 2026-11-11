CREATE OR REPLACE TABLE marts.medication_costs_by_code AS
SELECT CODE AS medication_code, count(*) AS medication_record_count,
 count(DISTINCT ENCOUNTER) AS encounter_count,
 count(*) FILTER (WHERE finance_valid) AS financial_record_count,
 sum(DISPENSES) FILTER (WHERE finance_valid) AS dispenses,
 sum(TOTALCOST) FILTER (WHERE finance_valid) AS medication_total_cost,
 sum(PAYER_COVERAGE) FILTER (WHERE finance_valid) AS medication_payer_coverage,
 sum(TOTALCOST) FILTER (WHERE finance_valid) / nullif(sum(DISPENSES) FILTER (WHERE finance_valid), 0) AS cost_per_dispense
FROM marts_medications GROUP BY CODE;
