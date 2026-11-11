# Pipeline de saúde — projeto final de Engenharia de Dados

Pipeline em Python, uv, DuckDB e SQL, com as camadas RAW → REFINED → MARTS no
mesmo banco local e dashboard em Streamlit e Plotly. Sem orquestrador.

As etapas 1–5 foram publicadas em commits separados. A etapa 6, com o dashboard
e os testes de cobertura, está publicada na branch `main`, no commit `6e75e02`.

Os testes usam dados fictícios em memória ou em arquivos DuckDB temporários,
sem acessar os CSVs originais ou o banco persistido do projeto.

## Instalação

Pré-requisitos: Git, [uv](https://docs.astral.sh/uv/getting-started/installation/),
Python 3.12 ou superior e acesso ao PyPI na primeira instalação. A validação foi
feita com Python 3.12.3, uv 0.13.5, DuckDB 1.5.6 e pytest 9.1.1 em Linux x86_64.
Após clonar o repositório, entre na raiz do projeto e instale as dependências:

```bash
uv sync --locked --python 3.12
```

O `uv.lock` fixa versões e hashes. Não é necessário instalar pacotes manualmente,
ativar a `.venv` ou definir `PYTHONPATH`. Os testes não precisam dos CSVs; os
comandos de execução e cobertura estão na seção [Auditoria de testes e cobertura](#auditoria-de-testes-e-cobertura).

### Resolução de problemas de instalação

O problema anterior do `uv sync` era de DNS/rede no ambiente restrito, não de
conflito de dependências. O acesso autorizado ao PyPI resolveu a instalação.
Em redes restritas, libere o acesso ao PyPI e a `files.pythonhosted.org`.
A opção `--offline` só funciona após o preenchimento do cache.

Um aviso de `VIRTUAL_ENV` de outro projeto não altera o destino: o uv usa a
`.venv` deste projeto. Prefira desativar o outro ambiente; não use `--active`
para instalar neste projeto. Relatório: [Reprodutibilidade](docs/reproducibility.md).

## Fonte, termos de uso e obtenção dos CSVs

Origem informada pelo responsável: [Synthea / MITRE — Downloads](https://synthea.mitre.org/downloads).
Os dados são sintéticos, não registros de pessoas reais. A
[página oficial alternativa de downloads](https://synthetichealth.github.io/downloads.html)
permite uso dos dados sem restrições e solicita citação do Synthea/SyntheticMass.
Essa declaração de uso dos dados é distinta da licença **Apache-2.0 do gerador**,
verificável no [LICENSE do Synthea](https://github.com/synthetichealth/synthea/blob/master/LICENSE).
Não atribuímos automaticamente Apache-2.0 ou CC0 aos CSVs. A licença do código
deste projeto ainda não foi escolhida. **Os arquivos CSV não estão incluídos
neste repositório.**

Referência: Walonoski J. et al. *Synthea: An approach, method, and software
mechanism for generating synthetic patients and the synthetic electronic health
care record*. JAMIA, 25(3), 230–238, 2018. [DOI](https://doi.org/10.1093/jamia/ocx079).

Para reproduzir a execução com a amostra pública:

1. Abra a página de downloads e escolha **100 Sample Synthetic Patient Records,
   CSV**, em “Latest Version of Synthea”. Se o domínio MITRE estiver indisponível,
   use a página oficial alternativa acima.
2. Baixe o [ZIP CSV oficial latest](https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip).
3. Extraia o pacote e copie somente `patients.csv`, `encounters.csv` e `medications.csv`
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
(108 / 5.571 / 3.850). A URL do pacote exato, a versão, a semente de geração (seed) e os parâmetros que
originaram os arquivos locais ainda não foram identificados. Os hashes das duas
amostras estão em [docs/reproducibility.md](docs/reproducibility.md). Para obter os
mesmos totais históricos, é necessário obter os três arquivos com os hashes
locais registrados. Não recorte tabelas isoladamente para tentar igualar contagens.
`data/` e `artifacts/` permanecem integralmente ignorados pelo Git.

## Execução do pipeline

Após posicionar os três CSVs em `data/`, execute as camadas nesta ordem, a partir
da raiz do projeto:

```bash
uv run --locked pipeline-saude raw --data-dir data --database artifacts/saude.duckdb
uv run --locked pipeline-saude refined --database artifacts/saude.duckdb
uv run --locked pipeline-saude marts --database artifacts/saude.duckdb
```

Os caminhos acima são os padrões. Os mesmos comandos podem ser escritos sem
os argumentos de caminho:

```bash
uv run --locked pipeline-saude raw
uv run --locked pipeline-saude refined
uv run --locked pipeline-saude marts
```

Para consultar a ajuda da CLI e dos subcomandos:

```bash
uv run --locked pipeline-saude --help
uv run --locked pipeline-saude raw --help
uv run --locked pipeline-saude refined --help
uv run --locked pipeline-saude marts --help
```

Também é possível executar a CLI como módulo Python:

```bash
uv run --locked python -m pipeline_saude.cli raw
```

RAW lê os três CSVs; REFINED exige RAW existente; MARTS exige REFINED existente.
As etapas não executam automaticamente as anteriores. Cada etapa substitui seu
snapshot em uma transação, sem acumular linhas. Em caso de erro, a transação da
etapa é desfeita e o comando retorna status 1. A saída JSON em `stdout` informa
as contagens; mensagens de erro são enviadas para `stderr`.

## Arquitetura e granularidade

| Camada / tabela | Granularidade | Tratamento |
| --- | --- | --- |
| `raw.patients` | uma linha por registro de origem de paciente | Todas as colunas originais como texto |
| `raw.encounters` | uma linha por registro de origem de atendimento | Idem, sem deduplicação |
| `raw.medications` | uma linha por registro de origem de medicamento | Código não é chave única |
| `refined.patients` | mesma linha da RAW | Datas, números e valores monetários tipados |
| `refined.encounters` | mesma linha da RAW | Instantes com fuso; valores monetários em DECIMAL |
| `refined.medications` | mesma linha da RAW | Identidade técnica por arquivo/hash/posição |

RAW acrescenta arquivo, SHA-256, posição, lote e instante da carga. REFINED
preserva registros, converte vazios em nulos, mantém códigos/CEPs como texto e
acrescenta `_quality_flags`. Conversões inválidas abortam a transação; alertas
não apagam ou corrigem registros. As três camadas são snapshots sem histórico.

### Relacionamentos entre tabelas (JOINs)

`encounters.PATIENT = patients.Id`; medicamentos por
`medications.ENCOUNTER = encounters.Id`, com o mesmo `PATIENT`. MARTS exclui chaves de pais ambíguas antes dos
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

## Dashboard — Streamlit e Plotly

Na raiz do projeto, após instalar as dependências, preparar os CSVs e executar
as três camadas, inicie o dashboard:

```bash
uv run --locked streamlit run app.py
```

Acesse o endereço local informado pelo Streamlit, normalmente
`http://localhost:8501`. O arquivo `app.py` contém a interface em layout amplo
(`wide`); `painel.py` contém a leitura, a formatação e as seis funções dos gráficos.
O caminho padrão compartilhado com a CLI está em `src/pipeline_saude/config.py`:
`artifacts/saude.duckdb`.

Execute o aplicativo na raiz do projeto. O dashboard não cria o banco nem executa
o pipeline; em caso de ausência dos dados necessários, a tela orienta a execução
das camadas. Após atualizar o código das MARTS, execute novamente a camada para
materializar suas tabelas e colunas:

```bash
uv run --locked pipeline-saude marts
```

### Cartões e gráficos

Os seis cartões leem exclusivamente `marts.dashboard_kpis`, que contém uma linha
global calculada em SQL:

| Cartão | Valor na amostra histórica local |
| --- | ---: |
| Pacientes distintos com atendimento clínico elegível | 108 |
| Atendimentos clínicos | 5.563 |
| Atendimentos com medicamentos associados | 2.225 |
| Proporção de atendimentos com medicamentos | 39,9964% |
| Custo registrado dos atendimentos | 16.804.458,34 |
| Custo registrado dos medicamentos | 11.498.345,15 |

A interface arredonda percentuais para uma casa decimal e não assume moeda.
Os custos de atendimentos e de medicamentos permanecem separados.

Os cinco indicadores originais geram seis gráficos:

1. Evolução dos atendimentos por ano e classe.
2. Utilização de emergência por faixa etária.
3. Custos dos atendimentos por ano e classe.
4. Dez códigos de medicamentos com maior custo registrado.
5. Proporção de atendimentos com medicamentos por classe e faixa etária.
6. Participação dos dez códigos de maior custo no custo de **todos** os medicamentos.

A participação vem da coluna SQL `medication_cost_proportion`; não é recalculada
para os dez códigos exibidos. Não há totais anuais ou históricos por classe
calculados no Python. As seis MARTS locais têm, respectivamente,
**245 / 4 / 245 / 146 / 37 / 1** linhas, sendo a última `dashboard_kpis`.

Os gráficos de medicamentos mantêm o código como identificador e exibem
`medication_description` na dica ao passar o cursor (tooltip). O SQL concatena
descrições distintas da REFINED em ordem determinística, mantendo uma linha por
código e todos os indicadores existentes.

### Filtros e atualização dos dados

Evolução e custos dos atendimentos têm filtros de intervalo independentes, com
ano inicial e final inclusivos. Cada um abre de 2000 até o último ano disponível
na sua MARTS e permite consultar todo o histórico. Os filtros apenas selecionam
linhas dos gráficos correspondentes; os cartões e os demais gráficos continuam
mostrando todo o histórico.

Os custos por ano e classe usam linhas, legenda horizontal e informações
unificadas ao passar o cursor sobre o ano, sem somar períodos.

O botão **Recarregar dados** invalida o cache de DataFrames e lê novamente o banco
em modo somente leitura. A conexão é fechada após cada leitura, inclusive em caso
de erro, permitindo a atualização pelo pipeline entre leituras. Durante uma escrita
ativa, aguarde o pipeline concluir e recarregue os dados. A tela consulta somente
as MARTS, sem acessar RAW ou REFINED.

Após atualizar as MARTS, clique em **Recarregar dados** para renovar o cache do
painel. As exclusões aprovadas, incluindo `Death Certification` e o tratamento
dos medicamentos com início posterior ao atendimento, permanecem inalteradas.
Contrato, limitações e validação: [Especificação do dashboard](docs/dashboard_spec.md).

## Auditoria de testes e cobertura

O grupo de desenvolvimento inclui `pytest-cov`. A medição abrange todo o código
em `src/pipeline_saude/` e `painel.py`. Exclui `tests/`, `app.py`, ambientes
virtuais e arquivos gerados. A interface continua com seus testes existentes;
a avaliação visual é feita no navegador. Nenhum CSV original ou banco persistido
é necessário para executar os testes.

Após instalar as dependências, execute os testes com o relatório de cobertura
e de linhas não cobertas:

```bash
uv run --locked pytest --cov --cov-report=term-missing
```

Para executar com saída resumida:

```bash
uv run --locked pytest -q
```

O pytest também ativa a cobertura e o relatório de linhas ausentes por padrão.
A execução falha se a cobertura total ficar abaixo do mínimo exigido de **60%**.

### Resultado final informado

| Verificação | Resultado |
| --- | ---: |
| Testes aprovados | 105 |
| Cobertura total | 98,97% |
| Cobertura mínima exigida | 60% |
| Duração da última execução informada | 45,42 segundos |

A auditoria inclui testes próprios de RAW (preservação, recarga, validação e
rollback com dependência real), CLI e erros de schema, além dos testes de REFINED,
MARTS e painel. Todos usam dados fictícios em memória ou em arquivos temporários;
não há mock do DuckDB, `skip`, `xfail` ou comparações monetárias por aproximação.

O teste Streamlit de cache/recarga foi reduzido para 2,35 s na medição documentada
da auditoria, isolando a renderização repetida de figuras nos testes de interface.
Os seis gráficos reais continuam exercitados pelos testes específicos. Produção,
SQLs e regras analíticas não foram modificados pela auditoria. A validação final
dessa correção foi executada uma única vez, conforme orientação do responsável.
A duração de 45,42 segundos na tabela corresponde à última execução informada;
a revisão deste README não executou novamente a suíte.

Para investigar demora, use um subconjunto de testes com `-vv --durations=10` e
limite de duração, sem repetir a suíte completa em laço. Os arquivos `.coverage`
e os relatórios XML e HTML gerados são ignorados pelo Git. O pytest importa os
módulos da raiz do projeto; o pacote em `src/` continua instalado por uv, sem
configurar `PYTHONPATH` manualmente.

Resultados por arquivo, lacunas e reprodução em ambiente limpo:
[Auditoria de testes](docs/test_audit.md).

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
