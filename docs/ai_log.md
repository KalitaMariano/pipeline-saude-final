# Registro de uso da IA

## 10/11/2026 — diagnóstico e etapa 1

**Solicitação:** analisar três CSVs sem alterá-los e, após aprovação da
arquitetura, preparar somente a estrutura inicial do projeto.

**Contribuição da IA:** leitura e perfil dos CSVs, verificação de chaves e
relacionamentos, propostas de indicadores e arquitetura; preparação da
configuração e documentação da etapa 1. Os resultados locais foram usados como
evidência; origem exata, versão e licença dos arquivos não foram verificadas.

**Limites de aprovação:** o usuário aprovou a stack e as três camadas. As regras
analíticas propostas no diagnóstico continuam pendentes, conforme
`decisions.md`. Não houve implementação de pipeline ou testes.

**Erros e correções:** nenhum erro de implementação identificado nesta etapa.
No diagnóstico, a suspeita de erro em sete atendimentos após o óbito foi
refinada ao verificar que todos têm descrição `Death Certification`; os
registros não foram classificados automaticamente como inválidos. Esse exemplo
deve orientar a revisão de hipóteses com evidência antes de aplicar limpeza.

**Limitação do ambiente:** o comando `git status --short` retornou
`fatal: not a git repository (or any of the parent directories): .git`.
O diretório `.git` está vazio e disponível somente para leitura. Os arquivos
foram preparados no diretório de trabalho; não foram adicionados ao índice,
commitados ou enviados a um remoto.

## 10/11/2026 — etapa 2: RAW

**Solicitação e escopo:** implementar somente ingestão dos três CSVs como texto,
com rastreabilidade, reexecução sem acúmulo, comandos e validação. Não implementar
refined, marts ou dashboard; não alterar nem versionar os CSVs; não fazer commit
ou push.

**Decisões concretizadas:** snapshot integral em uma transação; campos originais
`VARCHAR`, vazios preservados como `''`; metadados de arquivo, hash SHA-256,
posição, instante UTC e lote. Leitura dos bytes uma vez, antes da carga, para
que hash e conteúdo importado correspondam. Inserções parametrizadas em lotes
de até 500 registros. Contrato e critérios em `raw_spec.md`.

**Limitações do ambiente:** `uv sync` falhou por erro de DNS ao acessar o PyPI.
A tentativa de gerar lockfile offline também não conseguiu resolver as
dependências completas. Foi usado um cache copiado para `/tmp`, sem modificar
o cache original, para instalar DuckDB 1.5.6 no ambiente local do projeto.
A sincronização completa, o entry point instalado e o lockfile ainda precisam
de validação com acesso ao registro; a ingestão foi executada pela CLI como
módulo Python.

**Erro de validação e correção:** a primeira verificação tentou obter uma coluna
`TIMESTAMPTZ` diretamente como datetime Python e falhou porque `pytz` não estava
instalado no ambiente mínimo. A carga havia concluído. A conferência foi
ajustada para comparar `epoch(_ingested_at)` com o instante UTC do relatório,
sem alterar o tipo armazenado nem acrescentar dependência ao pipeline.

**Validação:** comparação integral das células com os CSVs, duas execuções,
conferência de tipos, cabeçalhos e metadados, hashes antes/depois e cenários
fictícios de preservação e falha transacional. Resultados em
`raw_validation.md`. O script pontual ficou em `/tmp`; nenhuma suíte de testes
foi adicionada nesta etapa.

**Git:** o repositório agora está disponível e contém o commit `3ffc687` da
estrutura inicial. Os dados e o banco permanecem ignorados. A IA não realizou
staging, commit ou push.

## 10/11/2026 — etapa 3: REFINED

**Autorização e escopo:** transformação das três tabelas RAW para REFINED,
tipagem, nulos, identificação técnica dos medicamentos, sinalização de qualidade,
recarga e testes unitários com dados fictícios em memória. Não implementar
marts nem dashboard; preservar CSVs e não fazer commit ou push.

**Decisões da IA para revisão:** contrato em `refined_spec.md`, com moedas
DECIMAL(18,2), inteiros BIGINT, timestamps com fuso explícito, vazios como nulos,
sem trim. Valores incompatíveis abortam toda a transação. Identificador de
medicamentos deriva da origem, sem deduplicação clínica. Verificações por EXISTS
evitam multiplicar linhas em relacionamentos com pais duplicados. Alertas
ficam em uma lista por registro, sem remover registros administrativos ou
medicamentos de duração zero. Decisões e pendências em `decisions.md`.

