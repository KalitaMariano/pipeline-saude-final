"""Interface Streamlit: apresenta valores materializados em MARTS."""
import duckdb
import streamlit as st

import painel


@st.cache_data(show_spinner='Lendo tabelas analíticas…')
def carregar_dados():
    return painel.ler()


def mostrar_grafico(frame, funcao):
    if frame.empty:
        st.info('Sem dados disponíveis para este gráfico.')
    else:
        st.plotly_chart(funcao(frame), width='stretch')


def selecionar_intervalo(frame, rotulo, chave):
    """Controla apenas as linhas exibidas por um gráfico, com estado independente."""
    limites = painel.intervalo_inicial(frame)
    if limites is None:
        return frame
    primeiro, ultimo, intervalo = limites
    if primeiro < ultimo:
        inicio, fim = st.slider(rotulo, min_value=primeiro, max_value=ultimo,
                               value=intervalo, step=1, format='%d', key=chave)
    else:
        inicio, fim = intervalo
        st.caption(f'Ano disponível: {primeiro}')
    return painel.filtrar_anos(frame, inicio, fim)


def main():
    st.set_page_config(page_title='Saúde | Visão Analítica', page_icon='🏥', layout='wide')
    st.title('Saúde | Visão Analítica')
    st.caption('Atendimentos, utilização e medicamentos — dados sintéticos Synthea.')
    st.info('Os indicadores gerais representam todo o histórico disponível.')
    if st.button('Recarregar dados'):
        carregar_dados.clear()
    try:
        dados = carregar_dados()
    except (FileNotFoundError, painel.TabelaMartsAusente) as error:
        st.error(str(error))
        st.code('uv run pipeline-saude raw\nuv run pipeline-saude refined\nuv run pipeline-saude marts', language='bash')
        st.stop()
    except duckdb.Error:
        st.error('Não foi possível ler o banco. Aguarde a execução do pipeline terminar e recarregue os dados.')
        st.stop()
    kpis = dados['dashboard_kpis']
    if len(kpis) != 1:
        st.error('marts.dashboard_kpis deve conter uma linha global. Execute a camada MARTS novamente.')
        st.stop()
    kpi = kpis.iloc[0]
    cards = [
        ('Pacientes distintos', 'patient_count', painel.numero),
        ('Atendimentos clínicos', 'encounter_count', painel.numero),
        ('Atendimentos com medicamentos associados', 'encounters_with_medications', painel.numero),
        ('Proporção de atendimentos com medicamentos', 'medication_encounter_proportion', painel.pct),
        ('Custo registrado dos atendimentos', 'total_claim_cost', painel.monetario),
        ('Custo registrado dos medicamentos', 'medication_total_cost', painel.monetario),
    ]
    for coluna, (titulo, campo, formato) in zip(st.columns(6), cards):
        coluna.metric(titulo, formato(kpi[campo]))
    st.caption('Pacientes distintos com atendimento clínico elegível. Custos apresentados sem atribuição de moeda.')
    st.subheader('Evolução dos atendimentos')
    frame = dados['encounters_by_year_class']
    evolucao = selecionar_intervalo(frame,
        'Ano inicial e final — somente evolução dos atendimentos', 'anos_evolucao')
    mostrar_grafico(evolucao, painel.evolucao)
    for coluna, tabela, funcao in zip(st.columns([1, 2, 1]),
            ['emergency_by_age', 'encounter_costs_by_year_class', 'medication_costs_by_code'],
            [painel.emergencia, painel.custos_atendimentos, painel.custos_medicamentos]):
        with coluna:
            frame = dados[tabela]
            if tabela == 'encounter_costs_by_year_class':
                frame = selecionar_intervalo(frame,
                    'Ano inicial e final — somente custos dos atendimentos', 'anos_custos')
            mostrar_grafico(frame, funcao)
    st.caption('Emergência: atendimentos emergency / todos os atendimentos da faixa. Custos de atendimentos exibidos por ano e classe, sem consolidar períodos.')
    for coluna, tabela, funcao in zip(st.columns(2),
            ['encounters_with_medications', 'medication_costs_by_code'],
            [painel.associacao, painel.participacao_medicamentos]):
        with coluna:
            mostrar_grafico(dados[tabela], funcao)
    st.caption('Associação: atendimentos com medicamentos / atendimentos clínicos do grupo. Participação: custo do código / custo de todos os medicamentos, calculada no SQL; o top 10 não altera o denominador.')
    with st.expander('Regras e limitações'):
        st.write('Idade completa no atendimento (UTC); faixas 0–17, 18–44, 45–64 e 65+. Death Certification fora da população clínica. Medicamentos iniciados após o término do atendimento mantêm o vínculo aprovado. Custos de medicamentos e atendimentos permanecem separados. Dados sintéticos: não representam a população real.')
        st.write('Após atualizar o banco pelo pipeline, clique em Recarregar dados. O cache guarda DataFrames; nenhuma conexão permanece aberta entre leituras.')


if __name__ == '__main__':
    main()
