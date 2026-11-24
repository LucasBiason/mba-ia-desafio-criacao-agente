# Plano de implementação — F01 — Fundação executável

## Dependências


## Passos de implementação

### SI01.1 — Preparar volumes e inicialização

- Tipo: infraestrutura.
- Depende de: Início da base.
- Ações: Definir serviços, variáveis de partida, health checks e carga idempotente dos bancos.
- Testes: Executar docker compose config e iniciar composition de teste; verificar saúde explícita de cada dependência.
- Critérios: F01-AC01, F01-AC02.

### SI01.2 — Publicar a interface local e provar persistência

- Tipo: comportamento.
- Depende de: SI01.1.
- Ações: Servir o build pelo proxy de mesma origem, manter a rede interna e validar reinício sobre volumes existentes.
- Testes: Abrir o login, consultar /api/health, comparar alterações antes e depois de reinício e recusar rota de introspecção pública.
- Critérios: F01-AC03, F01-SEC01.

### SI01.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para fundação executável.
- Testes: reiniciar users e common-areas sem executar restore e consultar GET /api/admin/users/{QA_USER} e GET /api/admin/areas/{QA_AREA}; confirmar que ambos retornam 200 com os mesmos identificadores e valores gravados, sem duplicação; executar make config e make up; conferir jobs identity-init, condo-init, session-init e agent-init concluídos, GET / e GET /docs nas respectivas portas; confirmar que manifesto válido, preparadores exit 0, portal 200 e documentação do assistente 200; liveness não certifica o provedor.
- Critérios: NFR02-AC01, NFR04-AC01.

### SI01.4 — Integrar a fundação HTTP e o importador por API

- Tipo: comportamento.
- Depende de: composição e cadastros administrativos existentes.
- Ações: instalar microservice-toolkit por dependência local empacotada, configurar os verificadores de identidade e implementar o importador administrativo por API.
- Testes: executar testes unitários HTTP da biblioteca, nove casos integrados do domínio, importação e repetição em QA e prova de runtime.
- Critérios: F01-AC04, F01-AC05.

### SI01.5 — Separar serviços e impor as camadas FastAPI

- Tipo: comportamento.
- Depende de: SI01.4 e contratos de cadastros existentes.
- Ações: separar os domínios em processos, adotar repositories SQLAlchemy, validators e serializers e centralizar health e documentação no toolkit.
- Testes: executar o gate de camadas, conferir Swagger e OpenAPI dos serviços, repetir os contratos HTTP e comparar os dados após preparar e reiniciar.
- Critérios: F01-AC06, F01-AC03, F01-AC04.


### SI01.6 — Consolidar o framework e separar a preparação dos dados

- Tipo: infraestrutura.
- Depende de: SI01.5 e ADR-0007.
- Ações: organizar o toolkit nos módulos da referência Shared; mover identidade, permissões e tipos Aurora ao aurora-toolkit; deixar somente domínios em services; renomear settings para parameters; usar REQUIRED_SECRETS no lifespan do framework e bootstrap explícito por componente, sem alteração de schema existente.
- Testes: executar a suíte do toolkit, os contratos HTTP/OpenAPI e a preparação repetida em volumes descartáveis; interromper apenas o banco do piloto, confirmar health 200 e operação de negócio 503, restaurar e comparar estado; verificar admin autorizado, morador 403 e chamada anônima 401 em apartments.
- Critérios: F01-AC02, F01-AC03, F01-AC04, F01-AC06, F01-SEC01.


### SI01.7 — Compor o cluster e distribuir os artefatos por serviço

- Tipo: infraestrutura.
- Depende de: SI01.6 e ADR-0008.
- Ações: manter um Compose em configs; colocar Dockerfile e entrypoint em cada serviço; centralizar configuração privada/exemplo em configs e manifesto e lock Python na raiz; regras Ruff em infra/python; preservar volumes e arquivos originais; iniciar portal, assistente e API do assistente com suas fronteiras.
- Testes: validar manifesto sem imprimir credenciais, construir imagens, subir o cluster isolado e consultar portal, Swagger e seis rotas do assistente; reiniciar e comparar estado; conferir ausência de caminhos internos no proxy público.
- Critérios: F01-AC01, F01-AC02, F01-AC03, F01-AC06, F01-SEC01.

### SI01.8 — Garantir a preparação explícita em todas as superfícies

- Tipo: infraestrutura.
- Depende de: SI01.6, SI01.7 e contratos de F09/F10.
- Ações: preparar histórico, ledger, admissão e sessões ADK nos jobs; manter HTTP sem DDL; aplicar models e repositories ORM também ao contrato acadêmico; manter manifesto e lock na raiz como metadados de distribuição.
- Testes: iniciar HTTP com banco indisponível e conferir liveness sem DDL; executar bootstrap explícito e repeti-lo preservando dados; rodar o gate estrutural em todas as aplicações e uv sync literal a partir da raiz.
- Critérios: F01-AC01, F01-AC02, F01-AC03, F01-AC06, NFR04-AC01.