**Validações:** 17 testes pytest com conexão exclusivamente em memória e dados
fictícios; nenhuma leitura de CSV real ou banco persistido pelos testes. Na
validação local separada, duas execuções mantiveram contagens, conteúdo tipado,
identificadores e flags. Comparação da RAW e hashes dos CSVs confirmou que não
foram alterados. Resultados completos em `refined_validation.md`.

**Erros e correções:** nenhum teste falhou nesta etapa. Na revisão dos testes,
uma asserção que consultava o próprio ID como valor esperado foi substituída
por verificações independentes de contagem, valor monetário e mudança do ID
quando o hash da origem muda. Um patch da documentação falhou por contexto
inexato; o contexto foi conferido e o patch reaplicado. Nenhum registro foi
corrigido ou descartado.

**Ambiente:** pytest 9.1.1 e dependências instalados do cache em `/tmp`; DuckDB
1.5.6 já disponível. Comandos executados pelo módulo Python e pelo pytest do
ambiente local. A pendência de sincronização completa e lockfile da etapa RAW
permanece registrada. Script de validação real em `/tmp`, relatório JSON em
`artifacts/`, ambos fora do conjunto de arquivos versionáveis do projeto.

**Entrega:** somente arquivos da REFINED, CLI, testes e documentação/configuração
relacionados. Nenhum staging, commit ou push. Licença dos CSVs ainda pendente;
dados e bancos continuam ignorados pelo Git.

## 10/11/2026 — etapa 4: MARTS

**Escopo:** cinco indicadores, SQL separado, comando CLI, materialização atômica,
testes fictícios em memória, validação real e documentação. Sem dashboard,
staging, commit ou push.

**Escolhas:** os documentos anteriores não fixavam fórmulas ou exclusões.
A IA concretizou e documentou as regras em marts_spec.md e decisions.md:
idade completa em UTC, faixas, populações por finalidade, exclusão administrativa
de Death Certification, chaves únicas antes dos JOINs e separação dos custos.
Alertas geográficos e financeiros não removem indiscriminadamente utilização.

**Validação:** 38 testes passaram (21 casos MARTS e 17 REFINED). Na base local,
5.563 atendimentos e 3.785 medicamentos elegíveis; oito registros administrativos
e 65 medicamentos iniciados após o atendimento ficaram fora da análise.
Duas execuções comparadas integralmente; RAW/REFINED com contagens e fingerprints
inalterados; custos reconciliados com as bases elegíveis. Resultados em
marts_validation.md. Nenhum teste unitário usa o banco real.

**Erro e correção:** o script pontual de validação tentou `row(t.*)` dentro de
hash, expansão não aceita pelo DuckDB. Ajustado para `hash(t)` e reexecutado com
sucesso. Não houve falha nos testes ou alteração dos dados de origem.

**Limitações:** procedência, licença, moeda e escopo financeiro continuam sem
confirmação externa. Não houve consulta externa; esta etapa implementa o contrato
local. Ambiente e lockfile mantêm as pendências anteriores.

## 10/11/2026 — revisão aprovada das regras MARTS

**Autorização:** manter os oito Death Certification fora da população clínica;
incluir os 65 medicamentos com início posterior ao atendimento nos indicadores
4 e 5; preservar RAW, REFINED e flags; atualizar SQL, testes e documentação.

**Correção:** removido somente o limite superior de início do medicamento na
base compartilhada dos indicadores 4 e 5. O limite inferior e os demais critérios
continuam iguais. O vínculo ENCOUNTER/PATIENT não exige início até o término do
atendimento. A exclusão anterior era excessiva para as perguntas aprovadas.

**Testes:** 39 aprovados (22 MARTS e 17 REFINED), em 24,25 s. Novo teste gera a
flag start_after_encounter pela transformação REFINED a partir de origem fictícia
e confirma inclusão em custos/dispensações e associação, sem alteração da flag
ou dos dados e sem multiplicar custos de atendimento.

**Dados locais:** 5.563 atendimentos clínicos; 3.850 medicamentos; 146 códigos;
39.152 dispensações; custos de medicamentos de 11.498.345,15; 2.225 atendimentos
com medicamentos. Duas execuções iguais, totais reconciliados e contagens e
fingerprints de RAW/REFINED inalterados, incluindo os 65 alertas temporais.
Relatório atualizado em artifacts/marts_validation.json (ignorado).

