# Validação MARTS — 10/11/2026

Execução local com DuckDB 1.5.6, pela CLI como módulo Python. A suíte completa
passou: **39 testes**, dos quais 22 casos da MARTS e 17 da REFINED, em 24,25 s.
Os testes não acessam CSVs nem banco persistido.

Casos MARTS: valores dos cinco indicadores; múltiplos medicamentos sem repetir
custos ou numeradores; aniversários de 18, 45 e 65 anos e dia anterior; ano em
UTC; denominador de emergência com duas classes; custo zero; anomalias financeiras
separadas da utilização; chaves duplicadas, órfãos, datas inválidas, óbito,
registros administrativos; medicamentos com vínculo divergente, início fora do
atendimento (anterior) e identidade ambígua; inclusão de início posterior com
alerta temporal preservado, custo e associação contabilizados; bases vazias;
recarga e rollback.

## Dados locais

RAW e REFINED mantiveram 108 pacientes, 5.571 atendimentos e 3.850 medicamentos.
A população analítica tem **5.563 atendimentos** e **3.850 medicamentos**.

- Excluídos oito atendimentos `Death Certification`: sete posteriores ao óbito
  e um sem alerta temporal. A exclusão é administrativa, conforme o contrato.
- Incluídos os 65 medicamentos com início posterior ao término do atendimento
  nos indicadores 4 e 5, conforme revisão aprovada. Os 65 alertas
  `start_after_encounter` permanecem na REFINED.
- Todos os registros elegíveis passaram nos critérios financeiros desta carga.
- 2.225 atendimentos têm ao menos um medicamento elegível.
- Custos de atendimentos: 16.804.458,34; cobertura: 12.453.385,69.
- Custos de medicamentos: 11.498.345,15; 39.152 dispensações; cobertura: 267.940,02.
- Valores sem atribuição de moeda; os custos das duas entidades não foram somados.

| Tabela marts | Linhas |
| --- | ---: |
| encounters_by_year_class | 245 |
| emergency_by_age | 4 |
| encounter_costs_by_year_class | 245 |
| medication_costs_by_code | 146 |
| encounters_with_medications | 37 |

Duas execuções produziram conteúdo idêntico em todas as tabelas, comparado com
ordenação de todas as colunas. Contagens e fingerprints agregados de todas as
colunas da RAW e REFINED permaneceram iguais antes/depois da recarga. As somas
dos MARTS financeiros foram reconciliadas separadamente com suas bases elegíveis.
Nenhuma escrita em CSV ou atualização de dados de origem faz parte desta etapa.

Relatório gerado em `artifacts/marts_validation.json` (ignorado pelo Git).
Script pontual de validação em `/tmp/validate_marts_revision.py`. A validação real é
separada dos testes e não fixa as contagens do dataset no código.

## Revisão aprovada das exclusões

Os oito Death Certification continuam excluídos da população clínica dos
indicadores 1, 2, 3 e 5. No indicador 4, não há impacto desses oito registros,
pois nenhum possui medicamentos. A exclusão administrativa foi explicitamente
aprovada; não caracteriza erro no registro preservado na REFINED.

Em relação à primeira entrega, a inclusão dos 65 medicamentos acrescentou
7.161 dispensações, 1.650.806,14 em custos e 7.229,56 em cobertura. Alterou 17
códigos, incluindo três novos, e acrescentou sete atendimentos ao numerador do
indicador 5. As linhas dos indicadores 1, 2, 3 e 5 permaneceram iguais.
Os custos de atendimentos permaneceram em 16.804.458,34 e a cobertura em
12.453.385,69, separados dos custos de medicamentos.

A validação comparou contagens e fingerprints de todas as colunas das seis
tabelas RAW/REFINED antes da primeira execução corrigida e após duas execuções.
Também verificou a presença dos 65 alertas temporais na base elegível, a ausência
de Death Certification na base clínica e todos os totais esperados por asserções.

## Extensões aprovadas na etapa 6

Acrescentados dashboard_kpis (uma linha global) e medication_cost_proportion no
indicador por código, sem mudar populações ou totais anteriores. Seis tabelas:
245 / 4 / 245 / 146 / 37 / 1 linhas. KPIs locais: 108 pacientes distintos,
5.563 atendimentos, 2.225 associados, fração 0,3999640481754449, custo de
atendimentos 16.804.458,34 e de medicamentos 11.498.345,15. Permanecem 39.152
dispensações. Duas execuções idênticas e RAW/REFINED com fingerprints inalterados.
A suíte ampliada tem 64 testes aprovados; detalhes em dashboard_spec.md.

## Descrições aprovadas — validação adicional

medication_description acrescentada por string_agg DISTINCT ordenado no SQL,
sem modificar regras ou dados REFINED. Comparação integral de todas as colunas
anteriores, ordenadas por código, confirmou igualdade antes/depois. As outras
cinco MARTS também permaneceram idênticas. Duas execuções confirmaram idempotência;
contagens/fingerprints de todas as tabelas RAW/REFINED permaneceram iguais.

Totais: 146 linhas e 146 códigos distintos, 3.850 registros de medicamentos,
39.152 dispensações, custo 11.498.345,15, cobertura 267.940,02. Participações
somam 1 dentro de tolerância de ponto flutuante (1,0000000000000007).
Os códigos 1000126 e 856987 preservam duas descrições distintas cada, incluindo
as diferenças de capitalização; não houve normalização textual.
Script pontual separado dos testes: /tmp/validate_medication_descriptions.py.
