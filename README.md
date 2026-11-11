# Pipeline de saúde — projeto final de Engenharia de Dados

Pipeline Python, uv, DuckDB e SQL com camadas RAW → REFINED → MARTS no mesmo
banco local. Etapas 1–4 publicadas com commits separados; etapa 5 revisa instalação
e reprodutibilidade. Sem orquestrador ou dashboard. **39 testes unitários** usam
somente dados fictícios e DuckDB em memória.

## Instalação e execução

Pré-requisitos: Git, [uv](https://docs.astral.sh/uv/getting-started/installation/),
Python 3.12 ou superior e acesso ao PyPI na primeira instalação. A validação foi
feita com Python 3.12.3, uv 0.13.5, DuckDB 1.5.6 e pytest 9.1.1 em Linux x86_64.
Após clonar o repositório e entrar na raiz do projeto:

```bash
uv sync --locked --python 3.12
uv run --locked pytest -q
```

O `uv.lock` fixa versões e hashes; não é necessário instalar pacotes manualmente,
ativar a `.venv` ou definir `PYTHONPATH`. Os testes não precisam dos CSVs.
Prepare os arquivos conforme a seção seguinte e execute na ordem:

```bash
uv run --locked pipeline-saude raw --data-dir data --database artifacts/saude.duckdb
uv run --locked pipeline-saude refined --database artifacts/saude.duckdb
uv run --locked pipeline-saude marts --database artifacts/saude.duckdb
```

Esses caminhos são os padrões; também funcionam `uv run --locked pipeline-saude
raw`, `refined` e `marts`, cada um como comando separado. Consulte
`uv run --locked pipeline-saude --help` e o `--help` de cada subcomando.
A CLI instalada também aceita `uv run --locked python -m pipeline_saude.cli raw`.
RAW lê os três CSVs; REFINED exige RAW existente e MARTS exige REFINED existente.
As etapas não executam automaticamente as anteriores. Cada etapa substitui seu
snapshot em uma transação, sem acumular linhas; erro desfaz a etapa e retorna
status 1. JSON no stdout informa contagens; mensagens de erro vão para stderr.

O problema anterior do `uv sync` era DNS/rede no ambiente restrito, não conflito
de dependências. O acesso autorizado ao PyPI resolveu a instalação. Em redes
restritas, libere PyPI e files.pythonhosted.org; `--offline` só funciona após
preencher o cache. Um aviso de `VIRTUAL_ENV` de outro projeto não altera o destino:
uv usa a `.venv` deste projeto. Prefira desativar o outro ambiente; não use
`--active` para instalar neste projeto. Relatório: [docs/reproducibility.md](docs/reproducibility.md).

## Fonte, termos de uso e obtenção dos CSVs

Origem informada pelo responsável: [Synthea / MITRE — Downloads](https://synthea.mitre.org/downloads).
Os dados são sintéticos, não registros de pessoas reais. A
[página oficial alternativa de downloads](https://synthetichealth.github.io/downloads.html)
permite uso dos dados sem restrições e solicita citação do Synthea/SyntheticMass.
Essa declaração de uso dos dados é distinta da licença **Apache-2.0 do gerador**,
verificável no [LICENSE do Synthea](https://github.com/synthetichealth/synthea/blob/master/LICENSE).
Não atribuímos automaticamente Apache-2.0 ou CC0 aos CSVs. A licença do código
deste projeto ainda não foi escolhida; este repositório não inclui os dados.

Referência: Walonoski J. et al. *Synthea: An approach, method, and software
mechanism for generating synthetic patients and the synthetic electronic health
care record*. JAMIA, 25(3), 230–238, 2018. [DOI](https://doi.org/10.1093/jamia/ocx079).

Para reproduzir a execução com a amostra pública:

1. Abra a página de downloads e escolha **100 Sample Synthetic Patient Records,
   CSV**, em “Latest Version of Synthea”. Se o domínio MITRE estiver indisponível,
   use a página oficial alternativa acima.
2. Baixe o [ZIP CSV oficial latest](https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip).
3. Extraia e copie somente `patients.csv`, `encounters.csv` e `medications.csv`
   para `data/` na raiz do projeto. Use os três arquivos do mesmo pacote, mantendo
   cabeçalhos e conteúdo originais. Não coloque o ZIP ou uma pasta intermediária
   no lugar dos três CSVs. Os demais arquivos do Synthea não são consumidos.

Alternativa por terminal, a partir da raiz (requer curl e Python):

```bash
mkdir -p data
curl --fail --location https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip --output data/synthea_sample_data_csv_latest.zip
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile
with ZipFile('data/synthea_sample_data_csv_latest.zip') as archive:
    for table in ('patients', 'encounters', 'medications'):
        name = table + '.csv'
        target = Path('data') / name
        if target.exists():
            raise SystemExit(f'{target} já existe; use uma pasta vazia para outra amostra.')
    for table in ('patients', 'encounters', 'medications'):
        name = table + '.csv'
        (Path('data') / name).write_bytes(archive.read(name))
PY
```

Layout esperado:

```text
data/
├── patients.csv
├── encounters.csv
└── medications.csv
```

**Reproduzir a execução não garante reproduzir os totais históricos.** O link
`latest` muda. O download verificado na etapa 5 contém 111 pacientes, 5.059
atendimentos e 3.216 medicamentos e difere da amostra local das etapas 1–4
(108 / 5.571 / 3.850). A URL do pacote exato, versão, seed e parâmetros que
originaram os arquivos locais ainda não foram identificados. Os hashes das duas
amostras estão em [docs/reproducibility.md](docs/reproducibility.md). Para obter os
mesmos totais históricos, é necessário obter os três arquivos com os hashes
locais registrados. Não recorte tabelas isoladamente para tentar igualar contagens.
`data/` e `artifacts/` permanecem integralmente ignorados pelo Git.

## Arquitetura e granularidade

| Camada / tabela | Granularidade | Tratamento |
| --- | --- | --- |
| `raw.patients` | uma linha por registro de origem de paciente | Todas as colunas originais como texto |
| `raw.encounters` | uma linha por registro de origem de atendimento | Idem, sem deduplicação |
| `raw.medications` | uma linha por registro de origem de medicamento | Código não é chave única |
| `refined.patients` | mesma linha da RAW | Datas, números e valores monetários tipados |
| `refined.encounters` | mesma linha da RAW | Instantes com fuso; moedas DECIMAL |
| `refined.medications` | mesma linha da RAW | Identidade técnica por arquivo/hash/posição |

RAW acrescenta arquivo, SHA-256, posição, lote e instante da carga. REFINED
preserva registros, converte vazios em nulos, mantém códigos/CEPs como texto e
acrescenta `_quality_flags`. Conversões inválidas abortam a transação; alertas
não apagam ou corrigem registros. As três camadas são snapshots sem histórico.

JOINs: `encounters.PATIENT = patients.Id`; medicamentos por `ENCOUNTER =
encounters.Id` e mesmo `PATIENT`. MARTS exclui chaves de pais ambíguas antes dos
JOINs. A associação usa atendimentos distintos antes do LEFT JOIN; custos de
atendimentos não são somados depois de um JOIN de um para muitos com medicamentos.

Contratos: [RAW](docs/raw_spec.md), [REFINED](docs/refined_spec.md),
[MARTS](docs/marts_spec.md). SQLs em `sql/marts/`; código e CLI em
`src/pipeline_saude/`; testes em `tests/`; decisões e registro da IA em `docs/`.
O wheel inclui os SQLs e funciona fora do checkout.

## Cinco indicadores MARTS

| Tabela | Granularidade | Medidas / denominadores |
| --- | --- | --- |
| `encounters_by_year_class` | ano UTC × classe | Contagem de atendimentos clínicos |
| `emergency_by_age` | faixa etária, todos os anos | Emergências / todos os atendimentos da faixa; pacientes distintos |
| `encounter_costs_by_year_class` | ano UTC × classe | Custos e cobertura; média por atendimento financeiro válido; cobertura / custo total válido |
| `medication_costs_by_code` | código textual, todos os anos | Registros, dispensações, custos e cobertura; custo / dispensações válidas |
| `encounters_with_medications` | classe × faixa etária, todos os anos | Atendimentos com medicamentos associados / atendimentos clínicos do grupo |

Idade completa na data UTC do atendimento; faixas 0–17, 18–44, 45–64 e 65+.
Os oito `Death Certification` ficam fora da população clínica por decisão
aprovada. Os 65 medicamentos iniciados após o término do atendimento local são
incluídos nos indicadores 4 e 5; os alertas temporais permanecem na REFINED.
Os demais filtros aprovados estão em [marts_spec.md](docs/marts_spec.md).
Anomalias financeiras afetam somas e denominadores financeiros; não removem
indiscriminadamente utilização ou vínculo. Divisão por zero retorna NULL.

Validação histórica com os arquivos locais: 5.563 atendimentos clínicos, 3.850
medicamentos, 146 códigos, 39.152 dispensações, custo de medicamentos de
11.498.345,15 e 2.225 atendimentos com medicamentos. Linhas MARTS, na ordem acima:
**245 / 4 / 245 / 146 / 37**. Evidências:
[raw_validation.md](docs/raw_validation.md),
[refined_validation.md](docs/refined_validation.md),
[marts_validation.md](docs/marts_validation.md).

## Limitações

- Dados sintéticos e amostra observacional: os indicadores não representam a
  população real nem sustentam inferências causais ou decisões clínicas.
- Emergência mede participação nos atendimentos observados, não incidência
  populacional ou taxa por pessoa-tempo. Só há grupos observados nas MARTS.
- Custos de atendimentos e medicamentos permanecem separados. TOTALCOST já
  incorpora dispensações; não multiplicar novamente. Moeda e escopo financeiro
  da versão local não foram confirmados; não somar os custos das duas entidades.
- Valores geográficos ausentes, medicamentos com término nulo ou duração zero
  são preservados; alertas não provam erro clínico nem indicam uso atual.
- Downloads novos podem mudar conteúdo ou schema e exigir revisão explícita do
  contrato; o pipeline não altera as regras automaticamente para aceitá-los.
- A instalação foi validada em Linux/Python 3.12; outras plataformas e versões
  permitidas pelo projeto não foram testadas. O backend de build continua
  declarado sem versão exata, como nas etapas anteriores.

Etapa 5 preparada para revisão. Nenhum commit ou push automático; aguardar
aprovação antes da publicação desta entrega.
