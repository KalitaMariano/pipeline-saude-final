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
| Organização física das camadas futuras | Etapa 2 autorizou ingestão no schema raw; apenas ele é criado no banco local | Confirmar detalhes de refined e marts nas respectivas etapas |
| Regras finais de refined e marts | O contrato RAW está em `raw_spec.md`; regras das outras camadas permanecem pendentes | Especificar critérios de aceitação antes de implementar |
| Identificador de medicamentos em refined | RAW usa arquivo, hash e posição para rastrear registros sem `Id` | Definir eventual chave de negócio na etapa refined |
| Ausências e anomalias | 268 términos de medicamento ausentes; 29 ZIP `00000`; outros achados no README | Aprovar sinalização, preservação e eventual tratamento |
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
