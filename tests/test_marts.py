"""Indicadores com dados fictícios; fixture usa somente DuckDB em memória."""
from decimal import Decimal

import duckdb
import pytest

from pipeline_saude.refined.transform import transform_refined
from pipeline_saude.marts.transform import TABLES, transform_marts


def prepare(connection):
    transform_refined(connection)
    connection.execute("UPDATE refined.encounters SET ENCOUNTERCLASS='emergency'")


def test_five_indicators_and_no_fanout(connection):
    prepare(connection)
    connection.execute("INSERT INTO refined.medications SELECT * REPLACE ('second' AS _medication_id) FROM refined.medications")
    report = transform_marts(connection)
    assert report['eligible_encounters'] == 1
    assert report['eligible_medications'] == 2
    assert connection.execute('SELECT * FROM marts.encounters_by_year_class').fetchall() == [(2020, 'emergency', 1)]
    assert connection.execute('SELECT * FROM marts.emergency_by_age').fetchall() == [('18-44', 1, 1, 1, 1, 1.0)]
    assert connection.execute('SELECT total_claim_cost, payer_coverage, coverage_ratio FROM marts.encounter_costs_by_year_class').fetchone() == (Decimal('20.20'), Decimal('5.05'), .25)
    assert connection.execute('SELECT medication_code, medication_record_count, dispenses, medication_total_cost, cost_per_dispense FROM marts.medication_costs_by_code').fetchone() == ('00042', 2, 4, Decimal('5.00'), 1.25)
    assert connection.execute('SELECT * FROM marts.encounters_with_medications').fetchone() == ('emergency', '18-44', 1, 1, 1.0)
    before = {t: connection.execute(f'SELECT * FROM marts.{t} ORDER BY ALL').fetchall() for t in TABLES}
    assert transform_marts(connection) == report
    assert before == {t: connection.execute(f'SELECT * FROM marts.{t} ORDER BY ALL').fetchall() for t in TABLES}
    assert connection.execute('SELECT count(*) FROM refined.medications').fetchone()[0] == 2


@pytest.mark.parametrize('birth,event,expected', [
    ('2002-01-02','2020-01-01','0-17'), ('2002-01-01','2020-01-01','18-44'),
    ('1975-01-02','2020-01-01','18-44'), ('1975-01-01','2020-01-01','45-64'),
    ('1955-01-02','2020-01-01','45-64'), ('1955-01-01','2020-01-01','65+'),
])
def test_age_at_event_birthday_boundaries(connection, birth, event, expected):
    prepare(connection)
    connection.execute('UPDATE refined.patients SET BIRTHDATE=?', [birth])
    # UTC is January 1, although local timestamp is December 31.
    connection.execute("UPDATE refined.encounters SET START='2019-12-31T22:00:00-02:00'")
    transform_marts(connection)
    assert connection.execute('SELECT age_group FROM marts.emergency_by_age').fetchone()[0] == expected
    assert connection.execute('SELECT year FROM marts.encounters_by_year_class').fetchone()[0] == 2020


@pytest.mark.parametrize('change', [
    "UPDATE refined.encounters SET DESCRIPTION='Death Certification'",
    "UPDATE refined.patients SET DEATHDATE='2019-01-01'",
    "UPDATE refined.patients SET BIRTHDATE='2021-01-01'",
    "UPDATE refined.encounters SET PATIENT='orphan'",
    "INSERT INTO refined.patients SELECT * FROM refined.patients",
    "INSERT INTO refined.encounters SELECT * FROM refined.encounters",
    "UPDATE refined.encounters SET STOP=START-INTERVAL '1 second'",
])
def test_clinical_exclusions_preserve_refined(connection, change):
    prepare(connection)
    connection.execute(change)
    before = connection.execute('SELECT count(*) FROM refined.encounters').fetchone()
    assert transform_marts(connection)['eligible_encounters'] == 0
    assert all(connection.execute(f'SELECT count(*) FROM marts.{t}').fetchone()[0] == 0 for t in TABLES)
    assert connection.execute('SELECT count(*) FROM refined.encounters').fetchone() == before


