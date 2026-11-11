"""CLI instalada e erros, sempre com arquivos e bancos fictícios temporários."""
import csv
import json
import sys
from decimal import Decimal

import duckdb
import pytest

from pipeline_saude import cli
from pipeline_saude.marts.transform import run_marts
from pipeline_saude.refined.transform import run_refined
from conftest import HEADERS


@pytest.fixture
def synthetic_csvs(connection, tmp_path):
    directory = tmp_path / 'synthetic'
    directory.mkdir()
    for table, header in HEADERS.items():
        columns = header.split()
        with (directory/f'{table}.csv').open('w',encoding='utf-8',newline='') as file:
            writer = csv.writer(file)
            writer.writerow(columns)
            projection = ','.join(f'"{column}"' for column in columns)
            writer.writerows(connection.execute(f'SELECT {projection} FROM raw.{table}').fetchall())
    return directory


def test_cli_executes_three_layers_with_default_database_in_temporary_directory(synthetic_csvs,tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path)
    reports = {}
    for layer in ('raw','refined','marts'):
        args = ['pipeline-saude',layer]
        if layer == 'raw':
            args += ['--data-dir',str(synthetic_csvs)]
        monkeypatch.setattr(sys,'argv',args)
        assert cli.main() == 0
        output = capsys.readouterr()
        assert output.err == ''
        reports[layer] = json.loads(output.out)
        assert reports[layer]['database'] == str(tmp_path/'artifacts/saude.duckdb')
    assert [t['obtained'] for t in reports['raw']['tables']] == [1,1,1]
    assert all(t['obtained']==1 for t in reports['refined']['tables'].values())
    assert reports['marts']['eligible_encounters']==1
    assert reports['marts']['eligible_medications']==1
    with duckdb.connect(str(tmp_path/'artifacts/saude.duckdb'),read_only=True) as con:
        assert con.execute('SELECT * FROM marts.dashboard_kpis').fetchone() == (1,1,1,1.0,Decimal('20.20'),Decimal('2.50'))


@pytest.mark.parametrize('layer',['raw','refined','marts'])
def test_cli_missing_inputs_return_failure_without_creating_database(layer,tmp_path,monkeypatch,capsys):
    database = tmp_path/'missing.duckdb'
    args=['pipeline-saude',layer,'--database',str(database)]
    if layer=='raw':
        args += ['--data-dir',str(tmp_path/'no-csvs')]
    monkeypatch.setattr(sys,'argv',args)
    assert cli.main() == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert f'Falha na etapa {layer}' in output.err
    assert not database.exists()


@pytest.mark.parametrize('layer',['refined','marts'])
def test_cli_existing_database_missing_schema_reports_failure(layer,tmp_path,monkeypatch,capsys):
    database=tmp_path/'empty.duckdb'
    with duckdb.connect(str(database)) as con:
        con.execute('CREATE TABLE sentinel (value INTEGER)')
        con.execute('INSERT INTO sentinel VALUES (42)')
    monkeypatch.setattr(sys,'argv',['pipeline-saude',layer,'--database',str(database)])
    assert cli.main()==1
    assert f'Falha na etapa {layer}' in capsys.readouterr().err
    with duckdb.connect(str(database)) as con:
        assert con.execute('SELECT * FROM sentinel').fetchall()==[(42,)]


@pytest.mark.parametrize('runner',[run_refined,run_marts])
def test_layer_runner_rejects_nonexistent_database(runner,tmp_path):
    path=tmp_path/'missing.duckdb'
    with pytest.raises(ValueError,match='Banco inexistente'):
        runner(path)
    assert not path.exists()