**Entrega:** oito arquivos de SQL/teste/documentação ajustados nesta revisão;
nenhuma alteração no código ou nos dados RAW/REFINED, sem commit ou push.

## 10/11/2026 — etapa 5: revisão final e reprodutibilidade

**Escopo:** resolver uv sync e lockfile, validar instalação do zero e entry points,
revisar testes e documentação, conferir origem/licença e falhas da revisão MARTS.
Sem alteração de regras analíticas, dados de origem ou banco original.

**Dependências:** reproduzida falha DNS no sandbox; acesso ao PyPI autorizado
resolveu instalação. Primeira resolução selecionou pytest 9.2.0; corrigida para
preservar pytest 9.1.1. DuckDB 1.5.6 mantido; faixas de dependências inalteradas.
uv.lock gerado. Removido pythonpath do pytest para testar instalação normal.

**Validação:** cópia sem .venv, cache, CSVs ou banco; sync com cache novo e rede;
39 testes aprovados sem PYTHONPATH. Três camadas pelo entry point criaram banco
novo em /tmp a partir dos CSVs locais, com totais históricos confirmados e hashes
dos CSVs inalterados. Sdist e wheel construídos; wheel instalado em outro ambiente
e executado fora do checkout. Pacote oficial latest também processado pelas três
camadas, com resultados diferentes, documentados em reproducibility.md.

**Fonte/licença:** domínio MITRE retornou timeout/502; consultadas FAQ, página
oficial alternativa e LICENSE do gerador. Registrada permissão de uso dos dados
sem confundir com Apache-2.0 do software. Pacote histórico exato não identificado;
solicitada informação ao usuário durante a revisão, sem presumir a resposta.

**Erros investigados:** reproduzidos row(t.*) e alias cost das consultas auxiliares
em /tmp; hash(t) e alias total_cost funcionaram. O status 1 final da etapa anterior
também pode ser identificado como rg sem correspondências após edição Python,
sem indicar falha do pipeline. Nesta etapa, uv venv inicialmente tentou usar cache
somente leitura: reexecutado com cache em /tmp. Instalação offline do wheel sem
metadados de resolução no cache falhou; instalação normal autorizada resolveu.
Nenhuma dessas falhas alterou regras analíticas ou exigiu dependência nova.

**Entrega:** README, configuração pytest, uv.lock e documentação da revisão.
Nenhum CSV, banco, cache ou build incluído. Sem staging, commit ou push.

## 10/11/2026 — etapa 6: dashboard Streamlit e Plotly

**Auditoria e autorização:** lidos README, contrato MARTS e SQLs; DESCRIBE das
cinco tabelas por conexão somente leitura. Identificada ausência de KPIs globais
e participação por código. A implementação foi interrompida para aprovação;
o usuário autorizou a sexta MARTS, a coluna percentual SQL e configuração comum.

**Implementação:** app.py e painel.py na raiz; seis consultas SELECT * exclusivas
a MARTS, read_only e fechamento em finally. Formatação brasileira sem locale ou
moeda presumida, gráficos Plotly Express sem agregação Python, filtro exclusivo
da evolução, cartões globais, cache de DataFrames, botão e erros com st.stop.
Nova MARTS global mantém uma linha inclusive para população vazia. Custos de
atendimento/medicamentos calculados separadamente; participação por código em SQL
com denominador de todos os códigos. Nenhuma regra analítica anterior alterada.

**Dependências:** Streamlit, Plotly e pandas declarados e lockfile atualizado,
com DuckDB 1.5.6 e pytest 9.1.1 preservados. Falha DNS do sandbox foi reproduzida;
sync com acesso autorizado resolveu. Versões instaladas: Streamlit 1.67.0,
Plotly 7.1.0 e pandas 2.3.3. Dois módulos da raiz incluídos no empacotamento.

**Correções durante os testes:** AppTest resolve caminhos relativos ao arquivo
de teste; caminho absoluto da raiz corrigiu três falhas iniciais. Depois, dois
testes de erro reutilizavam cache do teste anterior; isolamento ajustado com
st.cache_data.clear, confirmando que erros reais interrompem a página. Não houve
alteração de indicadores para contornar teste. Atualização do limite mínimo de
Streamlit para 1.50 cobre a API width utilizada na interface.

