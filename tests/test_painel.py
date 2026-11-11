"""Dashboard com dados fictícios; nenhum acesso ao banco/CSV do projeto."""
import ast
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import duckdb
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import app
import painel
from pipeline_saude.marts.transform import TABLES, transform_marts
from pipeline_saude.refined.transform import transform_refined


@pytest.fixture
def interface_graphs(monkeypatch):
    """Isola controles/cache; as figuras reais são verificadas nos testes próprios."""
    for name in ('evolucao', 'emergencia', 'custos_atendimentos',
                 'custos_medicamentos', 'associacao', 'participacao_medicamentos'):
        def lightweight_figure(frame, chart_name=name):
            # Registra linhas e identidade do gráfico; não agrega valores.
            return {'data': [{'type': 'scatter', 'x': [0], 'y': [0]}],
                    'layout': {'template': {}, 'meta': {
                        'chart': chart_name, 'rows': frame.to_json(orient='split')}}}
        monkeypatch.setattr(painel, name, lightweight_figure)


@pytest.fixture
def frames(connection):
    transform_refined(connection)
    transform_marts(connection)
    return {t: connection.execute(f'SELECT * FROM marts.{t}').fetchdf() for t in TABLES}


@pytest.fixture
def fake_database(tmp_path, frames):
    path = tmp_path / 'fake.duckdb'
    with duckdb.connect(str(path)) as con:
        con.execute('CREATE SCHEMA marts')
        for table, frame in frames.items():
            con.register('input_frame', frame)
            con.execute(f'CREATE TABLE marts.{table} AS SELECT * FROM input_frame')
    return path


@pytest.mark.parametrize('value,expected', [(1234567, '1.234.567'), (-1234,'-1.234'), (0,'0'), (None,'—'), (float('nan'),'—'), (pd.NA,'—')])
def test_numero(value, expected):
    assert painel.numero(value) == expected


def test_decimal_percent_and_no_currency():
    assert painel.numero(Decimal('1234.56'),2) == '1.234,56'
    assert painel.monetario(Decimal('-1234.56')) == '-1.234,56'
    assert painel.pct(Decimal('.399964')) == '40,0%'
    assert painel.pct(0) == '0,0%'
    assert painel.pct(None) == painel.monetario(None) == '—'


def test_read_six_tables_readonly_and_close(fake_database, frames):
    result = painel.ler(fake_database)
    assert list(result) == list(TABLES)
    for table in TABLES:
        pd.testing.assert_frame_equal(result[table], frames[table], check_dtype=False)
    # Uma conexão read_only vazada impediria esta abertura com outra configuração.
    with duckdb.connect(str(fake_database)) as writer:
        writer.execute('CREATE TABLE writable (id INTEGER)')
        assert writer.execute('SELECT count(*) FROM writable').fetchone() == (0,)
        # A leitura deve tentar read_only, incompatível com a conexão de escrita aberta.
        with pytest.raises(duckdb.ConnectionException, match='different configuration'):
            painel.ler(fake_database)


def test_missing_table_closes_connection(fake_database):
    with duckdb.connect(str(fake_database)) as con:
        con.execute('DROP TABLE marts.emergency_by_age')
    with pytest.raises(painel.TabelaMartsAusente,match='marts.emergency_by_age'):
        painel.ler(fake_database)
    with duckdb.connect(str(fake_database)) as writer:
        writer.execute('CREATE TABLE writable (id INTEGER)')
        assert writer.execute('SELECT count(*) FROM writable').fetchone() == (0,)


def test_read_queries_are_exclusively_select_all_from_marts():
    tree = ast.parse(Path(painel.__file__).read_text())
    reader = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ler')
    queries = [n for n in ast.walk(reader) if isinstance(n,ast.Call)
               and isinstance(n.func,ast.Attribute) and n.func.attr=='execute']
    assert len(queries)==1
    assert ast.unparse(queries[0].args[0]) == "f'SELECT * FROM marts.{table}'"


def test_missing_database_not_created(tmp_path):
    path=tmp_path/'missing.duckdb'
    with pytest.raises(FileNotFoundError):
        painel.ler(path)
    assert not path.exists()


def test_default_path_uses_shared_configuration(fake_database,monkeypatch):
    monkeypatch.setattr(painel.config,'DATABASE_PATH',fake_database)
    assert len(painel.ler()['dashboard_kpis']) == 1


@pytest.mark.parametrize('function,table', [
    (painel.evolucao,'encounters_by_year_class'),
    (painel.emergencia,'emergency_by_age'),
    (painel.custos_atendimentos,'encounter_costs_by_year_class'),
    (painel.custos_medicamentos,'medication_costs_by_code'),
    (painel.associacao,'encounters_with_medications'),
    (painel.participacao_medicamentos,'medication_costs_by_code'),
])
def test_small_and_empty_frames(function,table,frames):
    frame=frames[table];before=frame.copy(deep=True)
    fig=function(frame)
    assert len(fig.data)>0
    assert fig.layout.title.text
    pd.testing.assert_frame_equal(frame,before)
    assert function(frame.iloc[:0]).layout.title.text


