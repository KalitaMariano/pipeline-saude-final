# Registro de uso da IA

## 10/11/2026 — diagnóstico e etapa 1

**Solicitação:** analisar três CSVs sem alterá-los e, após aprovação da
arquitetura, preparar somente a estrutura inicial do projeto.

**Contribuição da IA:** leitura e perfil dos CSVs, verificação de chaves e
relacionamentos, propostas de indicadores e arquitetura; preparação da
configuração e documentação da etapa 1. Os resultados locais foram usados como
evidência; origem exata, versão e licença dos arquivos não foram verificadas.

**Limites de aprovação:** o usuário aprovou a stack e as três camadas. As regras
analíticas propostas no diagnóstico continuam pendentes, conforme
`decisions.md`. Não houve implementação de pipeline ou testes.

**Erros e correções:** nenhum erro de implementação identificado nesta etapa.
No diagnóstico, a suspeita de erro em sete atendimentos após o óbito foi
refinada ao verificar que todos têm descrição `Death Certification`; os
registros não foram classificados automaticamente como inválidos. Esse exemplo
deve orientar a revisão de hipóteses com evidência antes de aplicar limpeza.

**Limitação do ambiente:** o comando `git status --short` retornou
`fatal: not a git repository (or any of the parent directories): .git`.
O diretório `.git` está vazio e disponível somente para leitura. Os arquivos
foram preparados no diretório de trabalho; não foram adicionados ao índice,
commitados ou enviados a um remoto.

## 10/11/2026 — etapa 2: RAW

**Solicitação e escopo:** implementar somente ingestão dos três CSVs como texto,
com rastreabilidade, reexecução sem acúmulo, comandos e validação. Não implementar
refined, marts ou dashboard; não alterar nem versionar os CSVs; não fazer commit
ou push.

**Decisões concretizadas:** snapshot integral em uma transação; campos originais
`VARCHAR`, vazios preservados como `''`; metadados de arquivo, hash SHA-256,
posição, instante UTC e lote. Leitura dos bytes uma vez, antes da carga, para
que hash e conteúdo importado correspondam. Inserções parametrizadas em lotes
de até 500 registros. Contrato e critérios em `raw_spec.md`.

**Limitações do ambiente:** `uv sync` falhou por erro de DNS ao acessar o PyPI.
A tentativa de gerar lockfile offline também não conseguiu resolver as
dependências completas. Foi usado um cache copiado para `/tmp`, sem modificar
o cache original, para instalar DuckDB 1.5.6 no ambiente local do projeto.
A sincronização completa, o entry point instalado e o lockfile ainda precisam
de validação com acesso ao registro; a ingestão foi executada pela CLI como
módulo Python.

**Erro de validação e correção:** a primeira verificação tentou obter uma coluna
`TIMESTAMPTZ` diretamente como datetime Python e falhou porque `pytz` não estava
instalado no ambiente mínimo. A carga havia concluído. A conferência foi
ajustada para comparar `epoch(_ingested_at)` com o instante UTC do relatório,
sem alterar o tipo armazenado nem acrescentar dependência ao pipeline.

**Validação:** comparação integral das células com os CSVs, duas execuções,
conferência de tipos, cabeçalhos e metadados, hashes antes/depois e cenários
fictícios de preservação e falha transacional. Resultados em
`raw_validation.md`. O script pontual ficou em `/tmp`; nenhuma suíte de testes
foi adicionada nesta etapa.

**Git:** o repositório agora está disponível e contém o commit `3ffc687` da
estrutura inicial. Os dados e o banco permanecem ignorados. A IA não realizou
staging, commit ou push.

## 10/11/2026 — etapa 3: REFINED

**Autorização e escopo:** transformação das três tabelas RAW para REFINED,
tipagem, nulos, identificação técnica dos medicamentos, sinalização de qualidade,
recarga e testes unitários com dados fictícios em memória. Não implementar
marts nem dashboard; preservar CSVs e não fazer commit ou push.

**Decisões da IA para revisão:** contrato em `refined_spec.md`, com moedas
DECIMAL(18,2), inteiros BIGINT, timestamps com fuso explícito, vazios como nulos,
sem trim. Valores incompatíveis abortam toda a transação. Identificador de
medicamentos deriva da origem, sem deduplicação clínica. Verificações por EXISTS
evitam multiplicar linhas em relacionamentos com pais duplicados. Alertas
ficam em uma lista por registro, sem remover registros administrativos ou
medicamentos de duração zero. Decisões e pendências em `decisions.md`.

**Validações:** 17 testes pytest com conexão exclusivamente em memória e dados
fictícios; nenhuma leitura de CSV real ou banco persistido pelos testes. Na
validação local separada, duas execuções mantiveram contagens, conteúdo tipado,
identificadores e flags. Comparação da RAW e hashes dos CSVs confirmou que não
foram alterados. Resultados completos em `refined_validation.md`.

**Erros e correções:** nenhum teste falhou nesta etapa. Na revisão dos testes,
uma asserção que consultava o próprio ID como valor esperado foi substituída
por verificações independentes de contagem, valor monetário e mudança do ID
quando o hash da origem muda. Um patch da documentação falhou por contexto
inexato; o contexto foi conferido e o patch reaplicado. Nenhum registro foi
corrigido ou descartado.

**Ambiente:** pytest 9.1.1 e dependências instalados do cache em `/tmp`; DuckDB
1.5.6 já disponível. Comandos executados pelo módulo Python e pelo pytest do
ambiente local. A pendência de sincronização completa e lockfile da etapa RAW
permanece registrada. Script de validação real em `/tmp`, relatório JSON em
`artifacts/`, ambos fora do conjunto de arquivos versionáveis do projeto.

**Entrega:** somente arquivos da REFINED, CLI, testes e documentação/configuração
relacionados. Nenhum staging, commit ou push. Licença dos CSVs ainda pendente;
dados e bancos continuam ignorados pelo Git.