**Servidor:** criação de socket bloqueada no sandbox; execução autorizada fora
dele iniciou em 127.0.0.1:8501 e endpoint /_stcore/health retornou ok. Sdist e
wheel construídos em /tmp, sem incluir banco ou CSVs. Testes de leitura criam
bancos temporários exclusivamente fictícios, além da fixture em memória.

**Dados reais, validação separada:** duas recargas MARTS idênticas; fingerprints
RAW/REFINED iguais antes/depois. KPIs confirmados: 108 pacientes, 5.563 atendimentos,
2.225 associados, fração 0,3999640481754449, custos de atendimentos 16.804.458,34
e de medicamentos 11.498.345,15; 39.152 dispensações. Participações por código
somam 1 dentro da tolerância numérica. Nenhum alerta temporal foi removido.

**Resultado final:** 64 testes aprovados em 50,99 s (39 anteriores, dois SQL e
23 painel/interface). AppTest separado com dados locais mostrou seis cartões e
seis gráficos sem exceções. git diff --check passou. Sem inspeção visual manual
no navegador; validação de renderização pela API Streamlit. Nenhum staging,
commit ou push realizado. Dados, bancos e builds continuam ignorados.

## 10/11/2026 — revisão visual da etapa 6

**Solicitação:** trocar multiselect por intervalo, abrir evolução em 2000 até o
último ano, padronizar título, melhorar custos e auditar descrições de medicamentos.

**Alterações:** slider de ano inicial/final inclusivos, com acesso a todo o
histórico e tratamento de base vazia, ano único e históricos fora de 2000. Título
Evolução dos atendimentos. Custos por ano/classe passaram de barras para linhas
com marcadores, legenda horizontal, tooltip unificado e área central maior.
Seis cartões e demais gráficos preservados; sem agregações Python ou alteração SQL.

**Auditoria:** DESCRIBE confirmou ausência de descrições na MARTS. DESCRIPTION
existe na REFINED; dois códigos locais têm descrições múltiplas. Proposta de
string_agg DISTINCT ordenada por código apresentada para aprovação, sem aplicar
mudança à MARTS ou aos dados.

**Correção na validação:** a primeira execução de pytest importou módulos da raiz
copiados para site-packages pelo force-include do wheel, ainda na versão anterior.
Reexecutado uv sync --locked --offline --reinstall-package pipeline-saude;
nenhuma dependência ou regra mudou. Os testes agora verificam o intervalo padrão,
consulta histórica, preservação dos cartões/outros gráficos e valores por ano/classe.

**Resultado:** 72 testes aprovados em 42,75 s, incluindo os 39 originais.
git diff --check sem erros. Arquivos ajustados nesta revisão: app.py, painel.py,
tests/test_painel.py, README.md, docs/dashboard_spec.md e docs/ai_log.md.
Nenhuma MARTS modificada nesta revisão; sem commit ou push.

## 10/11/2026 — descrições de medicamentos aprovadas

**Autorização:** incluir medication_description exclusivamente por SQL, mantendo
uma linha por código, descrições distintas em ordem determinística e todos os
indicadores existentes; usar o campo nos tooltips, sem agregações Python.

**Implementação:** string_agg(DISTINCT DESCRIPTION, ' | ' ORDER BY DESCRIPTION)
na agregação existente de marts_medications. DESCRIPTION é preservada da REFINED;
nulos não geram rótulos inventados, todas nulas resultam NULL. Os dois gráficos
recebem o campo em custom_data e o exibem no tooltip, mantendo código no eixo.
Sem mudança de ranking, elegibilidade, custos ou percentuais.

**Testes:** acrescentados cenários fictícios com descrições duplicadas,
múltiplas e nulas; reordenação da origem confirma estabilidade. Os testes dos
gráficos conferem correspondência entre código e descrição no top 10, tooltip
e participação preservada. Reinstalado somente o pacote local para atualizar
as cópias dos módulos da raiz utilizadas pelo pytest; dependências inalteradas.

**Validação real separada:** todas as colunas anteriores do indicador por código
comparadas integralmente antes/depois, além das outras cinco MARTS. Totais
confirmados: 146 códigos, 3.850 registros, 39.152 dispensações, custo 11.498.345,15
e cobertura 267.940,02; participações totalizam 1 dentro da tolerância numérica.
Duas execuções iguais; contagens/fingerprints RAW/REFINED inalterados. Nenhuma
escolha arbitrária entre as variantes dos dois códigos com descrições múltiplas.