def test_financial_quality_does_not_remove_utilization_or_association(connection):
    prepare(connection)
    connection.execute('UPDATE refined.encounters SET PAYER_COVERAGE=99')
    connection.execute('UPDATE refined.medications SET TOTALCOST=-1')
    transform_marts(connection)
    assert connection.execute('SELECT encounter_count, financial_encounter_count, total_claim_cost, coverage_ratio FROM marts.encounter_costs_by_year_class').fetchone() == (1, 0, None, None)
    assert connection.execute('SELECT medication_record_count, financial_record_count, medication_total_cost FROM marts.medication_costs_by_code').fetchone() == (1, 0, None)
    assert connection.execute('SELECT medication_encounter_proportion FROM marts.encounters_with_medications').fetchone()[0] == 1


@pytest.mark.parametrize('change', [
    "UPDATE refined.medications SET PATIENT='other'",
    "UPDATE refined.medications SET ENCOUNTER='orphan'",
    "UPDATE refined.medications SET START=START-INTERVAL '1 day'",
    "INSERT INTO refined.medications SELECT * FROM refined.medications",
])
def test_invalid_medication_links(connection, change):
    prepare(connection)
    connection.execute(change)
    assert transform_marts(connection)['eligible_medications'] == 0
    assert connection.execute('SELECT encounter_count, encounters_with_medications, medication_encounter_proportion FROM marts.encounters_with_medications').fetchone() == (1, 0, 0.0)


def test_denominators_and_zero_cost(connection):
    prepare(connection)
    connection.execute("INSERT INTO refined.encounters SELECT * REPLACE ('e2' AS Id, 'ambulatory' AS ENCOUNTERCLASS) FROM refined.encounters")
    connection.execute('UPDATE refined.encounters SET BASE_ENCOUNTER_COST=0, TOTAL_CLAIM_COST=0, PAYER_COVERAGE=0')
    transform_marts(connection)
    assert connection.execute('SELECT encounter_count, emergency_count, patient_count, emergency_encounter_proportion FROM marts.emergency_by_age').fetchone() == (2, 1, 1, .5)
    assert connection.execute('SELECT coverage_ratio FROM marts.encounter_costs_by_year_class').fetchall() == [(None,), (None,)]


def test_empty_and_atomic_rollback(connection):
    prepare(connection)
    transform_marts(connection)
    connection.execute('ALTER TABLE refined.medications DROP COLUMN CODE')
    with pytest.raises(duckdb.Error):
        transform_marts(connection)
    assert connection.execute('SELECT encounter_count FROM marts.encounters_by_year_class').fetchone()[0] == 1
    connection.execute('ALTER TABLE refined.medications ADD COLUMN CODE VARCHAR')
    for t in ('medications', 'encounters', 'patients'):
        connection.execute(f'DELETE FROM refined.{t}')
    assert transform_marts(connection)['eligible_encounters'] == 0
    assert all(connection.execute(f'SELECT count(*) FROM marts.{t}').fetchone()[0] == 0 for t in TABLES)


def test_medication_after_encounter_is_associated_and_flags_preserved(connection):
    # A REFINED gera o alerta a partir da origem fictícia, antes da MARTS.
    connection.execute("UPDATE raw.medications SET START='2020-01-02T00:00:00Z', STOP=''")
    prepare(connection)
    before = connection.execute("SELECT * EXCLUDE (START, STOP, _refined_at, _ingested_at) FROM refined.medications").fetchall()
    assert connection.execute("SELECT list_contains(_quality_flags, 'start_after_encounter') FROM refined.medications").fetchone() == (True,)
    report = transform_marts(connection)
    assert report['eligible_medications'] == 1
    assert connection.execute("SELECT medication_record_count, dispenses, medication_total_cost FROM marts.medication_costs_by_code").fetchone() == (1, 2, Decimal('2.50'))
    assert connection.execute("SELECT encounter_count, encounters_with_medications, medication_encounter_proportion FROM marts.encounters_with_medications").fetchone() == (1, 1, 1.0)
    assert connection.execute("SELECT total_claim_cost FROM marts.encounter_costs_by_year_class").fetchone() == (Decimal('20.20'),)
    assert connection.execute("SELECT * EXCLUDE (START, STOP, _refined_at, _ingested_at) FROM refined.medications").fetchall() == before
    assert connection.execute("SELECT CAST(START AT TIME ZONE 'UTC' AS VARCHAR), STOP IS NULL FROM refined.medications").fetchone() == ('2020-01-02 00:00:00', True)
