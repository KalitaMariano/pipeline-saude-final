# Revisão final e reprodutibilidade — etapa 5

Validação em 10/11/2026 (America/Cuiaba), Linux x86_64, CPython 3.12.3,
uv 0.13.5. Nenhuma regra analítica ou código de transformação foi alterado.

## Dependências e instalação

A falha de `uv sync` foi reproduzida: DNS indisponível para
`https://pypi.org/simple/pytest/` dentro do sandbox. A execução com acesso de
rede autorizado resolveu e instalou o projeto normalmente, incluindo o entry
point `pipeline-saude`. Não foi necessário mudar as faixas do pyproject.toml.
Um VIRTUAL_ENV herdado de outro projeto foi ignorado pelo uv; nos testes limpos,
VIRTUAL_ENV e PYTHONPATH foram removidos do ambiente.

Gerado uv.lock com versões, fontes e hashes. A resolução inicial selecionou
pytest 9.2.0; foi ajustada com `uv lock --upgrade-package pytest==9.1.1` para
preservar a versão testada, depois sincronizada com `uv sync --locked`.
Versões finais: DuckDB 1.5.6, pytest 9.1.1, iniconfig 2.3.1, packaging 26.3,
pluggy 1.7.0, pygments 2.21.0; colorama 0.4.6 condicional ao Windows.
Não foram alteradas as faixas DuckDB >=1,<2 e pytest >=8,<10.
`uv lock --check --offline` passou com o cache preenchido.

Uma cópia dos fontes, SQLs, testes, README, pyproject e lockfile foi criada em
`/tmp/pipeline-saude-clean-n2vcvtkz`, sem .venv, CSVs, banco ou caches. Com cache
novo em `/tmp/pipeline-saude-clean-cache`, `uv sync --locked` baixou as dependências
e instalou o projeto. Não houve instalação manual nesse ambiente. A configuração
`pythonpath = ["src"]` foi removida do pytest para que a suíte use a instalação.
Os 39 casos passaram sem PYTHONPATH e sem dados persistidos na cópia limpa.

Também foi validado `uv build`: sdist e wheel construídos com sucesso, incluindo
os seis SQLs. O wheel foi instalado normalmente com sua dependência DuckDB 1.5.6
em outro ambiente vazio (`/tmp/pipeline-saude-wheel-env`). A CLI foi executada
com cwd `/tmp`; o caminho de SQL resolveu para `site-packages/pipeline_saude/sql/marts`,
sem recorrer ao checkout. A construção do wheel a partir do sdist também passou.
Os artefatos estão em `/tmp/pipeline-saude-dist`, fora do repositório.

Limites: a validação cobre Linux/Python 3.12.3. Outras plataformas e versões de
Python aceitas não foram testadas. O backend hatchling permanece sem pin exato;
o lockfile fixa dependências de execução/desenvolvimento, não promete builds
idênticos byte a byte. Acesso de rede continua necessário em instalações sem cache.

## Execução completa

Comandos oficiais, na raiz, após posicionar os CSVs em data/:

```bash
uv sync --locked --python 3.12
uv run --locked pipeline-saude raw --data-dir data --database artifacts/saude.duckdb
uv run --locked pipeline-saude refined --database artifacts/saude.duckdb
uv run --locked pipeline-saude marts --database artifacts/saude.duckdb
uv run --locked pytest -q
```

Na cópia limpa, as três camadas foram executadas pelo entry point via uv, lendo
os CSVs locais por caminho absoluto e criando um banco novo em /tmp. RAW e
REFINED: 108 pacientes, 5.571 atendimentos e 3.850 medicamentos. MARTS:
5.563 atendimentos clínicos, 3.850 medicamentos e linhas 245 / 4 / 245 / 146 / 37
na ordem dos cinco indicadores do README. Asserções separadas confirmaram
39.152 dispensações, custo de medicamentos 11.498.345,15, 2.225 atendimentos com
medicamentos e 65 flags start_after_encounter. Hashes dos CSVs antes/depois iguais.
Não foi reprocessado ou sobrescrito o banco original do projeto.

## Fonte e dois níveis de reprodução

