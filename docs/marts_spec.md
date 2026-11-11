# Contrato MARTS — etapa 4

Snapshot analítico no schema `marts`, consumindo exclusivamente REFINED. Seis
arquivos SQL materializam seis tabelas; `_base.sql` define duas views temporárias
compartilhadas, removidas ao concluir. A etapa 6 acrescenta dashboard consumidor, sem alterações na REFINED.
As regras de exclusão abaixo incorporam a revisão aprovada pelo usuário na etapa 4.

## População e qualidade

A base de atendimentos exige IDs preenchidos e únicos tanto em patients quanto
em encounters: todas as ocorrências de chaves ambíguas são excluídas, sem escolher
arbitrariamente um registro. JOIN pelo paciente, classe e início preenchidos,
término preenchido e maior ou igual ao início. Nascimento conhecido, não posterior
ao início; óbito, quando presente, não anterior ao nascimento ou à data do término.
Comparações de datas e ano são em UTC. Excluir descrição exatamente igual a
`Death Certification`, inclusive quando não há alerta temporal. A exclusão é
somente analítica e aprovada: os indicadores 1, 2, 3 e 5 descrevem atendimentos
clínicos. O indicador 4 usa medicamentos vinculados a essa mesma população;
não há medicamentos ligados aos oito registros administrativos nesta carga.
A exclusão não significa que o registro administrativo seja inválido.

Idade: anos completos entre nascimento e data UTC de início, por `age()`, nunca
idade atual ou simples diferença entre anos. Faixas: 0–17, 18–44, 45–64, 65+.
Sem limite superior arbitrário e sem período de observação imposto. Somente grupos
observados são materializados; não são criadas linhas artificiais de valor zero.

Medicamentos exigem atendimento elegível, mesmo paciente, código e identidade
técnica preenchidos, identidade técnica única e início não anterior ao início do
atendimento. O início pode ser posterior ao término do atendimento: o vínculo
por ENCOUNTER e PATIENT é suficiente nesse caso, tanto no indicador 4 quanto
no 5. A flag `start_after_encounter` permanece na REFINED e não exclui esses
registros. O filtro de início anterior ao atendimento continua em vigor.
Término nulo ou não anterior ao início é aceito.
Não exigir que o tratamento termine durante o atendimento. Registros distintos
do mesmo código não são deduplicados. Duração zero é permitida nas duas bases.

Não excluir por alertas de CEP, FIPS, coordenadas, renda, motivo ausente ou
incompleto. As condições são reavaliadas nos valores tipados; não basta uma
lista de flags vazia. Uma anomalia financeira não elimina utilização ou vínculo.

Medidas financeiras de atendimento usam somente linhas com os três valores
preenchidos: base >= 0, total >= base e cobertura entre zero e total. Medicamentos:
base, total e cobertura preenchidos e não negativos, cobertura <= total,
dispensações positivas e total = base × dispensações. Linhas inelegíveis ficam
nas contagens gerais, mas fora de todas as somas e denominadores financeiros.
Não imputar ausências como zero. Soma sem observações válidas e divisão por zero
retornam NULL. Custos são decimais; razões e médias usam divisão DuckDB.

## Granularidades e denominadores

| Tabela / arquivo SQL | Uma linha por | Medidas e denominadores |
| --- | --- | --- |
| `encounters_by_year_class` | ano UTC × classe | número de atendimentos elegíveis, sem denominador |
| `emergency_by_age` | faixa etária, todos os anos | atendimentos totais e de classe exatamente `emergency`; proporção = emergência / todos os atendimentos da faixa; pacientes distintos totais e com emergência na faixa |
| `encounter_costs_by_year_class` | ano UTC × classe | contagens total e financeiramente válida; somas base, total, cobertura e total menos cobertura; média = soma total / atendimentos financeiramente válidos; razão de cobertura = soma cobertura / soma total, na mesma população |
| `medication_costs_by_code` | código textual, todos os anos | registros e atendimentos distintos; registros financeiros válidos, soma dispensações, TOTALCOST e cobertura; custo por dispensação = soma TOTALCOST / soma DISPENSES válidas |
| `encounters_with_medications` | classe × faixa etária, todos os anos | atendimentos com ao menos um medicamento elegível / todos os atendimentos elegíveis do grupo |

As proporções são frações de 0 a 1, não percentuais. Emergência mede a participação
nos atendimentos observados, não uma taxa populacional ou por pessoa-tempo.
Pacientes podem aparecer em diferentes faixas conforme envelhecem. Dispensações
são a soma de DISPENSES, não a contagem de linhas nem quantidade de doses.
Descrições não entram na chave do medicamento, evitando fragmentar códigos.

O JOIN patients–encounters tem cardinalidade um para muitos após exclusão de
chaves ambíguas. Medicamentos são unidos a essa base única para a análise por
código. O quinto indicador usa uma lista DISTINCT de atendimentos com medicamentos
antes do LEFT JOIN. Os custos de atendimentos nunca são agregados após um JOIN
com medicamentos. TOTALCOST já inclui DISPENSES; não multiplicar novamente.
Não somar custos de medicamentos aos de atendimento, não inferir desembolso do
paciente a partir da diferença de cobertura e não presumir moeda ou escopo do
TOTAL_CLAIM_COST sem documentação da origem.

## Operação

`uv run pipeline-saude marts --database artifacts/saude.duckdb` exige banco e
REFINED existentes. Uma transação substitui as seis tabelas por CREATE OR
REPLACE; erro desfaz a etapa inteira. A saída JSON informa contagens de linhas
elegíveis e das tabelas. Uma recarga com a mesma REFINED produz o mesmo conteúdo.
Os SQLs também são incluídos no wheel. Testes: `uv run pytest -q`, exclusivamente
com dados fictícios e DuckDB em memória. Validação real separada em
[marts_validation.md](marts_validation.md).

## Extensões aprovadas para o dashboard — etapa 6

Adicionadas uma tabela `dashboard_kpis` (uma linha global para todo o histórico)
e a coluna `medication_cost_proportion DOUBLE` em `medication_costs_by_code`.
As definições completas e os tipos estão em [dashboard_spec.md](dashboard_spec.md).
KPIs: pacientes distintos com atendimento elegível, atendimentos clínicos,
atendimentos com medicamentos, sua proporção, custo válido de atendimentos e
custo válido de medicamentos. Custos calculados separadamente, com os mesmos
filtros financeiros já aprovados. Participação = custo do código / custo de todos
os códigos, calculada no SQL antes de qualquer top 10 visual. Denominadores zero
retornam NULL. Nenhuma regra de elegibilidade alterada.

## Descrições de medicamentos — extensão aprovada

A tabela medication_costs_by_code inclui medication_description VARCHAR,
calculada exclusivamente em SQL por `string_agg(DISTINCT DESCRIPTION, ' | '
ORDER BY DESCRIPTION)`, sobre as linhas da base elegível marts_medications,
com DESCRIPTION proveniente da REFINED. Uma linha por código, com descrições
distintas ordenadas e concatenadas; todas nulas produzem NULL. Não se aplica
normalização textual. Coluna descritiva adicional, sem mudança nas contagens,
valores financeiros, dispensações ou denominadores. Código continua sendo a
chave da agregação e o identificador dos gráficos.
