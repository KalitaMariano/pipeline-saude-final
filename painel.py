"""Leitura somente MARTS e apresentação; nenhuma agregação de negócio."""
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px

from pipeline_saude import config
from pipeline_saude.marts.transform import TABLES

AGE_GROUPS = ['0-17', '18-44', '45-64', '65+']
COLORS = ['#087f8c', '#7656a5', '#d58936', '#3b6ea8', '#bd5668', '#508357']


class TabelaMartsAusente(RuntimeError):
    """Tabela necessária não está materializada."""


def ler(database=None):
    """Retorna seis DataFrames, fechando a conexão mesmo em caso de erro."""
    path = Path(database) if database is not None else config.DATABASE_PATH
    if not path.is_file():
        raise FileNotFoundError(f'Banco não encontrado: {path}')
    connection = duckdb.connect(str(path), read_only=True)
    try:
        frames = {}
        for table in TABLES:
            try:
                frames[table] = connection.execute(f'SELECT * FROM marts.{table}').fetchdf()
            except duckdb.CatalogException as error:
                raise TabelaMartsAusente(f'Tabela ausente: marts.{table}') from error
        return frames
    finally:
        connection.close()


def numero(valor, casas=0):
    if valor is None or pd.isna(valor):
        return '—'
    return f'{valor:,.{casas}f}'.translate(str.maketrans({',': '.', '.': ','}))


def pct(valor, casas=1):
    if valor is None or pd.isna(valor):
        return '—'
    return numero(valor * 100, casas) + '%'


def monetario(valor, casas=2):
    return numero(valor, casas)


def intervalo_inicial(frame):
    """Limites de apresentação; prioriza 2000 em históricos que incluem esse ano."""
    anos = sorted(frame['year'].dropna().unique().tolist())
    if not anos:
        return None
    primeiro, ultimo = int(anos[0]), int(anos[-1])
    inicio = 2000 if primeiro <= 2000 <= ultimo else primeiro
    return primeiro, ultimo, (inicio, ultimo)


def filtrar_anos(frame, inicio, fim):
    """Seleciona intervalo inclusivo de linhas, sem recalcular indicadores."""
    return frame.loc[frame['year'].between(inicio, fim)].copy()


def _estilo(fig, percentual=False):
    fig.update_layout(
        template='plotly_white', colorway=COLORS, separators=',.',
        font=dict(family='Arial, sans-serif', color='#263b4a'),
        margin=dict(l=12, r=12, t=70, b=35), height=390,
        legend_title_text='Classe', title_font_size=17,
    )
    if percentual:
        fig.update_xaxes(tickformat='.0%')
    return fig


def evolucao(frame):
    data = frame.sort_values(['encounter_class', 'year'])
    fig = px.line(data, x='year', y='encounter_count', color='encounter_class',
                  markers=True, title='Evolução dos atendimentos',
                  color_discrete_sequence=COLORS,
                  labels={'year': 'Ano (UTC)', 'encounter_count': 'Atendimentos clínicos',
                          'encounter_class': 'Classe'})
    fig.update_xaxes(tickformat='d')
    return _estilo(fig)


def emergencia(frame):
    data = frame.set_index('age_group').reindex(AGE_GROUPS).dropna(how='all').reset_index()
    fig = px.bar(data, x='emergency_encounter_proportion', y='age_group', orientation='h',
                 title='Emergência por faixa etária',
                 custom_data=['emergency_count', 'encounter_count'],
                 labels={'age_group': 'Faixa etária (anos)',
                         'emergency_encounter_proportion': 'Emergências / atendimentos da faixa'})
    fig.update_traces(marker_color=COLORS[0], hovertemplate=(
        '%{y} anos<br>Proporção: %{x:.1%}<br>Emergências: %{customdata[0]}'
        '<br>Atendimentos da faixa: %{customdata[1]}<extra></extra>'))
    fig.update_yaxes(categoryorder='array', categoryarray=AGE_GROUPS, autorange='reversed')
    return _estilo(fig, percentual=True)


