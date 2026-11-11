"""Dados inteiramente fictícios; conexão DuckDB exclusivamente em memória."""

import duckdb
import pytest


HEADERS = {
    "patients": "Id BIRTHDATE DEATHDATE SSN DRIVERS PASSPORT PREFIX FIRST MIDDLE LAST SUFFIX MAIDEN MARITAL RACE ETHNICITY GENDER BIRTHPLACE ADDRESS CITY STATE COUNTY FIPS ZIP LAT LON HEALTHCARE_EXPENSES HEALTHCARE_COVERAGE INCOME",
    "encounters": "Id START STOP PATIENT ORGANIZATION PROVIDER PAYER ENCOUNTERCLASS CODE DESCRIPTION BASE_ENCOUNTER_COST TOTAL_CLAIM_COST PAYER_COVERAGE REASONCODE REASONDESCRIPTION",
    "medications": "START STOP PATIENT PAYER ENCOUNTER CODE DESCRIPTION BASE_COST PAYER_COVERAGE DISPENSES TOTALCOST REASONCODE REASONDESCRIPTION",
}


@pytest.fixture
def connection():
    with duckdb.connect(":memory:") as con:
        con.execute("CREATE SCHEMA raw")
        for table, header in HEADERS.items():
            columns = ', '.join(f'"{name}" VARCHAR' for name in header.split())
            con.execute(f"""CREATE TABLE raw.{table} ({columns},
                _source_file VARCHAR, _source_sha256 VARCHAR,
                _source_row_number BIGINT, _ingested_at TIMESTAMPTZ, _batch_id VARCHAR)""")
            values = {name: '' for name in header.split()}
            if table == 'patients':
                values.update(Id='p1', BIRTHDATE='1980-01-01', ZIP='00123',
                              FIPS='00111', LAT='10.5', LON='-20.5',
                              HEALTHCARE_EXPENSES='10.10', HEALTHCARE_COVERAGE='2.00', INCOME='123')
            else:
                values.update(START='2020-01-01T02:00:00+02:00', STOP='2020-01-01T01:00:00Z',
                              PATIENT='p1', PAYER='payer1', CODE='00042', DESCRIPTION='  descrição  ')
                if table == 'encounters':
                    values.update(Id='e1', ENCOUNTERCLASS='ambulatory',
                                  BASE_ENCOUNTER_COST='10.10', TOTAL_CLAIM_COST='20.20', PAYER_COVERAGE='5.05')
                else:
                    values.update(ENCOUNTER='e1', BASE_COST='1.25',
                                  PAYER_COVERAGE='0.25', DISPENSES='2', TOTALCOST='2.50')
            row = list(values.values()) + [f'{table}.csv', 'a'*64, 1, '2026-01-01T00:00:00Z', 'raw-batch']
            con.execute(f"INSERT INTO raw.{table} VALUES ({','.join('?' for _ in row)})", row)
        yield con