O responsável informou a origem https://synthea.mitre.org/downloads. O acesso
retornou timeout/502 nesta revisão. A [FAQ oficial](https://github.com/synthetichealth/synthea/wiki/Frequently-Asked-Questions)
confirma essa página como fonte de amostras. Foi acessada a
[página oficial alternativa](https://synthetichealth.github.io/downloads.html),
que aponta para o [CSV latest](https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip).
O README descreve o download e a extração exata dos três arquivos, sem versioná-los.

Os termos publicados para os dados permitem uso sem restrições e solicitam
citação do Synthea/SyntheticMass. A licença Apache-2.0 no
[repositório do gerador](https://github.com/synthetichealth/synthea/blob/master/LICENSE)
é do software. Não foi encontrada nessa página uma identificação nominal de
licença dos CSVs que justifique rotulá-los automaticamente como Apache-2.0 ou
CC0. Não foi escolhida uma licença para o código deste projeto.

O ZIP latest foi baixado em /tmp e processado pelas três camadas usando o wheel,
fora do repositório, sem modificar regras. Resultado: RAW/REFINED com 111 pacientes,
5.059 atendimentos e 3.216 medicamentos; MARTS com 5.048 atendimentos clínicos,
3.216 medicamentos e linhas 278 / 4 / 278 / 150 / 37. Todos os comandos retornaram
status 0. Isso valida o procedimento público de reprodução funcional.

A amostra latest não é idêntica aos CSVs locais. Reproduzir os totais das etapas
1–4 exige os arquivos originais; pacote exato, versão, seed e parâmetros locais
permanecem pendentes. Não se pode deduzir a versão apenas pela contagem.
O ZIP latest é mutável: SHA-256 observado nesta revisão:
`990d52064037bbf83d10f13163da428964b56ae673b7f39bf549d78c1e7eda16`.

| Arquivo | SHA-256 local (etapas 1–4) | SHA-256 público latest verificado |
| --- | --- | --- |
| patients.csv | `0e8a61760644976571e7ede02e8be5bfece5111bc179d2139af87f84b630c859` | `7cc321753455e7cd0cabe0d7526432d7329fe6a4522e408f97a62819ee99e280` |
| encounters.csv | `16d209cb1429605c90c80cd859ac16569108dc46890f50eb6a125a0602235b3a` | `7f9723603541d7dc64d4cbb4862b5d381513e8d4f0c812b74caa6f1749856ef8` |
| medications.csv | `53d1d9f51c62cc6cebf236ab739ef9973ba27e65f1000a8a518026670fbffa62` | `849969bdd83c4f69913c7dd552d7faccf2fa518ffc2021cdb75e45a2c657da2c` |

## Revisão dos testes e status 1 anterior

Os 39 casos são 17 REFINED e 22 MARTS, contando parametrizações. Todos usam a
fixture de tests/conftest.py: `duckdb.connect(':memory:')`, criação de tabelas
RAW e inserção de valores fictícios. Não abrem CSVs nem banco em artifacts/.
A suíte lê os SQLs versionados para testar os indicadores, mas não dados reais.
A execução na cópia sem data/ ou artifacts/ confirmou essa independência.
Não foi acrescentada configuração para contornar imports ou pacotes ausentes.

Os comandos Python auxiliares com status 1 durante a revisão MARTS tinham dois
erros de consulta, reproduzidos em memória nesta etapa:

- `hash(row(t.*))`: DuckDB não expandiu o asterisco nesse contexto e retornou
  `Can't pack nothing into a struct`. Correção: `hash(t)`.
- `sum(TOTALCOST) cost`: alias sem proteção provocou erro de parser em `cost`.
  Correção: `sum(TOTALCOST) AS total_cost`.

Esses scripts ficavam em /tmp, não eram comandos da CLI ou testes do projeto.
As consultas corrigidas retornaram status 0. Na revisão de exclusões, o banco
estava somente para leitura; o erro na última consulta não alterou os resultados
anteriores. Não indicam defeito nas transformações ou corrupção do banco.
Também houve um comando composto de documentação cujo status 1 veio de `rg`
sem correspondências (busca por números antigos), após o Python terminar bem.
`git diff --check` deve ser avaliado separadamente; não se deve interpretar esse
status de busca como falha de validação ou de Python.

## Arquivos e pendências

Mudanças da etapa: README.md, pyproject.toml (remoção do pythonpath do pytest),
uv.lock, docs/reproducibility.md, docs/decisions.md e docs/ai_log.md.
Código de camadas, regras analíticas, SQLs e conteúdo dos testes inalterados.
CSV, bancos, downloads, caches, relatórios temporários e builds não são incluídos.

Pendências: identificar o pacote original para reprodução exata dos totais;
escolher licença do código do projeto; confirmar moeda/escopo financeiro da
amostra original. Aprovação do usuário antes de commit ou push.

Conferência final: 39 testes aprovados na cópia limpa em 26,16 s e novamente
no checkout instalado em 20,83 s. `git diff --check` retornou status 0.
`git status --short` mostrou somente os seis arquivos da entrega acima;
`git ls-files data artifacts dist` não listou arquivos e `git check-ignore`
confirmou as exclusões de dados, banco e wheel. Nenhum staging foi realizado.
