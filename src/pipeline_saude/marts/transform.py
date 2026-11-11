"""Materialização atômica e idempotente dos cinco indicadores SQL."""
from pathlib import Path

import duckdb

TABLES = (
    'encounters_by_year_class', 'emergency_by_age',
    'encounter_costs_by_year_class', 'medication_costs_by_code',
    'encounters_with_medications',
)


def sql_directory():
    packaged = Path(__file__).resolve().parents[1] / 'sql' / 'marts'
    return packaged if packaged.is_dir() else Path(__file__).resolve().parents[3] / 'sql' / 'marts'


def transform_marts(connection: duckdb.DuckDBPyConnection) -> dict:
    """Substitui as cinco tabelas juntas; nunca modifica REFINED."""
    connection.execute('BEGIN TRANSACTION')
    try:
        connection.execute('CREATE SCHEMA IF NOT EXISTS marts')
        connection.execute((sql_directory() / '_base.sql').read_text())
        report = {'eligible_encounters': connection.execute('SELECT count(*) FROM marts_encounters').fetchone()[0],
                  'eligible_medications': connection.execute('SELECT count(*) FROM marts_medications').fetchone()[0],
                  'tables': {}}
        for table in TABLES:
            connection.execute((sql_directory() / f'{table}.sql').read_text())
            report['tables'][table] = connection.execute(f'SELECT count(*) FROM marts.{table}').fetchone()[0]
        connection.execute('DROP VIEW marts_medications')
        connection.execute('DROP VIEW marts_encounters')
        connection.execute('COMMIT')
        return report
    except Exception:
        connection.execute('ROLLBACK')
        raise


def run_marts(database: Path) -> dict:
    database = Path(database).resolve()
    if not database.is_file():
        raise ValueError(f'Banco inexistente: {database}. Execute RAW e REFINED primeiro.')
    with duckdb.connect(str(database)) as connection:
        return {'database': str(database), **transform_marts(connection)}
