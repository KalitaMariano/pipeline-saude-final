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
| Executar somente a etapa 1 agora | Estrutura, `pyproject.toml`, `.gitignore` e documentação inicial |
| Não versionar os CSVs antes de confirmar a licença | `data/` integralmente ignorado pelo Git |
| Não fazer commit nem push automaticamente | Aguardar aprovação do usuário |
| Não implementar ingestão, refined, marts ou testes nesta etapa | Diretórios vazios apenas reservam a estrutura |

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
  `uv.lock` quando o ambiente for sincronizado. Nenhuma dependência foi instalada.
- Bancos, artefatos, caches, ambientes virtuais e configurações locais ignorados.

## Questões pendentes

| Questão | Evidência ou motivo | Próximo encaminhamento |
| --- | --- | --- |
| Origem exata dos CSVs | Informados como Synthea; URL, pacote ou comando de geração não fornecidos | Registrar a procedência verificável |
| Versão e parâmetros do Synthea | Não disponíveis nos três CSVs analisados | Confirmar versão, data, população, filtros e parâmetros disponíveis |
| Licença dos dados e redistribuição | Ainda não confirmadas para estes arquivos | Validar licença e atribuições antes de adicionar dados ao Git |
| Licença do código do projeto | Não escolhida | Definir separadamente da licença dos dados antes da publicação |
| Organização física do DuckDB | Um banco com três schemas foi proposto, mas não aprovado explicitamente | Aprovar antes da ingestão |
| Regras finais das camadas | Arquitetura aprovada; conversões, metadados e política de rejeição ainda são propostas | Especificar critérios de aceitação antes de implementar |
| Identificador de medicamentos | Sem `Id`; nove repetições da combinação paciente/atendimento/código/início | Escolher identificação técnica e regra de estabilidade |
| Ausências e anomalias | 268 términos de medicamento ausentes; 29 ZIP `00000`; outros achados no README | Aprovar sinalização, preservação e eventual tratamento |
| Registros administrativos | Sete atendimentos após o óbito são `Death Certification` | Decidir inclusão nos indicadores clínicos |
| Indicadores, faixas etárias e período | Cinco perguntas sugeridas no diagnóstico; ainda não aprovadas explicitamente | Aprovar fórmulas, granularidades, filtros e denominadores |
| Semântica financeira e moeda | Custo total de medicamentos é custo base × dispensações em todas as linhas | Consultar a documentação da versão e evitar dupla contagem |
| Estratégia de recarga | Reexecução não deve acumular registros indevidamente | Definir comportamento e critérios antes da ingestão |
| Metadados Git indisponíveis neste ambiente | `.git` está vazio e somente para leitura; `git status` não reconhece repositório | Disponibilizar um repositório Git válido e gravável para staging e commits futuros |

As cinco perguntas propostas abrangem evolução dos atendimentos, utilização de
emergência por idade, custos e cobertura por classe, concentração de custos de
medicamentos e proporção de atendimentos com medicamentos. Não há indicadores
implementados nem fórmulas aprovadas neste momento.
