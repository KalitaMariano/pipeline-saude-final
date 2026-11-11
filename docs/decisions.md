# Decisões e pendências

Registro inicial: 10/11/2026. Uma proposta no diagnóstico não equivale a uma
decisão aprovada. Este documento distingue aprovação explícita, requisitos do
curso e escolhas iniciais de configuração sujeitas à revisão da etapa 1.

## Decisões aprovadas pelo usuário

| Decisão | Estado e consequência |
| --- | --- |
| Usar Python, uv, DuckDB e SQL | Aprovada; sem orquestrador conforme proposta aceita |
| Separar raw, refined e marts | Aprovada; implementação será realizada em etapas posteriores |
| Desenvolver por etapas, com um commit por etapa | Aprovada; revisar cada entrega antes do commit |
| Etapa 1: estrutura inicial | Preparada na etapa anterior; sem commit automático |
| Não versionar os CSVs antes de confirmar a licença | `data/` integralmente ignorado pelo Git |
| Não fazer commit nem push automaticamente | Aguardar aprovação do usuário |
| Etapa 2: implementar somente ingestão RAW | Autorizada na solicitação seguinte; validar conteúdo e recarga, sem refined, marts ou dashboard |
| Etapa 3: implementar somente REFINED e testes unitários | Autorizada; tipagem, rastreabilidade, qualidade e recarga, sem marts ou dashboard |

## Requisitos do curso registrados

- Preservar os dados originais na raw.
- Usar pelo menos duas tabelas relacionadas e realizar JOIN.
- Manter cada indicador em um arquivo SQL próprio.
- Criar testes unitários com pytest e dados fictícios, sem acessar o banco real.
- Documentar fonte, tabelas, arquitetura, indicadores e comandos no README.
- Preparar um repositório público com commits por etapa.
- Registrar decisões e erros da IA.

## Configuração proposta na etapa 1 — sujeita à revisão

- Layout `src/pipeline_saude`, com diretórios reservados para as três camadas.
- Python mínimo 3.12, compatível com o Python 3.12.3 observado no ambiente.
- Hatchling como backend de empacotamento.
- DuckDB como dependência de execução e pytest no grupo de desenvolvimento.
- Faixas de versões em `pyproject.toml`; versões exatas serão fixadas no
  `uv.lock` quando o ambiente for sincronizado. Na etapa 2, DuckDB 1.5.6 foi
  instalado do cache para validação; sincronização completa pendente.
- Bancos, artefatos, caches, ambientes virtuais e configurações locais ignorados.

## Questões pendentes

| Questão | Evidência ou motivo | Próximo encaminhamento |
| --- | --- | --- |
| Origem exata dos CSVs | Informados como Synthea; URL, pacote ou comando de geração não fornecidos | Registrar a procedência verificável |
| Versão e parâmetros do Synthea | Não disponíveis nos três CSVs analisados | Confirmar versão, data, população, filtros e parâmetros disponíveis |
| Licença dos dados e redistribuição | Ainda não confirmadas para estes arquivos | Validar licença e atribuições antes de adicionar dados ao Git |
| Licença do código do projeto | Não escolhida | Definir separadamente da licença dos dados antes da publicação |
| Organização e regras de marts | Contrato da etapa 4 em marts_spec.md | Revisar escolhas da entrega |
| Identidade clínica entre versões | A identidade técnica de medicamentos usa arquivo/hash/posição e muda com a versão do arquivo | Avaliar outra chave somente se houver necessidade de histórico entre versões |
| Tratamento analítico de ausências e anomalias | Filtros por finalidade documentados em marts_spec.md | Revisar entrega da etapa 4 |
| Registros administrativos | MARTS exclui oito Death Certification, sete após óbito | Exclusão administrativa aprovada na revisão da etapa 4 |
| Indicadores, faixas etárias e período | Cinco indicadores autorizados na etapa 4; fórmulas em marts_spec.md | Revisar concretização das regras |
| Semântica financeira e moeda | Custo total de medicamentos é custo base × dispensações em todas as linhas | Consultar a documentação da versão e evitar dupla contagem |
| Sincronização completa e lockfile | Resolvida na etapa 5 com acesso autorizado ao PyPI; uv.lock gerado | Versionar após aprovação desta entrega |

As cinco perguntas propostas abrangem evolução dos atendimentos, utilização de
emergência por idade, custos e cobertura por classe, concentração de custos de
medicamentos e proporção de atendimentos com medicamentos. Na etapa 4, os cinco indicadores foram autorizados e implementados; fórmulas
e filtros concretizados estão documentados em marts_spec.md para revisão.

## Decisões de implementação da RAW — etapa 2

