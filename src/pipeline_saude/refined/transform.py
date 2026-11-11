"""Transforma o snapshot raw preservando cardinalidade e linhagem."""

from pathlib import Path

import duckdb

from pipeline_saude.raw.ingest import METADATA, TABLES, quote_identifier as ident


TYPES = {
    "patients": {
        "BIRTHDATE": "DATE", "DEATHDATE": "DATE", "LAT": "DOUBLE", "LON": "DOUBLE",
        "HEALTHCARE_EXPENSES": "DECIMAL(18,2)",
        "HEALTHCARE_COVERAGE": "DECIMAL(18,2)", "INCOME": "BIGINT",
    },
    "encounters": {
        "START": "TIMESTAMPTZ", "STOP": "TIMESTAMPTZ",
        "BASE_ENCOUNTER_COST": "DECIMAL(18,2)",
        "TOTAL_CLAIM_COST": "DECIMAL(18,2)", "PAYER_COVERAGE": "DECIMAL(18,2)",
    },
    "medications": {
        "START": "TIMESTAMPTZ", "STOP": "TIMESTAMPTZ",
        "BASE_COST": "DECIMAL(18,2)", "PAYER_COVERAGE": "DECIMAL(18,2)",
        "TOTALCOST": "DECIMAL(18,2)", "DISPENSES": "BIGINT",
    },
}
PATTERNS = {
    "DATE": r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
    "TIMESTAMPTZ": (
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})"
    ),
    "DECIMAL(18,2)": r"[+-]?[0-9]+(\.[0-9]{1,2})?",
    "BIGINT": r"[+-]?[0-9]+",
}


def _convert(connection, table):
    columns = connection.execute(f"DESCRIBE raw.{table}").fetchall()
    names = {c[0] for c in columns}
    if not (set(TYPES[table]) | set(METADATA)) <= names:
        raise ValueError(f"raw.{table}: colunas obrigatórias ausentes")
    if names & {"_quality_flags", "_refined_at", "_medication_id"}:
        raise ValueError(f"raw.{table}: conflito com metadados refined")
    expressions = []
    for column, source_type, *_ in columns:
        q = ident(column)
        if column in METADATA:
            expressions.append(q)
            continue
        if source_type != "VARCHAR":
            raise ValueError(f"raw.{table}.{column}: esperado VARCHAR")
        value = f"NULLIF({q}, '')"
        target = TYPES[table].get(column, "VARCHAR")
        if target != "VARCHAR":
            invalid = f"TRY_CAST({value} AS {target}) IS NULL"
            if target in PATTERNS:
                invalid += f" OR NOT regexp_full_match({value}, ?)"
                params = [PATTERNS[target]]
            else:
                invalid += f" OR NOT isfinite(TRY_CAST({value} AS DOUBLE))"
                params = []
            count = connection.execute(
                f"SELECT count(*) FROM raw.{table} WHERE {value} IS NOT NULL "
                f"AND ({invalid})", params,
            ).fetchone()[0]
            if count:
                raise ValueError(f"raw.{table}.{column}: {count} valor(es) inválido(s) para {target}")
        expressions.append(f"CAST({value} AS {target}) AS {q}")
    expressions.append("current_timestamp AS _refined_at")
    if table == "medications":
        invalid_lineage = connection.execute(
            "SELECT count(*) FROM raw.medications WHERE "
            "coalesce(_source_file, '') = '' OR coalesce(_source_sha256, '') = '' "
            "OR _source_row_number IS NULL OR _source_row_number < 1"
        ).fetchone()[0]
        duplicate_lineage = connection.execute(
            "SELECT count(*) FROM (SELECT 1 FROM raw.medications GROUP BY "
            "_source_file, _source_sha256, _source_row_number HAVING count(*) > 1)"
        ).fetchone()[0]
        if invalid_lineage or duplicate_lineage:
            raise ValueError("raw.medications: linhagem ausente ou repetida; identificação ambígua")
        expressions.append(
            "sha256(to_json(list_value(_source_file, _source_sha256, "
            "CAST(_source_row_number AS VARCHAR)))) AS _medication_id"
        )
    connection.execute(
        f"CREATE OR REPLACE TABLE refined.{table} AS SELECT "
        + ", ".join(expressions) + f" FROM raw.{table}"
    )


