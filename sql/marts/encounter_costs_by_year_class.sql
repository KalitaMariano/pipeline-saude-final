CREATE OR REPLACE TABLE marts.encounter_costs_by_year_class AS
SELECT year, ENCOUNTERCLASS AS encounter_class, count(*) AS encounter_count,
 count(*) FILTER (WHERE finance_valid) AS financial_encounter_count,
 sum(BASE_ENCOUNTER_COST) FILTER (WHERE finance_valid) AS base_encounter_cost,
 sum(TOTAL_CLAIM_COST) FILTER (WHERE finance_valid) AS total_claim_cost,
 sum(PAYER_COVERAGE) FILTER (WHERE finance_valid) AS payer_coverage,
 sum(TOTAL_CLAIM_COST - PAYER_COVERAGE) FILTER (WHERE finance_valid) AS uncovered_claim_cost,
 sum(TOTAL_CLAIM_COST) FILTER (WHERE finance_valid) / nullif(count(*) FILTER (WHERE finance_valid), 0) AS mean_claim_cost,
 sum(PAYER_COVERAGE) FILTER (WHERE finance_valid) / nullif(sum(TOTAL_CLAIM_COST) FILTER (WHERE finance_valid), 0) AS coverage_ratio
FROM marts_encounters GROUP BY year, ENCOUNTERCLASS;
