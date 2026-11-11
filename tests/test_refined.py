from datetime import date
from decimal import Decimal

import pytest

from pipeline_saude.refined.transform import transform_refined


def flags(con, table):
    return con.execute(f"SELECT _quality_flags FROM refined.{table}").fetchone()[0]


def test_types_values_nulls_and_utc(connection):
    connection.execute("UPDATE raw.medications SET STOP = NULL")
    report = transform_refined(connection)
    assert all(r['expected'] == r['obtained'] == 1 for r in report.values())
    types = dict((r[0], r[1]) for r in connection.execute('DESCRIBE refined.patients').fetchall())
    assert types['BIRTHDATE'] == 'DATE'
    assert types['INCOME'] == 'BIGINT'
    assert types['HEALTHCARE_EXPENSES'] == 'DECIMAL(18,2)'
    assert types['LAT'] == 'DOUBLE'
    assert types['Id'] == types['ZIP'] == types['FIPS'] == 'VARCHAR'
    assert connection.execute('SELECT BIRTHDATE, DEATHDATE, ZIP, FIPS, HEALTHCARE_EXPENSES, INCOME FROM refined.patients').fetchone() == (date(1980, 1, 1), None, '00123', '00111', Decimal('10.10'), 123)
    assert connection.execute("SELECT CODE, DESCRIPTION, REASONCODE, STOP, epoch(START) FROM refined.medications").fetchone() == ('00042', '  descrição  ', None, None, 1577836800.0)
    assert dict((r[0], r[1]) for r in connection.execute('DESCRIBE refined.medications').fetchall())['START'] == 'TIMESTAMP WITH TIME ZONE'
    assert flags(connection, 'medications') == []
    # RAW mantém vazio textual e timestamp com offset original.
    assert connection.execute('SELECT DEATHDATE FROM raw.patients').fetchone() == ('',)
    assert connection.execute('SELECT START FROM raw.medications').fetchone() == ('2020-01-01T02:00:00+02:00',)


def test_duplicates_are_preserved_and_medication_ids_are_stable(connection):
    connection.execute('INSERT INTO raw.medications SELECT * REPLACE (2 AS _source_row_number) FROM raw.medications')
    connection.execute('INSERT INTO raw.patients SELECT * REPLACE (2 AS _source_row_number) FROM raw.patients')
    transform_refined(connection)
    first = connection.execute('SELECT _medication_id FROM refined.medications ORDER BY _source_row_number').fetchall()
    assert len(first) == len(set(first)) == 2
    assert connection.execute('SELECT count(*) FROM refined.patients').fetchone()[0] == 2
    assert connection.execute("SELECT count(*) FROM refined.patients WHERE list_contains(_quality_flags, 'duplicate_id')").fetchone()[0] == 2
    connection.execute("UPDATE raw.medications SET _batch_id = 'new-raw-batch'")
    transform_refined(connection)
    assert connection.execute('SELECT _medication_id FROM refined.medications ORDER BY _source_row_number').fetchall() == first
    assert connection.execute('SELECT count(*) FROM refined.encounters').fetchone()[0] == 1
    assert connection.execute('SELECT count(*) FROM refined.medications').fetchone()[0] == 2


def test_snapshot_changes_replace_previous_records(connection):
    transform_refined(connection)
    old = connection.execute('SELECT _medication_id FROM refined.medications').fetchone()[0]
    connection.execute("UPDATE raw.medications SET _source_sha256 = repeat('b', 64), TOTALCOST = '3.00'")
    transform_refined(connection)
    count, new_id, cost = connection.execute('SELECT count(*), min(_medication_id), min(TOTALCOST) FROM refined.medications').fetchone()
    assert count == 1
    assert cost == Decimal('3.00')
    assert new_id != old
    assert 'cost_product_mismatch' in flags(connection, 'medications')


def test_relationships_missing_keys_and_mismatch(connection):
    connection.execute("UPDATE raw.encounters SET PATIENT = 'unknown'")
    connection.execute("UPDATE raw.medications SET PATIENT = '', ENCOUNTER = 'absent'")
    transform_refined(connection)
    assert 'orphan_patient' in flags(connection, 'encounters')
    assert {'missing_patient', 'orphan_encounter'} <= set(flags(connection, 'medications'))
    connection.execute("UPDATE raw.medications SET PATIENT = 'p1', ENCOUNTER = 'e1'")
    transform_refined(connection)
    assert 'patient_encounter_mismatch' in flags(connection, 'medications')
    assert connection.execute('SELECT count(*) FROM refined.medications').fetchone()[0] == 1


