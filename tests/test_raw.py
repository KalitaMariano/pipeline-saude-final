"""Ingestão com CSVs inventados em tmp_path e DuckDB real."""
import csv
import hashlib

import duckdb
import pytest

from pipeline_saude.raw.ingest import TABLES, ingest_raw, read_source


@pytest.fixture
def raw_sources(tmp_path):
    data = tmp_path / 'source'
    data.mkdir()
    for table in TABLES:
        with (data / f'{table}.csv').open('w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Id', 'CODE', 'DESCRIPTION', 'EMPTY'])
            writer.writerows([
                ['001', '00042', '  ação, "teste"\nsegunda linha  ', ''],
                ['001', '00042', '  ação, "teste"\nsegunda linha  ', ''],
            ])
    return data, tmp_path / 'output' / 'fake.duckdb'


def snapshot(database):
    with duckdb.connect(str(database), read_only=True) as connection:
        return {table: connection.execute(
            f'SELECT to_json(t) FROM raw.{table} t ORDER BY _source_row_number'
        ).fetchall() for table in TABLES}


def test_raw_preserves_values_duplicates_types_and_lineage(raw_sources):
    data, database = raw_sources
    original = {p.name: p.read_bytes() for p in data.iterdir()}
    report = ingest_raw(data, database)
    assert report['database'] == str(database.resolve())
    assert all(t['expected'] == t['obtained'] == 2 for t in report['tables'])
    with duckdb.connect(str(database), read_only=True) as con:
        for table in TABLES:
            assert con.execute(f'SELECT Id,CODE,DESCRIPTION,EMPTY FROM raw.{table} ORDER BY _source_row_number').fetchall() == [
                ('001', '00042', '  ação, "teste"\nsegunda linha  ', ''),
                ('001', '00042', '  ação, "teste"\nsegunda linha  ', ''),
            ]
            assert [(r[0],r[1]) for r in con.execute(f'DESCRIBE raw.{table}').fetchall()[:4]] == [
                ('Id','VARCHAR'),('CODE','VARCHAR'),('DESCRIPTION','VARCHAR'),('EMPTY','VARCHAR')]
            assert con.execute(f'SELECT _source_row_number,_source_file,_source_sha256,_batch_id FROM raw.{table} ORDER BY _source_row_number').fetchall() == [
                (i, f'{table}.csv', hashlib.sha256(original[f'{table}.csv']).hexdigest(), report['batch_id']) for i in (1,2)]
            assert con.execute(f'SELECT count(DISTINCT epoch(_ingested_at)) FROM raw.{table}').fetchone() == (1,)
        assert con.execute("SELECT DISTINCT table_schema FROM information_schema.tables WHERE table_schema NOT IN ('information_schema','pg_catalog')").fetchall() == [('raw',)]
    assert original == {p.name:p.read_bytes() for p in data.iterdir()}


def test_raw_reload_replaces_snapshot_instead_of_accumulating(raw_sources):
    data, database = raw_sources
    first = ingest_raw(data, database)
    second = ingest_raw(data, database)
    assert first['batch_id'] != second['batch_id']
    assert first['tables'] == second['tables']
    (data/'patients.csv').write_text('Id,CODE,DESCRIPTION,EMPTY\n002,00001,new,\n', encoding='utf-8')
    third = ingest_raw(data, database)
    assert third['tables'][0]['obtained'] == 1
    with duckdb.connect(str(database),read_only=True) as con:
        assert con.execute('SELECT Id,CODE FROM raw.patients').fetchall() == [('002','00001')]
        assert con.execute('SELECT count(*) FROM raw.encounters').fetchone() == (2,)


def test_raw_rolls_back_earlier_table_when_database_rejects_replacement(raw_sources):
    data, database = raw_sources
    # Unique IDs permitem uma dependência FK real, sem mock ou falha artificial.
    (data/'encounters.csv').write_text('Id,CODE,DESCRIPTION,EMPTY\ne1,42,original,\n',encoding='utf-8')
    ingest_raw(data,database)
    with duckdb.connect(str(database)) as con:
        con.execute('ALTER TABLE raw.encounters ADD PRIMARY KEY (Id)')
        con.execute('CREATE TABLE raw.links (encounter_id VARCHAR REFERENCES raw.encounters(Id))')
        con.execute("INSERT INTO raw.links VALUES ('e1')")
    before = snapshot(database)
    (data/'patients.csv').write_text('Id,CODE,DESCRIPTION,EMPTY\np2,12,changed,\n',encoding='utf-8')
    with pytest.raises(duckdb.DependencyException,match='depend'):
        ingest_raw(data,database)
    assert snapshot(database) == before
    with duckdb.connect(str(database)) as con:
        assert con.execute('SELECT * FROM raw.links').fetchall() == [('e1',)]


@pytest.mark.parametrize('content,error', [
    (b'',ValueError), (b'Id,\n1,x\n',ValueError),
    (b'Id,id\n1,2\n',ValueError), (b'Id,_BATCH_ID\n1,2\n',ValueError),
    (b'Id,CODE\n1\n',ValueError), (b'Id,CODE\n1,2,3\n',ValueError),
    (b'Id,CODE\n1,\x00\n',ValueError), (b'I\x00d\n1\n',ValueError),
    (b'Id\n\xff\n',UnicodeDecodeError), (b'Id\n"unclosed\n',csv.Error),
])
def test_raw_invalid_source_preserves_previous_snapshot(raw_sources,content,error):
    data,database = raw_sources
    ingest_raw(data,database)
    before = snapshot(database)
    (data/'medications.csv').write_bytes(content)
    with pytest.raises(error):
        ingest_raw(data,database)
    assert snapshot(database) == before


def test_raw_missing_file_does_not_create_database(raw_sources):
    data,database = raw_sources
    (data/'medications.csv').unlink()
    with pytest.raises(FileNotFoundError):
        ingest_raw(data,database)
    assert not database.exists()


def test_raw_rejects_database_inside_source(raw_sources):
    data,_ = raw_sources
    with pytest.raises(ValueError,match='fora'):
        ingest_raw(data,data/'fake.duckdb')
    assert not (data/'fake.duckdb').exists()


def test_raw_header_only_source_creates_empty_tables(raw_sources):
    data,database = raw_sources
    for table in TABLES:
        (data/f'{table}.csv').write_text('Id,CODE\n',encoding='utf-8')
    report=ingest_raw(data,database)
    assert all(t['expected']==t['obtained']==0 for t in report['tables'])
    assert read_source(data/'patients.csv')[:2] == (['Id','CODE'],[])