def test_sorting_top_ten_without_recalculating_proportion():
    frame=pd.DataFrame({'medication_code':[f'{i:03}' for i in range(12)],
                        'medication_total_cost':list(range(12)),
                        'medication_description':[f'Medicamento {i}' for i in range(12)],
                        'medication_cost_proportion':[.02]*12})
    for function in (painel.custos_medicamentos,painel.participacao_medicamentos):
        fig=function(frame)
        assert list(fig.data[0].y)==[f'{i:03}' for i in range(11,1,-1)]
        assert fig.layout.yaxis.autorange=='reversed'
        assert list(fig.data[0].customdata[:,0])==[f'Medicamento {i}' for i in range(11,1,-1)]
        assert 'Descrição: %{customdata[0]}' in fig.data[0].hovertemplate
    assert list(painel.participacao_medicamentos(frame).data[0].x)==[.02]*10


def test_age_order_and_chronological_lines():
    frame=pd.DataFrame({'year':[2022,2020,2021],'encounter_class':['wellness']*3,'encounter_count':[3,1,2]})
    before=frame.copy()
    assert list(painel.evolucao(frame).data[0].x)==[2020,2021,2022]
    filtered=painel.filtrar_anos(frame,2021,2021)
    assert filtered['encounter_count'].tolist()==[2]
    assert painel.filtrar_anos(frame,1900,1999).empty
    pd.testing.assert_frame_equal(frame,before)
    ages=pd.DataFrame({'age_group':['65+','0-17'], 'emergency_encounter_proportion':[.1,.2],
                       'emergency_count':[1,2],'encounter_count':[10,10]})
    assert list(painel.emergencia(ages).data[0].y)==['0-17','65+']


def test_no_business_aggregations_in_presentation():
    banned={'sum','mean','groupby','merge','pivot','pivot_table','agg','aggregate','histogram','pie','connect'}
    for module in (painel,app):
        tree=ast.parse(Path(module.__file__).read_text())
        calls=[n.func for n in ast.walk(tree) if isinstance(n,ast.Call)]
        names={f.attr if isinstance(f,ast.Attribute) else f.id for f in calls if isinstance(f,(ast.Attribute,ast.Name))}
        # connect é permitido exclusivamente em ler, para leitura DuckDB.
        assert not names & (banned-{'connect'})
    tree=ast.parse(Path(painel.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef) and node.name!='ler':
            assert not any(isinstance(n,ast.Attribute) and n.attr=='execute' for n in ast.walk(node))


def test_streamlit_cards_filter_and_reload(frames,monkeypatch,interface_graphs):
    st.cache_data.clear()
    frames['encounters_by_year_class'] = pd.DataFrame({
        'year': [1990, 2000, 2020], 'encounter_class': ['ambulatory'] * 3,
        'encounter_count': [1, 2, 3]})
    read=Mock(return_value=frames)
    monkeypatch.setattr(painel,'ler',read)
    plot=Mock(wraps=painel.evolucao)
    monkeypatch.setattr(painel,'evolucao',plot)
    at=AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=10).run(timeout=10)
    assert plot.call_args.args[0]['year'].tolist()==[2000,2020]
    assert not at.exception
    assert len(at.metric)==6
    assert at.metric[0].value=='1'
    assert at.metric[1].value=='1'
    assert len(at.get('plotly_chart'))==6
    original=[m.value for m in at.metric]
    other_specs=[p.proto.spec for p in at.get('plotly_chart')[1:]]
    assert at.slider[0].value == (2000, 2020)
    at.slider[0].set_value((1990, 2020)).run()
    assert [m.value for m in at.metric]==original
    assert len(at.get('plotly_chart'))==6
    assert at.slider[0].value == (1990, 2020)
    assert plot.call_args.args[0]['year'].tolist()==[1990,2000,2020]
    assert [p.proto.spec for p in at.get('plotly_chart')[1:]]==other_specs
    assert read.call_count==1
    at.button[0].click().run()
    assert read.call_count==2
    st.cache_data.clear()


@pytest.mark.parametrize('error',[FileNotFoundError('Banco não encontrado'),painel.TabelaMartsAusente('Tabela ausente: marts.emergency_by_age')])
def test_streamlit_stops_on_read_error(error,monkeypatch):
    st.cache_data.clear()
    monkeypatch.setattr(painel,'ler',Mock(side_effect=error))
    at=AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=10).run(timeout=10)
    assert not at.exception
    assert at.error[0].value==str(error)
    assert len(at.metric)==0
    assert 'pipeline-saude marts' in at.code[0].value
    st.cache_data.clear()


@pytest.mark.parametrize('years,expected', [
    ([1942,2001,2026],(1942,2026,(2000,2026))),
    ([2010,2026],(2010,2026,(2010,2026))),
    ([1942,1999],(1942,1999,(1942,1999))),
    ([2020],(2020,2020,(2020,2020))),
    ([],None),
])
def test_initial_interval_and_full_history(years,expected):
    frame=pd.DataFrame({'year':years})
    assert painel.intervalo_inicial(frame)==expected


