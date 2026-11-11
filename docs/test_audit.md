# Auditoria de testes e cobertura

## Escopo e inspeção

Foram lidos os módulos Python, contratos RAW/REFINED/MARTS/dashboard e todos os
77 casos existentes (incluindo parametrizações). O número de testes não foi
usado para inferir cobertura. pytest-cov 7.1.0 e coverage 7.17.2 já estavam
instalados, declarados no grupo dev e no uv.lock ao iniciar esta auditoria.
Não foi preciso adicionar dependências nem atualizar versões.

O projeto não tinha configuração de coverage. A primeira medição, após definir
o escopo, apresentou 67,47%, mas uma falha de timeout do AppTest impediu considerá-la
validação bem-sucedida. A CLI tinha 0% e RAW 21,67%: faltavam testes de ingestão
e execução por arquivo/CLI, mesmo com muitos testes de indicadores.

O escopo agora é explícito no pyproject.toml:

- Todo o código Python em src/pipeline_saude, incluindo CLI, configuração,
  ingestão RAW e transformações REFINED/MARTS, mesmo se um módulo não for usado.
- painel.py: leitura, formatação, seleção de linhas e figuras.
- Fora da medição: tests/, app.py, ambientes, artefatos e arquivos gerados.
  app.py continua exercitado pelos testes de interface já existentes; sua
  cobertura não entra no percentual e a validação visual cabe ao navegador.

A configuração preserva tests/; aplica --cov e term-missing por padrão,
fail_under=60 e precisão de duas casas. Não há exclusão de linhas de produção,
pragma no cover ou remoção de caminhos difíceis do denominador. A medição é de
linhas executáveis, não de ramos, SQL ou código interno de terceiros. As regras
SQL são verificadas pelos valores esperados dos testes DuckDB reais.

