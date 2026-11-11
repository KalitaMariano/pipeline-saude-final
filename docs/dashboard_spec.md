# Dashboard — etapa 6

Implementação aprovada: Streamlit e Plotly Express em `app.py` e `painel.py`,
na raiz. Sem novo pipeline ou banco. `src/pipeline_saude/config.py` centraliza
DATABASE_PATH = artifacts/saude.duckdb, utilizado pelos padrões dos três comandos
e pelo painel. Execute na raiz; --database continua disponível na CLI. Se usar
esse argumento para outro caminho, ajuste a configuração compartilhada para o
painel consumir o mesmo banco. O dashboard nunca cria banco inexistente.

## Auditoria e extensões autorizadas

Antes de implementar, foram lidos README, contrato, SQLs e DESCRIBE das cinco
MARTS existentes por conexão somente leitura. Os seis totais globais não estavam
materializados; patient_count por faixa não pode ser somado para contar pacientes
globais. Também faltava participação por código no custo de medicamentos.
O usuário aprovou as duas extensões SQL e a leitura da sexta tabela.

`marts.dashboard_kpis` tem exatamente uma linha para todo o histórico:

| Coluna | Tipo DuckDB | Definição |
| --- | --- | --- |
| patient_count | BIGINT | Pacientes distintos com atendimento clínico elegível |
| encounter_count | BIGINT | Atendimentos clínicos elegíveis |
| encounters_with_medications | BIGINT | Atendimentos com ao menos um medicamento elegível |
| medication_encounter_proportion | DOUBLE | Com medicamentos / atendimentos clínicos |
| total_claim_cost | DECIMAL(38,2) | Soma de TOTAL_CLAIM_COST financeiro válido |
| medication_total_cost | DECIMAL(38,2) | Soma de TOTALCOST financeiro válido |

Contagens em base vazia são zero; proporção sem denominador e somas sem valores
válidos são NULL. O JOIN usa atendimentos distintos com medicamentos; os custos
das duas entidades são agregados separadamente, sem multiplicação.

`marts.medication_costs_by_code` recebeu `medication_cost_proportion DOUBLE`:
custo válido do código / soma do custo válido de todos os códigos, por janela
SQL. Denominador zero retorna NULL; códigos sem custo válido têm NULL. Não há
mistura com custos de atendimentos ou renormalização dos dez códigos exibidos.

Os demais nomes/tipos e granularidades permanecem os auditados no contrato
MARTS. RAW, REFINED, flags e regras de elegibilidade não foram alterados.

## Leitura e interface

`painel.ler()` retorna seis DataFrames, com as chaves iguais aos nomes das tabelas.
Cada consulta é exclusivamente SELECT * FROM marts.nome_da_tabela. Uma conexão
DuckDB read_only=True é aberta e fechada em finally, inclusive quando falta tabela.
Não há introspecção adicional por SQL. Falta de tabela gera erro que identifica
schema e tabela; banco inexistente não é criado.

`app.carregar_dados` usa st.cache_data apenas para DataFrames. Recarregar dados
limpa o cache dessa função antes de ler novamente. Não há conexão global nem
conexão em cache. Banco inexistente ou tabela ausente gera orientação para as três
camadas e st.stop(); banco temporariamente indisponível gera mensagem de erro.
O cache pode mostrar o snapshot anterior até clicar no botão; o painel não
reprocessa camadas. Uma leitura curta ainda pode coincidir com uma escrita ativa:
aguarde o pipeline concluir e recarregue. A conexão não fica aberta entre reruns.

Layout wide, título e subtítulo especificados; seis cartões na ordem aprovada,
um gráfico de evolução, três gráficos na faixa seguinte e dois na última.
Há dois filtros de intervalo independentes (ano inicial e final inclusivos):
um seleciona linhas da evolução, outro seleciona linhas de custos por ano/classe.
Cada filtro atua exclusivamente no seu gráfico, sem agregação ou recálculo.
Abre de 2000 até o último ano disponível e permite selecionar
todo o histórico. Se a base começar depois de 2000 ou terminar antes dele, abre
no período disponível. Base vazia mostra mensagem; base com um único ano não
exibe controle de intervalo. Os outros quatro gráficos e os seis cartões
permanecem com todo o histórico, acompanhado da mensagem solicitada pela SPEC.

Gráficos, sem agregações Python:

- Linhas de atendimentos ordenadas por ano dentro de cada classe.
- Emergência por faixa: emergency_count / encounter_count, valor já calculado no
  SQL; tooltip explicita numerador e denominador. Ordem 0–17, 18–44, 45–64, 65+.
- Custos por ano e classe com linhas e marcadores, mais espaço na faixa central,
  legenda horizontal abaixo e hover unificado por ano, sem consolidar períodos.
- Top 10 códigos por medication_total_cost, barras horizontais, maior no topo;
  empate ordenado pelo código textual, preservando zeros iniciais.
- Proporção de associação por classe e faixa; tooltip com numerador/denominador.
- Participação no custo de todos os medicamentos dos mesmos dez códigos de maior
  custo. Barra percentual usa a coluna SQL, sem somar outros códigos ou criar
  categoria Outros. Escolha de top 10 é seleção visual permitida na SPEC.

Cores consistentes, template branco, unidades nos eixos. `numero`, `pct` e
`monetario` são funções puras sem Streamlit e independentes do locale. Separadores
brasileiros, NULL/NaN exibidos como travessão; pct só converte fração para exibição.
Sem prefixo de moeda: valores são custo registrado. Não há groupby, sum, mean,
merge, pivot ou agregações de negócio em app.py/painel.py. Barras representam
as linhas agregadas da MARTS; não são histogramas ou setores renormalizados.

