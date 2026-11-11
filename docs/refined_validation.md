# Validação REFINED — etapa 3

Executada em 10/11/2026, com Python 3.12.3, DuckDB 1.5.6 e pytest 9.1.1.
Dependências da validação instaladas do cache local; sincronização completa e
lockfile continuam pendentes conforme limitações documentadas na etapa RAW.

## Testes unitários

Comando executado: `.venv/bin/python -m pytest -q`.

**17 testes aprovados**, usando apenas tabelas fictícias e DuckDB em memória,
sem abrir o banco persistido nem ler os CSVs reais. Incluem oito casos de
conversão inválida e dois casos de linhagem ambígua, além de tipos, UTC, nulos,
chaves, relacionamentos, alertas, recarga e snapshots vazios.

## Validação do banco local

Script pontual `/tmp/validate_pipeline_saude_refined.py`, executado com
`PYTHONPATH=src .venv/bin/python -u /tmp/validate_pipeline_saude_refined.py`.
Ele chamou a CLI `python -m pipeline_saude.cli refined` duas vezes. O script
temporário não integra a suíte de testes nem é dependência do projeto.

| Tabela | Esperado/RAW | Primeira execução | Segunda execução |
| --- | ---: | ---: | ---: |
| refined.patients | 108 | 108 | 108 |
| refined.encounters | 5.571 | 5.571 | 5.571 |
| refined.medications | 3.850 | 3.850 | 3.850 |

As duas execuções mantiveram todos os dados tipados, flags e IDs idênticos,
excluindo apenas `_refined_at` da comparação. Foram confirmados:

- 3.850 identificadores técnicos de medicamentos preenchidos, distintos e
  estáveis na recarga da mesma RAW.
- 99 datas de óbito e 268 términos de medicamentos nulos, preservados.
- 29 pacientes com CEP textual `00000`, preservados.
- Conteúdo completo da RAW inalterado, comparando hashes dos registros JSON
  ordenados por posição antes/depois.
- SHA-256 dos três CSVs inalterado antes/depois.
- Nenhuma tabela marts criada.

## Sinalizações observadas

| Tabela | Flag | Linhas sinalizadas |
| --- | --- | ---: |
| patients | missing_fips | 29 |
| patients | unknown_zip | 29 |
| encounters | start_after_death | 7 |
| encounters | stop_after_death | 7 |
| medications | start_after_encounter | 65 |
| medications | zero_duration | 995 |

Todas as demais regras tiveram zero ocorrências, incluindo chaves ausentes ou
duplicadas, registros órfãos e divergência de paciente entre medicamento e
atendimento. Os sete atendimentos após óbito correspondem aos registros de
`Death Certification` identificados no diagnóstico e continuam preservados.
As flags podem ocorrer juntas na mesma linha; não somá-las como total de
registros problemáticos.

Relatório JSON local: `artifacts/refined_validation.json`, ignorado pelo Git.
O banco permanece em `artifacts/saude.duckdb`, também ignorado. Não houve
staging, commit ou push.