def test_cost_lines_preserve_every_year_class_value():
    frame=pd.DataFrame({'year':[2021,2020,2020],
                        'encounter_class':['wellness','emergency','wellness'],
                        'total_claim_cost':[30.5,10.25,20.75]})
    before=frame.copy(deep=True)
    fig=painel.custos_atendimentos(frame)
    actual=[(trace.name,int(year),float(value)) for trace in fig.data for year,value in zip(trace.x,trace.y)]
    assert sorted(actual)==[('emergency',2020,10.25),('wellness',2020,20.75),('wellness',2021,30.5)]
    assert all(trace.type=='scatter' for trace in fig.data)
    assert fig.layout.hovermode=='x unified'
    assert fig.layout.legend.orientation=='h'
    assert painel.evolucao(pd.DataFrame({'year':[2020],'encounter_class':['wellness'],'encounter_count':[1]})).layout.title.text=='Evolução dos atendimentos'
    pd.testing.assert_frame_equal(frame,before)


@pytest.mark.parametrize('years', [[], [2020]])
def test_streamlit_empty_or_single_year(frames,monkeypatch,years,interface_graphs):
    st.cache_data.clear()
    frames['encounters_by_year_class']=pd.DataFrame({'year':years,
        'encounter_class':['ambulatory']*len(years),'encounter_count':[1]*len(years)})
    monkeypatch.setattr(painel,'ler',Mock(return_value=frames))
    at=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py', default_timeout=10).run(timeout=10)
    assert not at.exception
    assert len(at.metric)==6
    assert len(at.slider)==0
    st.cache_data.clear()


def test_independent_cost_and_encounter_intervals(frames,monkeypatch,interface_graphs):
    st.cache_data.clear()
    frames['encounters_by_year_class']=pd.DataFrame({
        'year':[1990,2000,2020], 'encounter_class':['ambulatory']*3,
        'encounter_count':[1,2,3]})
    frames['encounter_costs_by_year_class']=pd.DataFrame({
        'year':[1980,2000,2025], 'encounter_class':['ambulatory']*3,
        'total_claim_cost':[10.25,20.75,30.5]})
    before=frames['encounter_costs_by_year_class'].copy(deep=True)
    monkeypatch.setattr(painel,'ler',Mock(return_value=frames))
    evolution=Mock(wraps=painel.evolucao)
    costs=Mock(wraps=painel.custos_atendimentos)
    monkeypatch.setattr(painel,'evolucao',evolution)
    monkeypatch.setattr(painel,'custos_atendimentos',costs)
    at=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py', default_timeout=10).run(timeout=10)
    assert not at.exception
    assert at.slider(key='anos_evolucao').value==(2000,2020)
    assert at.slider(key='anos_custos').value==(2000,2025)
    assert costs.call_args.args[0]['total_claim_cost'].tolist()==[20.75,30.5]
    assert 'Evolução dos atendimentos' in [s.value for s in at.subheader]
    assert evolution.call_args.args[0]['year'].tolist()==[2000,2020]
    metrics=[m.value for m in at.metric]
    charts=[c.proto.spec for c in at.get('plotly_chart')]
    at.slider(key='anos_custos').set_value((1980,2000)).run()
    assert not at.exception
    assert costs.call_args.args[0]['total_claim_cost'].tolist()==[10.25,20.75]
    assert at.slider(key='anos_evolucao').value==(2000,2020)
    assert [m.value for m in at.metric]==metrics
    assert [c.proto.spec for i,c in enumerate(at.get('plotly_chart')) if i!=2]==[c for i,c in enumerate(charts) if i!=2]
    cost_chart=at.get('plotly_chart')[2].proto.spec
    at.slider(key='anos_evolucao').set_value((1990,2020)).run()
    assert not at.exception
    assert evolution.call_args.args[0]['year'].tolist()==[1990,2000,2020]
    assert at.slider(key='anos_custos').value==(1980,2000)
    assert at.get('plotly_chart')[2].proto.spec==cost_chart
    assert [m.value for m in at.metric]==metrics
    pd.testing.assert_frame_equal(frames['encounter_costs_by_year_class'],before)
    st.cache_data.clear()


@pytest.mark.parametrize('years',[[],[2020]])
def test_cost_filter_empty_or_single_year(frames,monkeypatch,years,interface_graphs):
    st.cache_data.clear()
    frames['encounter_costs_by_year_class']=pd.DataFrame({
        'year':years,'encounter_class':['ambulatory']*len(years),
        'total_claim_cost':[10.25]*len(years)})
    monkeypatch.setattr(painel,'ler',Mock(return_value=frames))
    at=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py', default_timeout=10).run(timeout=10)
    assert not at.exception
    assert len(at.metric)==6
    assert len(at.slider)==0
    st.cache_data.clear()