def custos_atendimentos(frame):
    data = frame.sort_values(['encounter_class', 'year'])
    fig = px.line(data, x='year', y='total_claim_cost', color='encounter_class',
                  markers=True, title='Custos dos atendimentos por ano e classe',
                  color_discrete_sequence=COLORS,
                  labels={'year': 'Ano (UTC)', 'total_claim_cost': 'Custo registrado',
                          'encounter_class': 'Classe'})
    _estilo(fig)
    fig.update_traces(hovertemplate=(
        'Ano: %{x:.0f}<br>Custo registrado: %{y:,.2f}<extra>%{fullData.name}</extra>'))
    fig.update_xaxes(tickformat='d', nticks=8, showgrid=False)
    fig.update_yaxes(tickformat=',.0f', separatethousands=True, rangemode='tozero')
    fig.update_layout(height=460, hovermode='x unified',
                      legend=dict(orientation='h', yanchor='top', y=-0.25, x=0),
                      margin=dict(l=12, r=12, t=70, b=120))
    return fig


def _top_medicamentos(frame):
    return frame.sort_values(['medication_total_cost', 'medication_code'],
                             ascending=[False, True], na_position='last').head(10)


def custos_medicamentos(frame):
    data = _top_medicamentos(frame)
    fig = px.bar(data, x='medication_total_cost', y='medication_code', orientation='h',
                 title='Dez medicamentos de maior custo registrado',
                 custom_data=['medication_description'],
                 labels={'medication_total_cost': 'Custo registrado',
                         'medication_code': 'Código do medicamento'})
    fig.update_traces(marker_color=COLORS[0], hovertemplate=(
        'Código: %{y}<br>Descrição: %{customdata[0]}'
        '<br>Custo registrado: %{x:,.2f}<extra></extra>'))
    fig.update_yaxes(type='category', categoryorder='array',
                     categoryarray=data['medication_code'].tolist(), autorange='reversed')
    return _estilo(fig)


def associacao(frame):
    data = frame.sort_values(['encounter_class', 'age_group'])
    fig = px.bar(data, x='medication_encounter_proportion', y='encounter_class',
                 color='age_group', orientation='h', barmode='group',
                 category_orders={'age_group': AGE_GROUPS},
                 color_discrete_sequence=COLORS,
                 title='Atendimentos com medicamentos associados',
                 custom_data=['encounters_with_medications', 'encounter_count'],
                 labels={'medication_encounter_proportion': 'Proporção de atendimentos',
                         'encounter_class': 'Classe', 'age_group': 'Faixa etária (anos)'})
    fig.update_traces(hovertemplate=(
        '%{y}<br>Proporção: %{x:.1%}<br>Com medicamentos: %{customdata[0]}'
        '<br>Atendimentos do grupo: %{customdata[1]}<extra></extra>'))
    _estilo(fig, percentual=True)
    fig.update_layout(legend_title_text='Faixa etária (anos)')
    return fig


def participacao_medicamentos(frame):
    data = _top_medicamentos(frame)
    fig = px.bar(data, x='medication_cost_proportion', y='medication_code', orientation='h',
                 title='Participação no custo de todos os medicamentos — top 10',
                 custom_data=['medication_description'],
                 labels={'medication_cost_proportion': 'Participação no custo registrado de medicamentos',
                         'medication_code': 'Código do medicamento'})
    fig.update_traces(marker_color=COLORS[1], hovertemplate=(
        'Código: %{y}<br>Descrição: %{customdata[0]}'
        '<br>Participação: %{x:.1%}<extra></extra>'))
    fig.update_yaxes(type='category', categoryorder='array',
                     categoryarray=data['medication_code'].tolist(), autorange='reversed')
    return _estilo(fig, percentual=True)