O usuário autorizou a ingestão como texto, metadados, comandos e recarga sem
acúmulo. As escolhas abaixo concretizam esses requisitos e estão sujeitas à
revisão da entrega:

- Banco padrão `artifacts/saude.duckdb`; somente schema `raw` nesta etapa.
- Substituição integral das três tabelas em uma transação: snapshot atual,
  sem histórico de versões e sem exclusão de duplicatas presentes na origem.
- Todas as colunas originais `VARCHAR`, incluindo campos vazios como `''`.
- Metadados com arquivo, hash SHA-256 dos bytes importados, posição do registro,
  instante UTC e UUID de lote comum à carga. Metadados têm tipos próprios.
- Leitura dos três arquivos em memória antes de abrir o banco, adequada aos
  9.529 registros atuais. Falhas de formato interrompem a carga inteira.
- Nenhum tratamento clínico, financeiro ou geográfico nesta camada.
- Validação pontual dos arquivos reais e de cenários fictícios em ambiente
  temporário; a suíte pytest ficará para sua etapa específica.

Na etapa 2, o Git já reconhece o repositório e o commit da estrutura inicial
(`3ffc687`). A limitação de metadados Git registrada na etapa 1 está resolvida.
Nenhum staging, commit ou push foi realizado pela IA nesta etapa.

## Decisões de implementação REFINED — etapa 3

O usuário autorizou conversões de tipo, preservação de linhas e nulos legítimos,
identificação técnica de medicamentos, verificações de qualidade, recarga,
testes em memória e validação das contagens reais. Escolhas concretizadas no
contrato `refined_spec.md`, para revisão desta entrega:

- Schema `refined` no mesmo banco; transformação consome exclusivamente RAW.
- Substituição integral das três tabelas em uma transação. Contagens devem
  corresponder à RAW; os números do dataset não ficam fixos no código.
- String vazia vira `NULL`; textos com espaços não são limpos automaticamente.
  Identificadores, documentos, códigos clínicos, FIPS e CEP permanecem textos.
- Datas `DATE`; timestamps com fuso explícito `TIMESTAMPTZ`, com comparações de
  datas em UTC; moedas `DECIMAL(18,2)`; renda e dispensações `BIGINT`;
  coordenadas `DOUBLE` finito. Valores incompatíveis abortam com rollback,
  inclusive quando o cast poderia arredondar silenciosamente.
- Linhagem RAW preservada e `_refined_at` acrescentado. `_medication_id` é
  SHA-256 da lista JSON de arquivo/hash/posição; estável para a mesma origem,
  distinto entre posições, sem pretensão de identidade clínica entre versões.
- `_quality_flags` é uma lista por registro. Chaves ausentes/repetidas,
  relacionamentos e anomalias são sinalizados sem rejeitar as linhas.
  Linhagem de medicamento ambígua aborta, pois inviabiliza sua identificação.
- `Death Certification` é mantido e sinalizado temporalmente; término nulo de
  medicamento e motivo completamente ausente não são classificados como erro.
- Nenhuma normalização de descrições, remoção de outliers ou interpretação
  financeira adicional. Nenhum objeto de marts criado.
- Testes pytest exclusivamente com dados fictícios e DuckDB em memória.
  Validação local separada confirmou as contagens e a recarga das três tabelas.

A instalação de pytest 9.1.1 usou cache local. Sincronização completa e lockfile
permanecem pendentes; não houve nova consulta à origem ou à licença dos dados.

## Decisões de implementação MARTS — etapa 4

O usuário autorizou os cinco indicadores, testes em memória, SQL separado,
validação local e documentação. Dashboard, commit e push não foram autorizados.
Contrato: [marts_spec.md](marts_spec.md); evidências: [marts_validation.md](marts_validation.md).

- Cinco tabelas substituídas atomicamente no schema marts; REFINED preservada.
- Faixas 0–17, 18–44, 45–64, 65+, idade completa no início em UTC; todos os anos.
- Excluir chaves ambíguas e vínculos/datas inválidos da população clínica;
  excluir Death Certification pela descrição exata, mesmo sem flag temporal.
- Qualidade financeira afeta apenas somas e denominadores financeiros; não
  excluir por geografia ou ausência de motivo. Medicamentos de duração zero
  e término ausente são aceitos, sem inferir uso atual.
- Emergência / atendimentos observados na faixa; associação / atendimentos
  elegíveis do grupo. Nenhuma taxa populacional ou inferência causal.
- Base única de atendimentos e medicamentos agregados/deduplicados por vínculo
  antes do JOIN de associação impedem multiplicação. Nenhuma deduplicação clínica.
- Custos de atendimentos e medicamentos separados; moeda e escopo financeiro
  da origem permanecem pendentes. TOTALCOST não é multiplicado novamente.

