# Gates Python e limites da evidência

Referência de trabalho: guidelines `definition-of-done`, `python` e `clean-arch`
do Mini Brain. Este repositório consumidor não instala nem altera o harness.

## Comandos reproduzíveis

- `make lint`: Ruff 0.14.2, regras E4/E7/E9/F em todo o Python descoberto.
- `make format-check`: Ruff 0.14.2, largura 88, sem modificar arquivos.
- `make lint-imports`: ordenação de imports no escopo explícito de ferramentas
  de QA e teste de transporte. Não reordena bootstrap, metadata ORM ou composição.
- `make test-agent-offline`: suite do agente usando modelos injetados, sem Gemini.
  Requer dependências do projeto instaladas com `uv sync --frozen`.
- `make typecheck-agent`: mypy 1.19.1 normal, com fontes internas dos dois
  toolkits e auxiliares de testes em `MYPYPATH`. Usa `.venv/bin/python` para
  descobrir as dependências; outro ambiente pode ser indicado explicitamente
  por `TYPECHECK_PYTHON=/caminho/do/venv/bin/python`. Requer `uv sync --frozen`.
  Não suprime erros de imports, não usa casts de conveniência e não equivale a
  `--strict` ou `--check-untyped-defs`. O escopo nominal é `services/agent`.
- `mypy --strict --no-incremental --explicit-package-bases services/agent`:
  diagnóstico de tipagem com mypy 1.19.1 disponível localmente. Não é um gate
  verde estabelecido. Deve rodar com dependências/tipos do projeto corretamente
  resolvidos antes de uma certificação de tipagem.

O primeiro uso dos comandos Ruff e mypy via `uvx` pode baixar a versão fixada do registro
oficial. Não modifica o ambiente operacional nem o lock de dependências.

## O que esses gates não provam

Lint e formatter não certificam arquitetura, permissões, concorrência, isolamento,
qualidade de prompts, acurácia do provedor ou contratos acadêmicos. A suite offline
não substitui teste real de Gemini, teste HTTP autenticado, PostgreSQL concorrente,
aceite visual nem validação de artefatos construídos.

O DoD completo continua exigindo: tipagem; lint/style; suite integral; build com
assets; contratos e critérios de aceite. Uma etapa indisponível ou reprovada deve
ser reportada como tal, nunca marcada concluída por substituição por Ruff.

## Revisão semântica separada

Avaliar em mudanças específicas, com testes de regressão:

1. Router → controller → validators → repository → serializer, conforme convenção
   FastAPI do projeto; não inserir uma camada service apenas para renomear controller.
2. Paginação do histórico no armazenamento, não somente após carregar todo o acervo.
3. Fronteira explícita da transação compartilhada entre agente, agenda e visitas.
4. Resultados autoritativos após commit e tratamento de falhas de consultas auxiliares.
5. Tipos públicos e docstrings que descrevam fielmente efeitos, limites e permissões.

Formatação mecânica foi comparada via AST antes/depois; imports não usados e
substituição de uma factory lambda por função foram tratados separadamente.
Imports de bootstrap que registram destinos de chaves estrangeiras foram mantidos
com justificativa local. Nenhuma exceção global foi usada para ocultar violações.

### Diagnóstico de tipagem (19/11/2026)

O comando strict acima terminou com 1.210 diagnósticos em 66 arquivos. Destacam-se
399 funções sem anotação e 583 chamadas a funções sem tipos; 47 imports não foram
resolvidos e 38 dependências não tinham tipos disponíveis no ambiente do mypy.
Esses números não equivalem a defeitos funcionais: o ambiente global da ferramenta
não é o venv isolado do projeto. Próxima avaliação deve usar `--python-executable`
apontando ao Python desse venv e separar código de produção dos testes. O resultado
atual é **reprovado**, não uma certificação de tipagem. Não foram adicionados ignores
ou stubs improvisados para tornar o relatório verde.

### Evolução do baseline

Com a descoberta explícita das fontes internas e o Python das dependências,
54 diagnósticos do modo normal caíram para oito, sem ignorar erros. As correções
subsequentes tratam bases ORM dinâmicas com `DeclarativeBase`, verificam a tabela
concreta no bootstrap, separam disponibilidade de ADK do símbolo de classe nos
testes e anotam a coleção de locks SQLite. A mudança das bases foi comparada por
DDL de tabelas e índices para PostgreSQL e SQLite, preservando as duas metadata
independentes. Isso não substitui o trabalho futuro de tipar interfaces públicas
e habilitar verificações dos corpos ainda sem anotações.
