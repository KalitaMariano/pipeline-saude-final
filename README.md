# Pipeline de saúde — projeto final de Engenharia de Dados

## Objetivo e estado atual

Construir um pipeline Python para organizar e analisar dados sintéticos de saúde,
com as camadas raw, refined e marts. O projeto segue spec-driven development:
documentar requisitos e decisões antes de implementar, avançando por etapas
revisadas e com um commit separado para cada etapa.

**Etapa 2:** ingestão RAW implementada. O banco local contém somente as três
tabelas do schema `raw`. Refined, marts, dashboard e suíte de testes ainda não
foram implementados.

## Tecnologias

- Python 3.12 ou superior e uv para gerenciar o projeto e as dependências.
- DuckDB e SQL para armazenamento e análise.
- pytest previsto para testes com dados fictícios, sem acessar o banco persistido.
- Sem orquestrador.

As dependências estão declaradas em `pyproject.toml`. Em um ambiente com acesso
ao PyPI, execute a partir da raiz do projeto:

```bash
uv sync
uv run pipeline-saude raw
```

O comando lê `data/` e grava `artifacts/saude.duckdb`. Para escolher os caminhos:

```bash
uv run pipeline-saude raw --data-dir data --database artifacts/saude.duckdb
uv run pipeline-saude raw --help
```

Também é possível executar o módulo após instalar o projeto:
`uv run python -m pipeline_saude.cli raw`.
A saída JSON informa banco, lote, instante, hashes e contagens esperadas/obtidas.
Falhas retornam código de saída 1 e mensagem no stderr.

Nesta sessão, o PyPI estava inacessível. Foi possível instalar apenas DuckDB
1.5.6 a partir do cache local e validar com
`PYTHONPATH=src .venv/bin/python -m pipeline_saude.cli raw`.
A sincronização completa e a geração do `uv.lock` continuam pendentes; quando
gerado, o lockfile deverá ser versionado. Não há suíte de testes executável ainda.

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
  O tratamento analítico desses registros ainda precisa de aprovação.
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

Refined será destinada à tipagem e qualidade; marts, aos indicadores SQL, cada
um em seu próprio arquivo. As regras dessas etapas continuam pendentes.

```text
pipeline-saude-final/
├── data/                       # CSVs locais; ignorados pelo Git
├── docs/
│   ├── decisions.md            # Decisões aprovadas e questões pendentes
│   ├── ai_log.md               # Uso da IA, limitações e correções
│   ├── raw_spec.md             # Contrato de ingestão
│   └── raw_validation.md       # Resultados da validação
├── src/pipeline_saude/
│   ├── __init__.py
│   ├── cli.py                  # Comando raw
│   ├── raw/
│   │   ├── __init__.py
│   │   └── ingest.py           # Leitura e carga transacional
│   ├── refined/                # Apenas reserva de diretório
│   └── marts/                  # Apenas reserva de diretório
├── sql/marts/                  # Apenas reserva de diretório
├── .gitignore
├── pyproject.toml
└── README.md
```

Os arquivos `.gitkeep` preservam diretórios vazios no Git. O diretório
`artifacts/` contém o banco local e está ignorado. Testes e arquivos SQL serão
adicionados nas etapas próprias.

## Desenvolvimento por etapas

1. Estrutura, configuração e documentação inicial — preparada anteriormente.
2. Ingestão RAW e validação — etapa atual, aguardando revisão.
3. Refined, indicadores SQL e testes — etapas futuras, a aprovar.

Cada etapa terá um commit separado após revisão. Não realizar commit ou push
automaticamente. Consulte `docs/decisions.md` para o escopo aprovado e as
pendências que limitam as próximas etapas.