## Operação e testes

```bash
uv sync --locked
uv run pipeline-saude marts
uv run streamlit run app.py
uv run pytest -q
```

RAW/REFINED precisam existir; em instalação nova, execute as três camadas conforme
README. Após atualizar MARTS, clique em Recarregar dados. O wheel inclui os dois
módulos da raiz e os SQLs; o comando Streamlit acima é executado no checkout.

Testes fictícios em tests/test_painel.py: formatação, leitura de seis tabelas,
consulta exata, conexão somente leitura e fechamento no sucesso/erro, banco
inexistente, configuração padrão, figuras pequenas/vazias, ordenação/top 10,
filtro, ausência de agregações por inspeção AST, seis cartões, cache, botão e
interrupção da página com erro. As tabelas usadas na leitura são criadas em
arquivo temporário por pytest a partir de dados fictícios em memória; não usam
banco ou CSV do projeto. Tests/test_marts.py verifica KPIs, pacientes distintos,
prevenção de multiplicação e participações SQL, inclusive denominadores zero.

## Validação final — 10/11/2026

**64 testes aprovados em 50,99 s**: 39 casos anteriores, dois casos novos dos
agregados SQL e 23 casos do painel/interface. Asserções de bases vazias anteriores
foram ajustadas apenas para reconhecer que dashboard_kpis mantém uma linha global;
os indicadores antigos continuam vazios quando não há população elegível.

Contagens locais das seis MARTS: 245 / 4 / 245 / 146 / 37 / 1. KPIs:
108 pacientes, 5.563 atendimentos clínicos, 2.225 com medicamentos, fração
0,3999640481754449, custo de atendimentos 16.804.458,34 e custo de medicamentos
11.498.345,15. A interface apresenta 40,0% após formatação a uma casa decimal.
39.152 dispensações confirmadas; participação dos códigos soma 1 em tolerância
numérica. Duas execuções produziram conteúdo idêntico, com contagens/fingerprints
RAW e REFINED preservados.

AppTest separado com dados locais confirmou seis cartões e seis gráficos sem
exceções. Servidor Streamlit iniciado em localhost:8501, endpoint de saúde ok.
Essa validação real é separada dos testes fictícios. Sem inspeção visual manual
em navegador; a renderização foi conferida pela API de testes do Streamlit.
Sdist e wheel construídos com sucesso em /tmp. git diff --check sem erros.

## Revisão de apresentação antes da publicação

Título exato do gráfico: Evolução dos atendimentos. O código auditado já usava
atendimentos, sem ocorrência de prestadores; a revisão padroniza o título pedido.
Filtro de intervalo substitui as etiquetas do multiselect. Custos preservam cada
valor de ano/classe, com eixo numérico legível, tooltip com duas casas decimais
e painel central mais largo. Nenhuma alteração SQL ou nos dados nesta revisão.

A inclusão de descrição foi aprovada em revisão posterior. `medication_description`
(VARCHAR) é calculada exclusivamente no SQL de medication_costs_by_code, usando
`string_agg(DISTINCT DESCRIPTION, ' | ' ORDER BY DESCRIPTION)` sobre
marts_medications, que preserva DESCRIPTION da REFINED. Há uma linha por código;
valores nulos são ignorados e, se todas as descrições forem nulas, o resultado é
NULL. Não há trim, tradução ou escolha arbitrária de nome. Múltiplas descrições
são preservadas em ordem determinística. Os dois gráficos de medicamentos exibem
a descrição no tooltip e mantêm o código textual no eixo. Não se modifica o
ranking, custos, contagens, dispensações ou participações. O painel deve ser
recarregado após a atualização MARTS para descartar DataFrames antigos em cache.

Validação desta revisão: **72 testes aprovados em 42,75 s**, incluindo oito
casos novos de intervalo/legibilidade. O teste de interface confirma a abertura
em 2000, expansão para todo o histórico e igualdade dos seis cartões e das
especificações dos outros cinco gráficos antes/depois do filtro. Custos mantêm
os valores originais por ano/classe. git diff --check passou.

Validação após incluir medication_description: **74 testes aprovados em 44,42 s**.
Os tooltips de custo e participação usam a descrição SQL correspondente a cada
código; o top 10 mantém sua ordenação e os percentuais não são recalculados.

## Intervalo independente dos custos — revisão final

Controle de custos com chave anos_custos, sem compartilhar estado com
anos_evolucao. Ambos abrem em 2000 até o último ano disponível na respectiva
MARTS; bases fora desse período usam seu histórico disponível. Usa as mesmas
funções puras de limites e seleção inclusiva de linhas. Sem banco ou SQL novo,
sem modificação de indicadores, elegibilidade, contagens ou custos. O título
Evolução dos atendimentos está confirmado tanto no subtítulo quanto na figura;
não há texto prestadores nos módulos do dashboard.

Testes fictícios alteram o filtro de custos e conferem cartões, evolução e os
outros quatro gráficos idênticos; depois alteram evolução e conferem custos e
intervalo preservados. Valores são comparados aos registros originais da MARTS,
sem somas. Cobertos também custos vazios e com apenas um ano disponível.

Validação final dos filtros independentes: **77 testes aprovados em 77,00 s**.
AppTest com dados locais confirmou seis cartões/seis gráficos e ambos os
intervalos inicialmente em 2000–2026. Nenhuma escrita no banco nesta revisão.
