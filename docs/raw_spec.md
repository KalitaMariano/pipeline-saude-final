# Especificação da camada RAW — etapa 2

## Escopo e contrato

Ingerir somente `patients.csv`, `encounters.csv` e `medications.csv`, de uma
pasta local, em `raw.patients`, `raw.encounters` e `raw.medications` de um banco
DuckDB. Não criar refined, marts ou dashboard. Origem e licença continuam
pendentes; CSVs e banco gerado permanecem fora do Git.

Preservar nomes, ordem e conteúdo de todas as colunas originais como `VARCHAR`.
Campos vazios ficam como strings vazias (`''`), sem conversão para `NULL`.
Não remover espaços, zeros iniciais, registros repetidos ou anomalias. A
fidelidade refere-se aos valores decodificados do CSV, não à sua representação
física de aspas e quebras de linha; os arquivos originais permanecem intocados.

Usar CSV com cabeçalho, delimitador vírgula, aspas duplas e UTF-8. Arquivos
ausentes, codificação inválida, cabeçalhos vazios/repetidos, conflito de nomes
com metadados, bytes NUL ou registros com quantidade incorreta de campos
interrompem a carga, sem descartar registros silenciosamente.

## Metadados adicionados após as colunas originais

| Coluna | Tipo | Significado |
| --- | --- | --- |
| `_source_file` | VARCHAR | Nome do arquivo, sem expor caminho pessoal |
| `_source_sha256` | VARCHAR | SHA-256 dos bytes usados na leitura |
| `_source_row_number` | BIGINT | Posição do registro de dados, iniciando em 1, sem cabeçalho |
| `_ingested_at` | TIMESTAMPTZ | Instante UTC comum às três tabelas |
| `_batch_id` | VARCHAR | UUID da execução, comum às três tabelas |

O número representa o registro CSV, não a linha física: um campo entre aspas
pode conter quebras de linha. Arquivo, hash e posição permitem rastrear um
registro até a versão de origem, inclusive em medicamentos sem `Id`.

## Recarga e falhas

Cada execução substitui integralmente as três tabelas raw em uma única
transação. Não há append nem deduplicação por chave de negócio. Reexecutar os
mesmos CSVs mantém contagens e conteúdo original, atualizando lote e instante.
Alterações na origem são refletidas no próximo snapshot; versões anteriores
não são mantidas no banco nesta etapa.

Todos os CSVs são lidos e validados antes de abrir o banco. Hash e registros
vêm da mesma leitura em memória, adequada ao volume atual. Durante a gravação,
qualquer falha desfaz a transação inteira, preservando o snapshot anterior.
Não são alterados objetos fora das três tabelas raw; o banco deve ficar fora
da pasta dos CSVs. Em volumes maiores, revisar a leitura integral em memória.

## Critérios de aceitação

1. Os CSVs permanecem byte a byte iguais antes e depois da carga.
2. Cada tabela contém exatamente os registros do respectivo CSV.
3. Cabeçalhos originais e valores de todas as células coincidem, na ordem de
   `_source_row_number`; todos os campos originais são `VARCHAR`.
4. Metadados completos, hashes corretos e posições contínuas de 1 a N.
5. Duas execuções não acumulam registros; somente metadados de execução mudam.
6. Falhas não deixam uma carga parcial; não criar outras camadas.

Comandos de execução e resultados da validação estão no README e em
`raw_validation.md`. A validação desta etapa não substitui os futuros testes
unitários com pytest e dados fictícios.