`pythonpath = ["."]` faz o pytest importar painel.py/app.py do checkout, evitando
medir cópias antigas que force-include coloca em site-packages. Não acrescenta
src ao PYTHONPATH: pipeline_saude continua instalado por uv. Ambientes virtuais
e dependências de terceiros não entram na cobertura. Referências de configuração:
[pytest-cov](https://pytest-cov.readthedocs.io/en/latest/config.html) e
[coverage.py](https://coverage.readthedocs.io/en/latest/config.html).

## Cenários auditados e complementados

| Área | Evidência |
| --- | --- |
| RAW | CSVs fictícios preservam vazios, zeros, espaços, Unicode, aspas, vírgulas, quebra de linha e duplicatas; tipos, hashes, posições e lote; recarga substitui; cabeçalho apenas produz tabelas vazias |
| RAW — falhas | Ausência de arquivo, UTF-8 inválido, CSV malformado, cabeçalhos ausentes/repetidos/em conflito, bytes NUL, número incorreto de campos e banco dentro da pasta de origem |
| RAW — transação | FK real em DuckDB impede substituir a segunda tabela; comparação integral confirma rollback da primeira e preservação dos metadados e das três tabelas |
| REFINED | Testes anteriores de tipos, nulos, UTC, decimais, IDs, relações, flags, recarga e rollback; novos cenários de coluna obrigatória ausente, conflito de metadados e tipo RAW inesperado |
| MARTS | Testes anteriores de granularidade, aniversários, JOIN sem multiplicar custos, exclusões, vínculos, finanças, descrições, KPIs, proporções, vazio, idempotência e rollback preservados |
| CLI | Três comandos reais em diretório temporário com CSVs completos fictícios; JSON, status, caminho padrão local e KPIs; entradas/banco/schema ausentes com erro e preservação de tabela sentinela |
| painel.py | Seis tabelas, DataFrames esperados, somente leitura, conexão fechada no sucesso/erro; consultas SELECT * exclusivas; formatação, filtros e figuras pequenas/vazias |
| Interface existente | Seis cartões, cache/recarga, erros, títulos e independência dos dois intervalos, sem incluir app.py na medição |

Dois testes de leitura que usavam Mock(wraps=connection) foram substituídos por
DuckDB real. Para verificar read_only, uma conexão de escrita temporária aberta
faz o leitor falhar por configuração incompatível; para verificar fechamento,
uma conexão de escrita abre imediatamente após ler ou após erro. A consulta
exata é conferida separadamente pela AST. Mocks restantes são apenas de dados
ou chamadas de apresentação nos testes Streamlit, não do motor DuckDB.

A investigação com -vv, --durations e faulthandler identificou demora no teste
Streamlit de cache/recarga: 10,20 s de execução, com stack em atualização de layout
Plotly durante o botão Recarregar. Não era espera por DuckDB. A importação a frio
de painel.py também carrega pandas/Plotly, contribuindo para a coleta; não há
leitura do banco no import do módulo. Não se alterou o código de produção.

Os testes AppTest de controles/cache agora usam uma fixture explícita de figuras
leves, cada uma com identidade própria e metadados das linhas recebidas. Mantêm
as assertivas de filtros, seis cartões, cache/recarga e gráficos não afetados.
Os testes específicos dos seis gráficos continuam chamando Plotly real e
verificando valores, ordem, descrições e figuras pequenas/vazias. Não há mock
DuckDB, exclusão de testes ou redução do escopo de cobertura. O timeout AppTest
foi fixado em dez segundos por execução, em vez de simplesmente elevar esperas.

Diagnóstico direcionado com limite externo de 60 s: oito casos passaram em
14,00 s; cache/recarga passou a 2,38 s e independência dos filtros a 0,66 s.
Durante o ajuste da fixture foram corrigidos dados vazios e IDs duplicados das
figuras de teste, sem modificar o Streamlit de produção. As assertivas continuam
obrigatórias; não há skip, xfail, testes sem assert ou pytest.approx para dinheiro.
Valores monetários tipados são comparados com Decimal.

## Reprodução

Na raiz, com as dependências do lockfile:

```bash
uv sync --locked
uv run --locked pytest --cov --cov-report=term-missing
```

O comando não usa --cov-append: cada rodada mede do zero. Um
percentual abaixo de 60 faz a execução falhar. O arquivo .coverage é local e
ignorado, assim como coverage.xml e htmlcov/. Relatórios opcionais:
`uv run --locked coverage json -o /tmp/health-coverage.json`.

A validação final usa uma cópia em /tmp contendo apenas fontes, SQLs, testes,
metadados e lockfile, sem data/, artifacts/ ou .venv prévia. O ambiente é instalado
pelo uv com as versões bloqueadas. Nenhum teste depende dos dados reais ou de
pipeline previamente executado: a sequência da CLI cria sua própria origem e
banco temporários dentro do teste. Não são movidos ou alterados dados do projeto.

## Controle de execução após orientação do usuário

A primeira rodada completa anterior à correção passou 105 casos, com 98,97%,
em 169,01 s. A segunda foi interrompida a pedido do usuário, durante o teste de
cache/recarga; não é tratada como validação concluída. A exigência inicial de duas
rodadas consecutivas foi substituída pela instrução posterior de investigar com
execuções direcionadas e rodar a suíte completa uma única vez após a correção.
Não se afirma repetibilidade de duas rodadas completas corrigidas.

A execução final tem -vv, --durations=15, --maxfail=1, faulthandler_timeout=20 e
limite externo de 180 s (mais 5 s para encerramento forçado). Isso registra o
caso corrente e stacks se houver nova demora, sem repetir a suíte em laço. O
mínimo de 60% permanece configurado; --cov-fail-under=0 foi usado somente nos
subconjuntos de diagnóstico, que não exercitam toda a produção.

## Resultado final após a correção

**105 testes aprovados em 52,45 s; cobertura total 98,97%** (289 de 292 linhas
executáveis). Esta foi a única execução completa após a correção de desempenho.
Rodou na cópia sem dados reais com as versões do lockfile e retornou status 0.
Não há testes ignorados ou esperados como falha. O limite de 60% foi aplicado.

| Arquivo | Linhas executáveis | Ausentes | Cobertura | Linhas não cobertas |
| --- | ---: | ---: | ---: | --- |
| painel.py | 88 | 0 | 100,00% | — |
| src/pipeline_saude/__init__.py | 0 | 0 | 100,00% | — |
| src/pipeline_saude/cli.py | 34 | 1 | 97,06% | 45 |
| src/pipeline_saude/config.py | 2 | 0 | 100,00% | — |
| src/pipeline_saude/marts/__init__.py | 0 | 0 | 100,00% | — |
| src/pipeline_saude/marts/transform.py | 28 | 0 | 100,00% | — |
| src/pipeline_saude/raw/__init__.py | 0 | 0 | 100,00% | — |
| src/pipeline_saude/raw/ingest.py | 60 | 1 | 98,33% | 89 |
| src/pipeline_saude/refined/__init__.py | 0 | 0 | 100,00% | — |
| src/pipeline_saude/refined/transform.py | 80 | 1 | 98,75% | 165 |
| **Total** | **292** | **3** | **98,97%** | |

Principais lacunas, mantidas no denominador:

- cli.py:45: chamada pelo guard `if __name__ == '__main__'`. main() é testado
  diretamente nos três comandos, com sucesso e erro; não foi executado esse
  guard específico para inflar cobertura.
- raw/ingest.py:89 e refined/transform.py:165: salvaguardas de divergência de
  cardinalidade. Os testes confirmam cardinalidade correta e rollback real,
  mas não falsificam retornos do DuckDB para provocar contagens inconsistentes.

A métrica não prova cobertura de todos os ramos das regras SQL nem validação
visual em navegador. Os valores dos indicadores são verificados por testes reais;
as figuras reais continuam exercitadas fora da fixture exclusiva de interface.
Nenhum código de produção, SQL ou regra analítica foi alterado na auditoria,
confirmado por comparação SHA-256 dos arquivos antes/depois.

Distribuição: 8 casos CLI, 26 MARTS, 35 painel/interface, 16 RAW e 20 REFINED.
Durações finais: cache/recarga 2,35 s, figura real de evolução pequena/vazia
1,19 s, execução dos três comandos CLI 0,79 s, filtros independentes 0,73 s.
Não foi observada trava; o maior custo redundante dos AppTests foi removido.

Arquivos da auditoria: pyproject.toml, tests/test_raw.py, tests/test_cli.py,
tests/test_refined.py, tests/test_painel.py, README.md, docs/test_audit.md e
docs/ai_log.md. uv.lock não precisou de modificação nesta auditoria.
Relatório JUnit em /tmp/health-audit-final.xml; dados coverage na cópia em /tmp.
Arquivos gerados não entram na entrega. git diff --check sem erros.
