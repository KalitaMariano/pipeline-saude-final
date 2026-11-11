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
| Organização e regras de marts | RAW e REFINED usam schemas separados no mesmo banco local | Especificar marts antes da implementação |
| Identidade clínica entre versões | A identidade técnica de medicamentos usa arquivo/hash/posição e muda com a versão do arquivo | Avaliar outra chave somente se houver necessidade de histórico entre versões |
| Tratamento analítico de ausências e anomalias | REFINED preserva registros e sinaliza; não imputa nem corrige | Decidir filtros ou tratamentos apenas nos indicadores aprovados |
| Registros administrativos | Sete atendimentos após o óbito são `Death Certification` | Decidir inclusão nos indicadores clínicos |
| Indicadores, faixas etárias e período | Cinco perguntas sugeridas no diagnóstico; ainda não aprovadas explicitamente | Aprovar fórmulas, granularidades, filtros e denominadores |
| Semântica financeira e moeda | Custo total de medicamentos é custo base × dispensações em todas as linhas | Consultar a documentação da versão e evitar dupla contagem |
| Sincronização completa e lockfile | PyPI indisponível; cache permitiu instalar DuckDB, mas não resolver todo o projeto | Executar `uv sync` com conectividade e versionar o `uv.lock` |

As cinco perguntas propostas abrangem evolução dos atendimentos, utilização de
emergência por idade, custos e cobertura por classe, concentração de custos de
medicamentos e proporção de atendimentos com medicamentos. Não há indicadores
implementados nem fórmulas aprovadas neste momento.

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