def _rules(table):
    rules = {}
    if table in ("patients", "encounters"):
        rules.update({
            "missing_id": "r.Id IS NULL",
            "duplicate_id": "r.Id IS NOT NULL AND count(*) OVER (PARTITION BY r.Id) > 1",
        })
    if table == "patients":
        rules.update({
            "missing_birthdate": "r.BIRTHDATE IS NULL",
            "death_before_birth": "r.DEATHDATE < r.BIRTHDATE",
            "unknown_zip": "r.ZIP IS NULL OR r.ZIP = '00000'",
            "invalid_zip": "r.ZIP IS NOT NULL AND NOT regexp_full_match(r.ZIP, '[0-9]{5}')",
            "missing_fips": "r.FIPS IS NULL",
            "invalid_coordinates": "r.LAT NOT BETWEEN -90 AND 90 OR r.LON NOT BETWEEN -180 AND 180",
            "negative_amount": "r.HEALTHCARE_EXPENSES < 0 OR r.HEALTHCARE_COVERAGE < 0 OR r.INCOME < 0",
        })
        return rules
    rules.update({
        "missing_patient": "r.PATIENT IS NULL",
        "orphan_patient": "r.PATIENT IS NOT NULL AND NOT EXISTS (SELECT 1 FROM refined.patients p WHERE p.Id = r.PATIENT)",
        "missing_start": "r.START IS NULL",
        "stop_before_start": "r.STOP < r.START",
        "zero_duration": "r.STOP = r.START",
        "start_before_birth": "EXISTS (SELECT 1 FROM refined.patients p WHERE p.Id = r.PATIENT AND CAST(r.START AT TIME ZONE 'UTC' AS DATE) < p.BIRTHDATE)",
        "start_after_death": "EXISTS (SELECT 1 FROM refined.patients p WHERE p.Id = r.PATIENT AND CAST(r.START AT TIME ZONE 'UTC' AS DATE) > p.DEATHDATE)",
        "stop_after_death": "EXISTS (SELECT 1 FROM refined.patients p WHERE p.Id = r.PATIENT AND CAST(r.STOP AT TIME ZONE 'UTC' AS DATE) > p.DEATHDATE)",
        "reason_pair_mismatch": "(r.REASONCODE IS NULL) <> (r.REASONDESCRIPTION IS NULL)",
    })
    if table == "encounters":
        rules.update({
            "missing_stop": "r.STOP IS NULL",
            "negative_amount": "r.BASE_ENCOUNTER_COST < 0 OR r.TOTAL_CLAIM_COST < 0 OR r.PAYER_COVERAGE < 0",
            "coverage_above_total": "r.PAYER_COVERAGE > r.TOTAL_CLAIM_COST",
            "total_below_base": "r.TOTAL_CLAIM_COST < r.BASE_ENCOUNTER_COST",
        })
    else:
        rules.update({
            "missing_encounter": "r.ENCOUNTER IS NULL",
            "orphan_encounter": "r.ENCOUNTER IS NOT NULL AND NOT EXISTS (SELECT 1 FROM refined.encounters e WHERE e.Id = r.ENCOUNTER)",
            "patient_encounter_mismatch": "EXISTS (SELECT 1 FROM refined.encounters e WHERE e.Id = r.ENCOUNTER AND e.PATIENT IS DISTINCT FROM r.PATIENT)",
            "start_before_encounter": "EXISTS (SELECT 1 FROM refined.encounters e WHERE e.Id = r.ENCOUNTER AND r.START < e.START)",
            "start_after_encounter": "EXISTS (SELECT 1 FROM refined.encounters e WHERE e.Id = r.ENCOUNTER AND r.START > e.STOP)",
            "negative_amount": "r.BASE_COST < 0 OR r.TOTALCOST < 0 OR r.PAYER_COVERAGE < 0",
            "coverage_above_total": "r.PAYER_COVERAGE > r.TOTALCOST",
            "invalid_dispenses": "r.DISPENSES IS NULL OR r.DISPENSES <= 0",
            "cost_product_mismatch": "CAST(r.TOTALCOST AS DECIMAL(38,2)) <> CAST(r.BASE_COST AS DECIMAL(38,2)) * r.DISPENSES",
        })
    return rules


def transform_refined(connection: duckdb.DuckDBPyConnection) -> dict:
    """Substitui refined atomicamente; conexão pode ser inteiramente em memória."""
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute("CREATE SCHEMA IF NOT EXISTS refined")
        for table in TABLES:
            _convert(connection, table)
        report = {}
        for table in TABLES:
            flags = ", ".join(
                f"CASE WHEN {condition} THEN '{flag}' END"
                for flag, condition in _rules(table).items()
            )
            connection.execute(
                f"CREATE OR REPLACE TABLE refined.{table} AS SELECT r.*, "
                f"list_filter([{flags}], flag -> flag IS NOT NULL) AS _quality_flags "
                f"FROM refined.{table} r"
            )
            expected = connection.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
            actual = connection.execute(f"SELECT count(*) FROM refined.{table}").fetchone()[0]
            if actual != expected:
                raise RuntimeError(f"refined.{table}: contagem divergente")
            counts = connection.execute(
                f"SELECT flag, count(*) FROM refined.{table}, "
                "UNNEST(_quality_flags) AS flags(flag) GROUP BY flag ORDER BY flag"
            ).fetchall()
            report[table] = {"expected": expected, "obtained": actual, "quality_flags": dict(counts)}
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return report


def run_refined(database: Path) -> dict:
    """Abre somente um banco existente; não lê nem altera arquivos CSV."""
    database = Path(database).resolve()
    if not database.is_file():
        raise ValueError(f"Banco inexistente: {database}. Execute a RAW primeiro.")
    with duckdb.connect(str(database)) as connection:
        return {"database": str(database), "tables": transform_refined(connection)}