def test_temporal_anomalies_retained_including_death_certification(connection):
    connection.execute("UPDATE raw.patients SET DEATHDATE = '2019-12-31'")
    connection.execute("UPDATE raw.encounters SET DESCRIPTION = 'Death Certification', STOP = '2019-12-31T23:00:00Z'")
    connection.execute("UPDATE raw.medications SET START = '2020-01-02T00:00:00Z', STOP = '2020-01-02T00:00:00Z'")
    transform_refined(connection)
    assert {'stop_before_start', 'start_after_death'} <= set(flags(connection, 'encounters'))
    assert {'zero_duration', 'start_after_death', 'stop_after_death', 'start_after_encounter'} <= set(flags(connection, 'medications'))
    assert connection.execute('SELECT DESCRIPTION FROM refined.encounters').fetchone()[0] == 'Death Certification'
    connection.execute("UPDATE raw.patients SET BIRTHDATE = '2021-01-01'")
    transform_refined(connection)
    assert 'death_before_birth' in flags(connection, 'patients')
    assert 'start_before_birth' in flags(connection, 'encounters')
    connection.execute("UPDATE raw.medications SET START = '2010-01-01T00:00:00Z'")
    transform_refined(connection)
    assert 'start_before_encounter' in flags(connection, 'medications')


def test_quality_rules_do_not_clean_or_drop_values(connection):
    connection.execute("UPDATE raw.patients SET ZIP = '00000', FIPS = '', LAT = '95'")
    connection.execute("UPDATE raw.encounters SET Id = '', REASONCODE = '42'")
    connection.execute("UPDATE raw.medications SET BASE_COST = '-1.25', DISPENSES = '0', PAYER_COVERAGE = '3.00'")
    transform_refined(connection)
    assert {'unknown_zip', 'missing_fips', 'invalid_coordinates'} <= set(flags(connection, 'patients'))
    assert {'missing_id', 'reason_pair_mismatch'} <= set(flags(connection, 'encounters'))
    assert {'negative_amount', 'invalid_dispenses', 'coverage_above_total', 'cost_product_mismatch', 'orphan_encounter'} <= set(flags(connection, 'medications'))
    assert connection.execute('SELECT BASE_COST, DISPENSES FROM refined.medications').fetchone() == (Decimal('-1.25'), 0)


@pytest.mark.parametrize('table,column,value', [
    ('patients', 'BIRTHDATE', '2020-02-30'),
    ('patients', 'LAT', 'NaN'),
    ('patients', 'INCOME', '1.5'),
    ('patients', 'INCOME', '9223372036854775808'),
    ('medications', 'TOTALCOST', '2.505'),
    ('medications', 'TOTALCOST', '10000000000000000.00'),
    ('medications', 'DISPENSES', 'abc'),
    ('medications', 'START', '2020-01-01T00:00:00'),
])
def test_invalid_conversion_rolls_back_every_table(connection, table, column, value):
    transform_refined(connection)
    previous = {name: connection.execute(f'SELECT to_json(r) FROM refined.{name} r').fetchall()
                for name in ('patients', 'encounters', 'medications')}
    connection.execute("UPDATE raw.patients SET FIRST = 'changed'")
    connection.execute(f'UPDATE raw.{table} SET "{column}" = ?', [value])
    with pytest.raises(ValueError, match='inválido'):
        transform_refined(connection)
    for name in previous:
        assert connection.execute(f'SELECT to_json(r) FROM refined.{name} r').fetchall() == previous[name]


@pytest.mark.parametrize('change', [
    'UPDATE raw.medications SET _source_sha256 = NULL',
    'INSERT INTO raw.medications SELECT * FROM raw.medications',
])
def test_ambiguous_lineage_fails_without_publishing_partial_schema(connection, change):
    connection.execute(change)
    with pytest.raises(ValueError, match='linhagem'):
        transform_refined(connection)
    assert connection.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'refined'").fetchone()[0] == 0


def test_empty_snapshot_replaces_old_snapshot(connection):
    transform_refined(connection)
    for table in ('medications', 'encounters', 'patients'):
        connection.execute(f'DELETE FROM raw.{table}')
    report = transform_refined(connection)
    assert all(r['expected'] == r['obtained'] == 0 and not r['quality_flags'] for r in report.values())
