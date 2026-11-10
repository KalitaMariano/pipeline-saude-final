# Validação da RAW — etapa 2

Executada em 10/11/2026 com Python 3.12.3 e DuckDB 1.5.6, instalado do cache
local. Banco: `artifacts/saude.duckdb`, ignorado pelo Git.

## Execuções e contagens

Um script pontual em `/tmp/validate_pipeline_saude_raw.py` executou a CLI como
módulo duas vezes, leu o banco em modo somente leitura após cada execução e
comparou os dados com uma leitura dos CSVs via `csv.reader`.
Esse script temporário não integra o repositório nem substitui os testes pytest
previstos para etapa posterior.

| Tabela | Esperado no CSV | Primeira execução validada | Segunda execução validada |
| --- | ---: | ---: | ---: |
| `raw.patients` | 108 | 108 | 108 |
| `raw.encounters` | 5.571 | 5.571 | 5.571 |
| `raw.medications` | 3.850 | 3.850 | 3.850 |
| **Total** | **9.529** | **9.529** | **9.529** |

Lote final: `2ec9f5ac-d691-417c-9bba-da7056a399b4`.
Instante da carga: `2026-11-10T23:50:09.220970+00:00`.

## Conferências aprovadas

- Todas as células originais foram comparadas, sem amostragem, nas duas cargas,
  ordenadas pela posição do registro de origem.
- Nomes e ordem das 28, 15 e 13 colunas originais preservados, respectivamente;
  todas com tipo `VARCHAR`. Cada tabela tem mais cinco colunas de metadados.
- Arquivo e hash corretos em cada registro, posições contínuas de 1 a N,
  instante e lote comuns às três tabelas, lote diferente a cada execução.
- Somente as três tabelas do schema `raw` foram criadas; não há tabelas refined
  ou marts no banco validado.
- Recarga sem acúmulo e hashes dos três CSVs inalterados antes/depois.
- CLI `raw --help`, sintaxe Python e configuração TOML verificadas.

Hashes SHA-256 conferidos antes e depois da validação:

```text
patients.csv
0e8a61760644976571e7ede02e8be5bfece5111bc179d2139af87f84b630c859

encounters.csv
16d209cb1429605c90c80cd859ac16569108dc46890f50eb6a125a0602235b3a

medications.csv
53d1d9f51c62cc6cebf236ab739ef9973ba27e65f1000a8a518026670fbffa62
```

## Cenários fictícios temporários aprovados

Em outro banco e outros CSVs dentro de um diretório temporário:

- Preservação de string vazia, `00123`, texto literal `NULL`, espaços nas
  extremidades, Unicode, aspas, vírgula, quebra de linha e duas linhas idênticas.
- Arquivo com número incorreto de campos rejeitado antes de alterar o banco.
- Falha de gravação provocada por uma view preexistente em `raw.encounters`:
  a substituição anterior de `raw.patients` foi desfeita e a view preservada,
  comprovando rollback da carga inteira.

## Limitações registradas

A primeira conferência encontrou ausência de `pytz` ao buscar `TIMESTAMPTZ`
como datetime Python. A validação final usou `epoch(_ingested_at)` para comparar
o instante UTC sem alterar o tipo armazenado. Detalhes em `ai_log.md`.

O comando usado para executar a ingestão neste ambiente mínimo foi:

```bash
PYTHONPATH=src .venv/bin/python -m pipeline_saude.cli raw
```

`uv sync` e a resolução offline do lockfile não concluíram por indisponibilidade
do registro e do conjunto completo de dependências em cache. O comando instalado
`uv run pipeline-saude raw` permanece pendente de validação após sincronização
completa; a CLI como módulo foi validada. Não há `uv.lock` gerado nesta entrega.
