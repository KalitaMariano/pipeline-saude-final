# Pipeline de saúde — projeto final de Engenharia de Dados

## Objetivo e estado atual

Construir um pipeline Python para organizar e analisar dados sintéticos de saúde,
com as camadas raw, refined e marts. O projeto segue spec-driven development:
documentar requisitos e decisões antes de implementar, avançando por etapas
revisadas e com um commit separado para cada etapa.

**Etapa 4:** RAW, REFINED e os cinco indicadores MARTS implementados.
Testes unitários usam dados fictícios em memória. Dashboard fora desta etapa.

## Tecnologias

- Python 3.12 ou superior e uv para gerenciar o projeto e as dependências.
- DuckDB e SQL para armazenamento e análise.
- pytest para testes com dados fictícios, sem acessar o banco persistido.
- Sem orquestrador.

As dependências estão declaradas em `pyproject.toml`. Em um ambiente com acesso
ao PyPI, execute a partir da raiz do projeto:

```bash
uv sync
uv run pipeline-saude raw
uv run pipeline-saude refined
uv run pipeline-saude marts
uv run pytest -q
```

O comando lê `data/` e grava `artifacts/saude.duckdb`. Para escolher os caminhos:

```bash
uv run pipeline-saude raw --data-dir data --database artifacts/saude.duckdb
uv run pipeline-saude refined --database artifacts/saude.duckdb
uv run pipeline-saude marts --database artifacts/saude.duckdb
uv run pipeline-saude raw --help
uv run pipeline-saude refined --help
```

Também é possível executar o módulo após instalar o projeto:
`uv run python -m pipeline_saude.cli raw`.
A saída JSON informa banco, lote, instante, hashes e contagens esperadas/obtidas.
Na REFINED, a saída informa banco, contagens e ocorrências de cada flag.
Falhas retornam código de saída 1 e mensagem no stderr. A REFINED requer um
banco existente com as três tabelas RAW e não executa a ingestão automaticamente.

O PyPI estava inacessível na etapa RAW. DuckDB 1.5.6 e, na etapa REFINED,
pytest 9.1.1 foram instalados do cache local. Comandos validados nesse ambiente:

```bash
PYTHONPATH=src .venv/bin/python -m pipeline_saude.cli raw
PYTHONPATH=src .venv/bin/python -m pipeline_saude.cli refined
.venv/bin/python -m pytest -q
```

A sincronização completa e a geração do `uv.lock` continuam pendentes; quando
gerado, o lockfile deverá ser versionado. O entry point instalado por `uv sync`
ainda precisa ser validado; a CLI como módulo Python foi validada.

## Dados disponíveis

Os três CSVs locais foram informados como provenientes do Synthea. A origem
exata, a versão, os parâmetros de geração e a licença aplicável ainda precisam
ser confirmados. Por isso, **a pasta `data/` está excluída do Git**. Este
repositório, por enquanto, não distribui os arquivos nem declara uma licença
para os dados.

Perfil observado nos arquivos locais em 10/11/2026:

| Arquivo | Significado | Linhas | Colunas | Identificação |
| --- | --- | ---: | ---: | --- |
| `patients.csv` | Cadastro de pacientes | 108 | 28 | `Id`, único e preenchido |
| `encounters.csv` | Atendimentos | 5.571 | 15 | `Id`, único e preenchido |
| `medications.csv` | Registros de medicamentos vinculados a atendimentos | 3.850 | 13 | Sem coluna `Id` |

Não foram encontradas linhas integralmente duplicadas em nenhum dos arquivos.
Todos os pacientes têm `STATE = Massachusetts`.

### Relacionamentos confirmados

- `encounters.PATIENT` referencia `patients.Id`: nenhum registro órfão.
- `medications.PATIENT` referencia `patients.Id`: nenhum registro órfão.
- `medications.ENCOUNTER` referencia `encounters.Id`: nenhum registro órfão.
- Nos 3.850 registros de medicamentos, o paciente coincide com o do atendimento.
- Os 108 pacientes têm atendimentos; 105 têm registros de medicamentos.
- Existem medicamentos vinculados a 2.225 dos 5.571 atendimentos.

### Cuidados identificados

- Pacientes: 99 datas de óbito ausentes, 29 valores de `FIPS` ausentes e 29
  códigos postais `00000`. Códigos postais devem preservar zeros iniciais.
- Atendimentos: 2.044 registros sem código e descrição do motivo. Os inícios
  vão de 26/11/1942 a 16/08/2026.
- Medicamentos: 268 términos ausentes, 900 registros sem motivo e 995 registros
  com início igual ao término. Os inícios vão de 04/12/1955 a 16/08/2026.
- A combinação paciente, atendimento, código e início repete-se em nove grupos
  de medicamentos; os términos diferem. Não é seguro deduplicar por essa chave.
- Sete atendimentos posteriores ao óbito têm descrição `Death Certification`.
  A MARTS exclui todos os oito registros `Death Certification` (incluindo um sem alerta temporal).
- Um LEFT JOIN de atendimentos com medicamentos gera 7.196 linhas. Indicadores
  deverão evitar a repetição de custos de atendimento.