**Resultado final:** 74 testes aprovados em 44,42 s, incluindo todos os casos
anteriores. git diff --check passou. Nenhum commit ou push realizado.

## 10/11/2026 — intervalo independente dos custos

**Solicitação:** garantir título Evolução dos atendimentos e acrescentar filtro
próprio de custos por ano, padrão 2000 até o último disponível, sem recálculos.

**Implementação:** controle compartilhado de apresentação selecionar_intervalo
com chaves distintas anos_evolucao e anos_custos. Cada gráfico recebe somente as
linhas selecionadas da sua MARTS. Seis cartões, quatro gráficos não temporais,
consultas, indicadores, SQLs e regras de negócio preservados. O título solicitado
já constava no fonte e foi confirmado nos testes de figura e interface; nenhuma
ocorrência de prestadores nos módulos. Reinstalado o pacote local para atualizar
módulos copiados pelo empacotamento, sem mudar dependências.

**Validação:** testes novos verificam independência bidirecional dos filtros,
valores originais por ano/classe, igualdade dos cartões e figuras não afetadas,
bases vazias e ano único. Nenhum CSV ou banco real usado nos testes.

**Resultado:** 77 testes aprovados em 77,00 s. AppTest separado com dados locais
confirmou os dois filtros em 2000–2026, título correto, seis cartões e seis
gráficos sem exceções. git diff --check passou. Nenhuma escrita no banco ou
modificação SQL nesta revisão. Sem commit ou push.

## Auditoria de testes — cobertura e diagnóstico de duração

**Escopo:** medir src/pipeline_saude e painel.py, excluir app.py/testes/ambientes,
mínimo de 60%, completar cenários sem modificar produção, SQL ou regras.
pytest-cov 7.1.0 e coverage 7.17.2 já estavam declarados/instalados; lockfile e
versões preservados. Configuração de coverage adicionada ao pyproject.toml.

**Testes:** acrescentados RAW e CLI com CSVs inventados e DuckDB real temporário,
rollback RAW por dependência FK real, erros de entrada/schema e contrato REFINED.
Dois wrappers/mock de DuckDB substituídos por conexões reais. AST verifica consulta
exclusiva às MARTS. Todas as funções test_ possuem assert; sem skip/xfail/approx.

**Execuções e correção de rumo:** primeira medição de escopo teve 67,47%, com um
AppTest excedendo seu timeout de três segundos. Após complementar testes, uma
rodada limpa passou 105 casos e 98,97% em 169,01 s. A segunda rodada foi interrompida
quando o usuário pediu investigação de demora; não foi marcada como concluída.
A orientação de duas rodadas foi substituída por diagnóstico direcionado e uma
única execução final da suíte corrigida.

**Diagnóstico:** teste cache/recarga isolado com -vv, duração e faulthandler mostrou
10,20 s, stack em Plotly update_layout durante reconstrução das figuras. Importação
a frio de painel.py passou por pandas/Plotly, sem ler banco. Corrigida a separação
dos testes: AppTest usa figuras leves e registra as linhas/identidade, enquanto
os testes unitários continuam construindo e verificando as seis figuras reais.
Fixture inicialmente vazia provocou erro de dados vazios; um trace mínimo e uma
identidade por gráfico resolveram também os IDs duplicados. Nenhum código de
produção alterado para contornar os testes. Limites AppTest de dez segundos.

**Diagnóstico corrigido:** oito casos AppTest passaram em 14,00 s, cache/recarga
2,38 s e independência de intervalos 0,66 s. Execuções de diagnóstico limitadas
externamente a 60 s. Final única com limite de 180 s, -vv e durações, na cópia
em /tmp sem data/ ou artifacts/, usando ambiente instalado pelo lockfile.

**Resultado da execução final única:** 105 testes aprovados em 52,45 s, cobertura
98,97% (289/292). Teste cache/recarga 2,35 s; figura real de evolução 1,19 s;
filtros independentes 0,73 s. O mínimo de 60% foi aplicado normalmente.
Relatório por arquivo e três linhas não cobertas, com justificativas, em
docs/test_audit.md. A segunda rodada antiga foi interrompida, não contabilizada
como validação. Não se repetiu a suíte completa após o resultado final.
Produção/SQLs/dashboard conferidos por SHA-256, sem alterações nesta auditoria.
Nenhum commit ou push. Resultados gerados permanecem fora do conjunto versionável.