São escolhas explícitas de implementação para revisão, não alegações de aprovação
prévia de fórmulas que os documentos anteriores ainda deixavam pendentes.

## Revisão aprovada das exclusões MARTS — etapa 4

O usuário aprovou manter os oito Death Certification fora da população de
atendimentos clínicos (indicadores 1, 2, 3 e denominador do 5). O indicador 4
mantém o vínculo a atendimento clínico elegível; esses oito não têm medicamentos.

A exclusão dos 65 medicamentos iniciados após o término do atendimento foi
revogada: os indicadores 4 e 5 usam o vínculo ENCOUNTER/PATIENT, sem exigir
início até o término do atendimento. A flag start_after_encounter é preservada
na REFINED; não se alteram RAW, REFINED ou seus alertas. Os demais critérios,
incluindo rejeição de início anterior ao atendimento, permanecem inalterados.

Resultado: 3.850 medicamentos, 146 códigos, 39.152 dispensações, custo de
11.498.345,15 e 2.225 atendimentos com medicamentos; 5.563 atendimentos clínicos.
Esta decisão substitui a exclusão temporal posterior da entrega inicial.

## Etapa 5 — revisão final e reprodutibilidade

Autorizada revisão de instalação, lockfile, execução limpa, fonte/licença,
testes, falhas auxiliares e documentação; sem alterar regras analíticas.

- DNS do PyPI no sandbox era a causa reproduzida da falha uv sync. Acesso
  autorizado resolveu. DuckDB 1.5.6 e pytest 9.1.1 preservados no uv.lock,
  sem mudar faixas do pyproject. Removido pythonpath do pytest para validar
  os imports a partir da instalação normal.
- Instalação limpa, 39 testes e execução das três camadas por entry point
  confirmados. Wheel e sdist construídos; wheel executado fora do checkout.
- Origem informada: synthea.mitre.org/downloads; página oficial alternativa
  consultada e pacote CSV latest baixado e processado com sucesso. Esse pacote
  difere dos CSVs históricos; a reprodução dos mesmos totais segue dependente
  da identificação do pacote original. Hashes em reproducibility.md.
- Termos oficiais dos dados permitem uso sem restrições e solicitam citação.
  Apache-2.0 é a licença do gerador, não atribuída automaticamente aos CSVs.
  Licença do código deste projeto ainda depende de escolha do responsável.
- Falhas status 1 de consultas auxiliares não indicam problema do pipeline;
  diagnóstico e correções em reproducibility.md. Regras aprovadas preservadas.

As pendências históricas de rede/instalação nas seções anteriores descrevem
as etapas respectivas e ficam superadas pelas validações desta etapa.

## Etapa 6 — dashboard e extensões SQL aprovadas

O usuário aprovou a SPEC Streamlit/Plotly e, após auditoria das colunas reais,
a criação de marts.dashboard_kpis, medication_cost_proportion no indicador de
medicamentos e a centralização do caminho padrão do banco. Também aprovou a
leitura de seis MARTS, em vez das cinco inicialmente previstas.

- Configuração compartilhada DATABASE_PATH em pipeline_saude.config, mantendo
  artifacts/saude.duckdb e os argumentos --database da CLI.
- KPIs em SQL sobre bases elegíveis já aprovadas: pacientes distintos com
  atendimento clínico, atendimentos, atendimentos com medicamentos, proporção e
  custos registrados de cada entidade, calculados separadamente.
- Participação de medicamentos calculada por janela SQL antes da seleção visual
  de dez códigos. Denominador é o custo válido de todos os códigos, não o top 10.
- painel.py e app.py na raiz; sem agregações de negócio no Python, somente
  seleção/ordenação/formatação. Filtro de ano exclusivo da evolução por classe;
  custo de atendimento continua por ano/classe. Nenhuma regra de elegibilidade
  alterada; RAW e REFINED preservadas.
- st.cache_data armazena apenas DataFrames. Conexão read_only fechada em finally;
  botão Recarregar dados invalida a leitura. Nenhum segundo banco é criado.
- Custos sem prefixo de moeda. Especificação e limites em dashboard_spec.md.

Dashboard local preparado para revisão; sem commit ou push automático.

## Descrição dos medicamentos — aprovação na revisão da etapa 6

Usuário aprovou medication_description na MARTS por código, concatenando no SQL
as descrições distintas da base elegível originadas da REFINED, em ordem
lexicográfica determinística e com separador ` | `. Nenhuma seleção arbitrária
de descrição, normalização textual ou mudança de granularidade. Campo exibido
nos tooltips dos dois gráficos; código mantido como identificador. Nenhuma
agregação descritiva ou de negócio em Python, nem alteração de elegibilidade.
