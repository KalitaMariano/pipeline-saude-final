# Especificação REFINED — etapa 3

## Escopo e preservação

Transformar exclusivamente `raw.patients`, `raw.encounters` e `raw.medications`
em tabelas de mesmo nome no schema `refined`, no mesmo DuckDB. A transformação
não lê CSVs, não altera RAW e não cria marts ou dashboard.

Manter nomes e ordem das colunas originais e todos os metadados RAW. Não filtrar,
deduplicar, imputar ou corrigir valores de negócio. Converter exclusivamente a
string vazia (`''`) em `NULL`, inclusive em textos; `NULL` já existente continua
nulo. Não aplicar trim: espaços são preservados, não considerados ausência.
Textos literais como `NULL` não são marcadores de ausência.

## Tipos e conversões

| Tabela | Colunas | Tipo REFINED |
| --- | --- | --- |
| patients | BIRTHDATE, DEATHDATE | DATE |
| patients | LAT, LON | DOUBLE finito |
| patients | HEALTHCARE_EXPENSES, HEALTHCARE_COVERAGE | DECIMAL(18,2) |
| patients | INCOME | BIGINT |
| encounters | START, STOP | TIMESTAMPTZ |
| encounters | BASE_ENCOUNTER_COST, TOTAL_CLAIM_COST, PAYER_COVERAGE | DECIMAL(18,2) |
| medications | START, STOP | TIMESTAMPTZ |
| medications | BASE_COST, PAYER_COVERAGE, TOTALCOST | DECIMAL(18,2) |
| medications | DISPENSES | BIGINT |
| Todas | Demais colunas originais | VARCHAR |

Identificadores, códigos clínicos, `FIPS`, `ZIP` e documentos são textos,
preservando zeros iniciais. Metadados RAW mantêm seus tipos anteriores.

Datas devem ter formato `AAAA-MM-DD` e existir no calendário. Timestamps devem
ser ISO 8601 com segundos, até seis casas fracionárias e fuso explícito (`Z` ou
offset `±HH:MM`): convertem-se para instantes absolutos, com comparações de data
feitas explicitamente em UTC. A apresentação de TIMESTAMPTZ por um cliente pode
depender do fuso da sessão; `AT TIME ZONE 'UTC'` permite apresentação UTC.

Inteiros aceitam somente dígitos com sinal opcional dentro do limite BIGINT.
Valores monetários aceitam ponto decimal e no máximo duas casas, dentro do
limite DECIMAL(18,2). Não aceitar arredondamento implícito de valores como
`1.5` em inteiro ou `2.505` em moeda. Não aceitar NaN ou infinito em coordenadas.

Um campo preenchido incompatível com o tipo interrompe e desfaz toda a carga,
com mensagem indicando tabela, coluna e quantidade inválida, sem expor valores
pessoais. A RAW permanece disponível e a versão REFINED anterior é preservada.
Assim, conversões inválidas não se tornam nulos silenciosamente.

## Rastreabilidade e identificação técnica

Acrescentar `_refined_at` (TIMESTAMPTZ), instante da transação comum às tabelas.
Em medicamentos, acrescentar `_medication_id` (VARCHAR), SHA-256 da lista JSON:

```text
[nome do arquivo, SHA-256 do arquivo, posição do registro como texto]
```

A lista JSON evita ambiguidade por separadores. O identificador é estável para
a mesma versão do arquivo e posição, independentemente do lote RAW. Registros
idênticos em posições diferentes recebem IDs diferentes. Uma nova versão do
arquivo muda os IDs: esta é uma identidade de origem, não uma chave clínica
estável entre versões. Arquivo, hash ou posição ausentes/inválidos, ou a mesma
linhagem repetida, abortam a carga, pois impedem identificação inequívoca.

## Qualidade: sinalizar e preservar

Cada linha recebe `_quality_flags` (VARCHAR[]), uma lista vazia quando nenhuma
regra é acionada. Chaves e relacionamentos são verificações de qualidade, sem
constraints que rejeitem ou apaguem registros. Não impor unicidade aos códigos
de medicamentos ou à combinação paciente/atendimento/código/início.

As verificações com as tabelas relacionadas usam EXISTS, evitando multiplicação
de linhas mesmo quando há chaves de negócio duplicadas. Se houver múltiplos
pais, uma divergência em qualquer correspondência sinaliza a linha; as chaves
duplicadas dos pais também ficam sinalizadas.

| Grupo | Sinalizações |
| --- | --- |
| Chaves de patients e encounters | `missing_id`, `duplicate_id` (todas as linhas da chave repetida) |
| Pacientes | `missing_birthdate`, `death_before_birth`, `unknown_zip` (nulo ou `00000`), `invalid_zip` (não tem cinco dígitos), `missing_fips`, `invalid_coordinates` (fora dos limites), `negative_amount` (inclui renda) |
| Atendimentos e medicamentos | `missing_patient`, `orphan_patient`, `missing_start`, `stop_before_start`, `zero_duration`, `start_before_birth`, `start_after_death`, `stop_after_death`, `reason_pair_mismatch`, `negative_amount`, `coverage_above_total` |
| Atendimentos | `missing_stop`, `total_below_base` |
| Medicamentos | `missing_encounter`, `orphan_encounter`, `patient_encounter_mismatch`, `start_before_encounter`, `start_after_encounter`, `invalid_dispenses` (nulo ou não positivo), `cost_product_mismatch` |

Datas de nascimento e óbito não têm hora; comparar apenas a data UTC do evento,
sem presumir o horário do óbito. `Death Certification` permanece na tabela e
recebe sinalização temporal se aplicável, sem classificação automática como
registro inválido. Não sinalizar término ausente de medicamento como erro nem
inferir uso atual. Motivo ausente em ambos os campos é permitido.

Não consolidar descrições por código, tratar outliers financeiros ou inferir
moeda. As flags são alertas, não provas de erro clínico. A contagem de flags
pode exceder a quantidade de linhas, pois uma linha pode receber vários alertas.

## Recarga, comandos e critérios de aceitação

Substituir as três tabelas REFINED em uma única transação. Reexecutar sobre a
mesma RAW mantém conteúdo, IDs e flags; apenas `_refined_at` pode mudar. Não
manter histórico e não adicionar registros por append. A contagem de cada
tabela deve ser igual à da RAW correspondente; divergências abortam a carga.
As contagens de 108/5.571/3.850 são critérios da validação local, não constantes
do código, que também deve funcionar com dados fictícios e tabelas vazias.

Comando: `uv run pipeline-saude refined --database artifacts/saude.duckdb`.
O banco deve existir e conter a RAW. A saída JSON resume contagens e flags;
falhas produzem código de saída 1. Testes: `uv run pytest -q`.

Os testes unitários criam tabelas fictícias usando exclusivamente
`duckdb.connect(':memory:')`, sem CSVs ou banco persistido. Cobrem tipos, UTC,
decimais, nulos, zeros iniciais, preservação, chaves, relacionamentos, anomalias,
recarga, estabilidade da identidade e rollback. Resultados da validação local
estão em `refined_validation.md`.