- `TOTALCOST = BASE_COST × DISPENSES` em todos os registros de medicamentos.
  Moeda, escopo dos custos e significado financeiro da cobertura ainda precisam
  de confirmação; não somar custos de tabelas diferentes sem essa definição.

Esses números descrevem os arquivos locais, não a população real. As regras
finais de qualidade e dos indicadores serão especificadas antes da implementação.

## Arquitetura e estrutura

As três camadas estão aprovadas. A RAW preserva os campos originais como texto,
incluindo vazios como `''`, zeros e espaços. Acrescenta `_source_file`,
`_source_sha256`, `_source_row_number`, `_ingested_at` e `_batch_id`.
Cada execução substitui as três tabelas em uma única transação, sem acumular
linhas e sem deduplicar a origem. Não mantém versões antigas no banco.
Consulte o contrato completo em [docs/raw_spec.md](docs/raw_spec.md) e a
validação em [docs/raw_validation.md](docs/raw_validation.md).

A REFINED converte datas, timestamps em instantes UTC, moedas em `DECIMAL(18,2)`,
renda e dispensações em inteiros e coordenadas em `DOUBLE`. Identificadores,
códigos e CEPs continuam textos; campos vazios tornam-se nulos. Registros não
são excluídos nem deduplicados. `_quality_flags` sinaliza chaves, relacionamentos
e anomalias; `_medication_id` rastreia medicamentos por arquivo, hash e posição.
Valores preenchidos incompatíveis com os tipos interrompem a transação inteira,
sem transformar erros em nulos silenciosamente. A recarga substitui as três
tabelas sem acúmulo.

Contrato: [docs/refined_spec.md](docs/refined_spec.md).
Resultados: [docs/refined_validation.md](docs/refined_validation.md).
A validação local manteve **108 pacientes, 5.571 atendimentos e 3.850
medicamentos** nas duas execuções. **17 testes unitários aprovados**.
A MARTS contém cinco tabelas: evolução por ano/classe (245 linhas), emergência
por idade (4), custos/cobertura por ano/classe (245), medicamentos por código
(146) e proporção de atendimentos com medicamentos por classe/idade (37).
A população elegível tem 5.563 atendimentos e 3.850 medicamentos; 2.225
atendimentos têm medicamentos elegíveis. Custos permanecem separados por entidade.

Granularidades, denominadores, idade no atendimento e exclusões:
[docs/marts_spec.md](docs/marts_spec.md). Contagens, reconciliação financeira e
recarga: [docs/marts_validation.md](docs/marts_validation.md).
**39 testes aprovados**, incluindo 22 casos MARTS.
Os 65 medicamentos iniciados após o atendimento participam dos indicadores 4 e 5;
o alerta temporal permanece na REFINED. Os oito `Death Certification` ficam
fora da população de atendimentos clínicos por decisão aprovada.
Comando local validado: `PYTHONPATH=src .venv/bin/python -m pipeline_saude.cli marts`.
O comando requer REFINED existente e substitui as cinco tabelas em uma transação;
a saída JSON informa contagens elegíveis e por tabela. Os SQLs são incluídos no wheel.

```text
pipeline-saude-final/
├── data/                       # CSVs locais; ignorados pelo Git
├── docs/
│   ├── decisions.md            # Decisões aprovadas e questões pendentes
│   ├── ai_log.md               # Uso da IA, limitações e correções
│   ├── raw_spec.md             # Contrato de ingestão
│   ├── raw_validation.md       # Resultados da RAW
│   ├── refined_spec.md         # Tipos, identidade e qualidade
│   └── refined_validation.md   # Resultados da REFINED
├── src/pipeline_saude/
│   ├── __init__.py
│   ├── cli.py                  # Comandos raw, refined e marts
│   ├── raw/
│   │   ├── __init__.py
│   │   └── ingest.py           # Leitura e carga transacional
│   ├── refined/
│   │   ├── __init__.py
│   │   └── transform.py        # Tipagem e qualidade transacionais
│   └── marts/                  # Execução transacional dos indicadores
├── tests/
│   ├── conftest.py             # Dados fictícios e conexão em memória
│   └── test_refined.py
├── sql/marts/                  # Cinco indicadores SQL e base compartilhada
├── .gitignore
├── pyproject.toml
└── README.md
```

Os arquivos `.gitkeep` preservam diretórios vazios no Git. O diretório
`artifacts/` contém o banco local e relatórios gerados e está ignorado.
Os contratos e testes MARTS complementam a estrutura acima em
`docs/marts_spec.md`, `docs/marts_validation.md` e `tests/test_marts.py`.

## Desenvolvimento por etapas

1. Estrutura, configuração e documentação inicial — preparada anteriormente.
2. Ingestão RAW e validação — preparada anteriormente.
3. REFINED, testes unitários e validação — preparada anteriormente.
4. Indicadores SQL e marts — implementada, aguardando revisão.

Cada etapa terá um commit separado após revisão. Não realizar commit ou push
automaticamente. Consulte `docs/decisions.md` para o escopo aprovado e as
pendências que limitam as próximas etapas.
