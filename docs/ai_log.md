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
